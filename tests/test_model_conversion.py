from pathlib import Path

import hypothesis as ht
import pytest

from demux_sapio_watcher.bclconvert.find_folders import find_bclconvert_folders
from demux_sapio_watcher.bclconvert.parse_folder import parse_bclconvert_folder
from demux_sapio_watcher.sapio_types import SequencingFile
from tests.conftest import runfolder
from tests.data_generation import PairedReadSampleTestData, build_samples


@ht.given(build_samples())
def test_conversion(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        converted = [SequencingFile.from_bclconvert(item) for item in data]
        assert len(converted) == len(data)


@ht.given(build_samples())
def test_payload(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        converted = [SequencingFile.from_bclconvert(item) for item in data]
        assert len(converted) == len(data)
        for item in converted:
            payload = item.update_payload()
            assert "dataTypeName" in payload
            assert "recordId" in payload
            assert "fields" in payload


@ht.given(build_samples())
def test_qc_metrics(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        assert len(data), "No data parsed from BCLConvert folder"

        for item in data:
            # Check first for paired ends
            converted = SequencingFile.from_bclconvert(item)
            assert item.quality_metrics_read2 is not None, (
                "Expected paired-end data for this test"
            )
            assert converted.dataReadPasses == 2
            assert converted.readsPf == item.demux_stats.num_reads
            assert (
                converted.pfClustersPercentPerLane
                == 100 * item.demux_stats.percent_reads
            )
            assert (
                converted.perfectIndexReadPercent
                == 100 * item.demux_stats.percent_perfect_index_reads
            )
            assert (
                converted.oneMismatchIndexReadPercent
                == 100 * item.demux_stats.percent_one_mismatch_index_reads
            )
            assert (
                converted.yieldPfGb
                == (
                    item.quality_metrics_read1.yield_
                    + item.quality_metrics_read2.yield_
                )
                / 1e9
            )

            assert converted.basesQ30Percent == (
                100
                * (
                    item.quality_metrics_read1.yield_q30
                    + item.quality_metrics_read2.yield_q30
                )
                / (
                    item.quality_metrics_read1.yield_
                    + item.quality_metrics_read2.yield_
                )
            )

            assert converted.averageQScore == (
                item.quality_metrics_read1.quality_score_sum
                + item.quality_metrics_read2.quality_score_sum
            ) / (item.quality_metrics_read1.yield_ + item.quality_metrics_read2.yield_)

            # Check for single-end data by removing read 2
            item.fastq.read2_file = None
            item.quality_metrics_read2 = None
            converted_se = SequencingFile.from_bclconvert(item)
            assert item.quality_metrics_read2 is None, (
                "Expected single-end data for this test"
            )
            assert converted_se.dataReadPasses == 1
            assert converted_se.yieldPfGb == item.quality_metrics_read1.yield_ / 1e9
            assert converted_se.basesQ30Percent == pytest.approx(
                100
                * (
                    item.quality_metrics_read1.yield_q30
                    / item.quality_metrics_read1.yield_
                )
            )
            assert converted_se.averageQScore == (
                item.quality_metrics_read1.quality_score_sum
                / item.quality_metrics_read1.yield_
            )
