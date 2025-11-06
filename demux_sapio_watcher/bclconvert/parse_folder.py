import logging
from collections.abc import Generator
from pathlib import Path

from pydantic import ValidationError

from demux_sapio_watcher.bclconvert.models import (
    CombinedSampleData,
    DemuxStats,
    FastqListEntry,
    QualityMetrics,
)

logger = logging.getLogger(__name__)
REQUIRED_BCLCONVERT_FILES = {
    "Demultiplex_Stats": "fastq/Reports/Demultiplex_Stats.csv",
    "Quality_Metrics": "fastq/Reports/Quality_Metrics.csv",
    "fastq_list": "fastq/Reports/fastq_list.csv",
}


def parse_bclconvert_folder(
    bclconvert_path: Path,
) -> Generator[CombinedSampleData]:
    """Parse the BCLConvert folder and return a dictionary with sample names as keys."""
    # Check for required files
    for file_desc, rel_path in REQUIRED_BCLCONVERT_FILES.items():
        file_path = bclconvert_path / rel_path
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required file '{file_desc}' not found at {file_path}"
            )

    combined_data: dict[str, dict] = {}
    fastq_list_path = bclconvert_path / REQUIRED_BCLCONVERT_FILES["fastq_list"]
    with fastq_list_path.open("r") as f:
        header = next(f).strip("\n").split(",")
        for line in f:
            fields = line.strip("\n").split(",")
            sample_info = dict(zip(header, fields))
            try:
                fastq_entry = FastqListEntry(filename=fastq_list_path, **sample_info)
            except ValidationError as e:
                logger.error(f"Error parsing FastqListEntry: {e}")
                continue
            if fastq_entry.sample_id in combined_data:
                logger.warning(
                    f"Duplicate sample ID {fastq_entry.sample_id} found in fastq_list.csv. Overwriting previous entry."
                )
            combined_data[fastq_entry.sample_id] = {"fastq": fastq_entry}

    with open(bclconvert_path / REQUIRED_BCLCONVERT_FILES["Demultiplex_Stats"]) as f:
        header = next(f).strip("\n").split(",")
        for line in f:
            fields = line.strip("\n").split(",")
            sample_info = dict(zip(header, fields))
            try:
                demux_entry = DemuxStats(**sample_info)
            except ValidationError as e:
                logger.error(f"Error parsing DemuxStats entry: {e}")
                continue
            if demux_entry.sample_id not in combined_data:
                combined_data[demux_entry.sample_id] = {}

            if "demux_stats" in combined_data[demux_entry.sample_id]:
                logger.warning(
                    f"Duplicate sample ID {demux_entry.sample_id} found in Demultiplex_Stats.csv. Overwriting previous entry."
                )

            combined_data[demux_entry.sample_id]["demux_stats"] = demux_entry

    with open(bclconvert_path / REQUIRED_BCLCONVERT_FILES["Quality_Metrics"]) as f:
        header = next(f).strip("\n").split(",")
        for line in f:
            fields = line.strip("\n").split(",")
            sample_info = dict(zip(header, fields))
            try:
                quality_entry = QualityMetrics(**sample_info)
            except ValidationError as e:
                logger.error(f"Error parsing QualityMetrics entry: {e}")
                continue

            if quality_entry.read_number == 1:
                combined_data[quality_entry.sample_id]["quality_metrics_read1"] = (
                    quality_entry
                )
            elif quality_entry.read_number == 2:
                combined_data[quality_entry.sample_id]["quality_metrics_read2"] = (
                    quality_entry
                )

    for data in combined_data.values():
        try:
            yield CombinedSampleData(**data)
        except ValidationError as e:
            logger.error(f"Error combining sample data: {e}")
            continue
