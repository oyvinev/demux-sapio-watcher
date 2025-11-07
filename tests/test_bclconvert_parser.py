from pathlib import Path

import hypothesis as ht

from demux_sapio_watcher.bclconvert.find_folders import find_bclconvert_folders
from demux_sapio_watcher.bclconvert.parse_folder import parse_bclconvert_folder
from tests.conftest import runfolder
from tests.data_generation import (
    PairedReadSampleTestData,
    RunFolder,
    SingleReadSampleTestData,
    build_samples,
    test_paired_sample_strategy,
    test_single_read_sample_strategy,
)


@ht.given(build_samples())
def test_parse_bclconvert_folder(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        assert len(data) == len(samples), (
            f"Expected {len(samples)} samples, got {len(data)} - not all samples were parsed?"
        )


@ht.given(test_paired_sample_strategy)
def test_parse_bclconvert_single_sample(sample: PairedReadSampleTestData):
    with runfolder([sample]) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        assert len(data) == 1, f"Expected 1 sample, got {len(data)}"


@ht.given(test_single_read_sample_strategy)
def test_parse_bclconvert_single_no_paired_ends(sample: SingleReadSampleTestData):
    with runfolder([sample]) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        assert len(data) == 1, f"Expected 1 sample, got {len(data)}"
        combined_sample = data[0]
        assert combined_sample.fastq.read2_file is None, "Read2File should be None"
        assert combined_sample.quality_metrics_read2 is None, (
            "QualityMetrics for Read 2 should be None"
        )


@ht.given(test_paired_sample_strategy)
def test_parse_bclconvert_missing_fastq(sample: PairedReadSampleTestData):
    with runfolder([sample]) as rf:
        # Remove one of the fastq files
        fastq1_path = (
            Path(rf.root) / RunFolder.FASTQC_LIST
        ).parent / sample.fastq_read1_path
        fastq1_path.unlink()  # delete the file

        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        assert len(data) == 0, (
            f"Expected 0 samples due to missing fastq, got {len(data)}"
        )
