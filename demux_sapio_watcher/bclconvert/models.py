from pathlib import Path
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.types import DirectoryPath, FilePath


class BCLConvertFolder(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: DirectoryPath
    demultiplex_stats_path: FilePath
    quality_metrics_path: FilePath
    fastq_list_path: FilePath

    @field_validator(
        "demultiplex_stats_path",
        "quality_metrics_path",
        "fastq_list_path",
        mode="after",
    )
    def resolve_paths(cls, v: Path) -> Path:
        """Ensure paths are absolute."""
        return v.resolve()

    @classmethod
    def from_path(cls, path: Path) -> BCLConvertFolder:
        """Create a BCLConvertFolder from a given path."""
        # Are there other possible locations for these files?
        valid_subpaths = {
            "Demultiplex_Stats.csv": (
                path / "Demultiplex_Stats.csv",
                path / "Demux/Demultiplex_Stats.csv",
                path / "BCLConvert/fastq/Reports/Demultiplex_Stats.csv",
            ),
            "Quality_Metrics.csv": (
                path / "Quality_Metrics.csv",
                path / "Demux/Quality_Metrics.csv",
                path / "BCLConvert/fastq/Reports/Quality_Metrics.csv",
            ),
            "fastq_list.csv": (
                path / "fastq_list.csv",
                path / "Demux/fastq_list.csv",
                path / "BCLConvert/fastq/Reports/fastq_list.csv",
            ),
        }

        demultiplex_stats_path = next(
            (f for f in valid_subpaths["Demultiplex_Stats.csv"] if f.is_file()),
            None,
        )
        quality_metrics_path = next(
            (f for f in valid_subpaths["Quality_Metrics.csv"] if f.is_file()),
            None,
        )
        fastq_list_path = next(
            (f for f in valid_subpaths["fastq_list.csv"] if f.is_file()), None
        )
        return cls(
            path=path,
            demultiplex_stats_path=demultiplex_stats_path,
            quality_metrics_path=quality_metrics_path,
            fastq_list_path=fastq_list_path,
        )


class QualityMetrics(BaseModel):
    lane: int = Field(..., alias="Lane")
    sample_id: str = Field(..., alias="SampleID")
    # sample_project: str = Field(..., alias="Sample_Project")
    index: str = Field(..., alias="index")
    index2: str = Field(..., alias="index2")
    read_number: int = Field(..., alias="ReadNumber")
    yield_: int = Field(..., alias="Yield")
    yield_q30: int = Field(..., alias="YieldQ30")
    quality_score_sum: int = Field(..., alias="QualityScoreSum")
    mean_quality_score_pf: float = Field(..., alias="Mean Quality Score (PF)")
    percent_q30: float = Field(..., alias="% Q30")


class DemuxStats(BaseModel):
    lane: int = Field(..., alias="Lane")
    sample_id: str = Field(..., alias="SampleID")
    # sample_project: str = Field(..., alias="Sample_Project")
    index: str = Field(..., alias="Index")
    num_reads: int = Field(..., alias="# Reads")
    num_perfect_index_reads: int = Field(..., alias="# Perfect Index Reads")
    num_one_mismatch_index_reads: int = Field(..., alias="# One Mismatch Index Reads")
    num_two_mismatch_index_reads: int = Field(..., alias="# Two Mismatch Index Reads")
    percent_reads: float = Field(..., alias="% Reads")
    percent_perfect_index_reads: float = Field(..., alias="% Perfect Index Reads")
    percent_one_mismatch_index_reads: float = Field(
        ..., alias="% One Mismatch Index Reads"
    )
    percent_two_mismatch_index_reads: float = Field(
        ..., alias="% Two Mismatch Index Reads"
    )


class FastqListEntry(BaseModel):
    file: FilePath
    read_group: str = Field(..., alias="RGID")
    sample_id: str = Field(..., alias="RGSM")
    library: str = Field(..., alias="RGLB")
    lane: int = Field(..., alias="Lane")
    read1_file: Path = Field(..., alias="Read1File")
    read2_file: Path | None = Field(..., alias="Read2File")

    @field_validator("read2_file", mode="before")
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    @model_validator(mode="after")
    def check_read2_file(self):
        if not self.read1_file.is_absolute():
            self.read1_file = (self.file.parent / self.read1_file).resolve()
        if self.read2_file and not self.read2_file.is_absolute():
            self.read2_file = (self.file.parent / self.read2_file).resolve()

        if self.read1_file == self.read2_file:
            raise ValueError("Read1File and Read2File cannot be the same")

        if not self.read1_file.exists():
            raise ValueError(f"Read1File does not exist: {self.read1_file}")
        if self.read2_file and not self.read2_file.exists():
            raise ValueError(f"Read2File does not exist: {self.read2_file}")
        return self


class CombinedSampleData(BaseModel):
    fastq: FastqListEntry
    demux_stats: DemuxStats
    quality_metrics_read1: QualityMetrics
    quality_metrics_read2: QualityMetrics | None = None

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.fastq.sample_id != self.demux_stats.sample_id:
            raise ValueError("Sample ID mismatch between FastqListEntry and DemuxStats")
        if self.fastq.sample_id != self.quality_metrics_read1.sample_id:
            raise ValueError(
                "Sample ID mismatch between FastqListEntry and QualityMetrics (Read 1)"
            )
        if self.fastq.read2_file is not None:
            if self.quality_metrics_read2 is None:
                raise ValueError(
                    "Read 2 file is present but QualityMetrics for Read 2 is missing"
                )
            if self.fastq.sample_id != self.quality_metrics_read2.sample_id:
                raise ValueError(
                    "Sample ID mismatch between FastqListEntry and QualityMetrics (Read 2)"
                )
        return self

    @model_validator(mode="after")
    def num_fastq_files_consistency(self) -> Self:
        if self.fastq.read2_file is None and self.quality_metrics_read2 is not None:
            raise ValueError(
                "QualityMetrics for Read 2 is present but Read 2 file is missing"
            )
        if self.fastq.read2_file is not None and self.quality_metrics_read2 is None:
            raise ValueError(
                "Read 2 file is present but QualityMetrics for Read 2 is missing"
            )
        return self

    @model_validator(mode="after")
    def validate_read_number(self) -> Self:
        assert self.quality_metrics_read1.read_number == 1, (
            "Read number for quality_metrics_read1 must be 1"
        )
        if self.quality_metrics_read2:
            assert self.quality_metrics_read2.read_number == 2, (
                "Read number for quality_metrics_read2 must be 2"
            )
        return self
