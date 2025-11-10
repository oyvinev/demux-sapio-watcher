import logging
from collections.abc import Generator

from pydantic import ValidationError

from demux_sapio_watcher.bclconvert.models import (
    BCLConvertFolder,
    CombinedSampleData,
    DemuxStats,
    FastqListEntry,
    QualityMetrics,
)

logger = logging.getLogger(__name__)


def parse_bclconvert_folder(
    bclconvert_folder: BCLConvertFolder,
) -> Generator[CombinedSampleData]:
    """Parse the BCLConvert folder and return a dictionary with sample names as keys."""
    combined_data: dict[str, dict] = {}
    # with fastq_list_path.open("r") as f:
    for fastq_list_path in bclconvert_folder.fastq_list_paths:
        with fastq_list_path.open("r") as f:
            header = next(f).strip("\n").split(",")
            for line in f:
                fields = line.strip("\n").split(",")
                sample_info = dict(zip(header, fields))
                if sample_info.get("SampleID") == "Undetermined":
                    continue

                try:
                    fastq_entry = FastqListEntry(file=fastq_list_path, **sample_info)
                except ValidationError as e:
                    logger.error(f"Error parsing FastqListEntry: {e}")
                    continue
                if fastq_entry.sample_id in combined_data:
                    logger.warning(
                        f"Duplicate sample ID {fastq_entry.sample_id} found in fastq_list.csv. Overwriting previous entry."
                    )
                combined_data[fastq_entry.sample_id] = {"fastq": fastq_entry}

    for demultiplex_stats_path in bclconvert_folder.demultiplex_stats_paths:
        with demultiplex_stats_path.open("r") as f:
            header = next(f).strip("\n").split(",")
            for line in f:
                fields = line.strip("\n").split(",")
                sample_info = dict(zip(header, fields))
                if sample_info.get("SampleID") == "Undetermined":
                    continue
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

    for quality_metrics_path in bclconvert_folder.quality_metrics_paths:
        with quality_metrics_path.open("r") as f:
            header = next(f).strip("\n").split(",")
            for line in f:
                fields = line.strip("\n").split(",")
                sample_info = dict(zip(header, fields))
                if sample_info.get("SampleID") == "Undetermined":
                    continue
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

    for sample_id, data in combined_data.items():
        try:
            yield CombinedSampleData(**data)
        except ValidationError as e:
            logger.error(f"Error combining sample data for sample '{sample_id}':\n{e}")
            continue
