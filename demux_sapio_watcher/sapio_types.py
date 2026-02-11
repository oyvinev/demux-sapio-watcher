import re
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from demux_sapio_watcher.bclconvert.models import CombinedSampleData, QualityMetrics

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


class SapioRecord(BaseModel):
    record_id: int | None = Field(
        ...,
        alias="RecordId",
        description="The system-wide unique ID of this data record",
    )

    def update_payload(self, deleted=False, new=False) -> dict:
        "Return a dict suitable for the 'fields' in the set_field_value API."
        return {
            "dataTypeName": self.__class__.__name__,
            "recordId": self.record_id,
            "fields": self.model_dump(
                mode="json", by_alias=True, exclude={"record_id"}
            ),
            "deleted": deleted,
            "new": new,
        }


class SequencingFile(SapioRecord):
    model_config = ConfigDict(extra="ignore")
    sample_guid: UUID = Field(
        ...,
        alias="SampleGuid",
        description="The UUID associated with this sequencing file",
    )
    fastq_path_R1: Path | None = Field(
        None, alias="FASTQ_path_R1", description="Path to the R1 FASTQ file"
    )
    fastq_path_R2: Path | None = Field(
        None, alias="FASTQ_path_R2", description="Path to the R2 FASTQ file"
    )
    fastq_path_I1: Path | None = Field(
        None, alias="FASTQ_path_I1", description="Path to the I1 FASTQ file"
    )
    fastq_path_I2: Path | None = Field(
        None, alias="FASTQ_path_I2", description="Path to the I2 FASTQ file"
    )
    sample_name: str | None = Field(
        None, alias="SampleName", description="The name of the sample"
    )
    all_files_available: bool = Field(
        ..., alias="AllFilesAvailable", description="Whether all files are available"
    )

    readsPf: int | None = Field(
        None,
        description="# Reads from demux stats",
    )

    pfClustersPercentPerLane: float | None = Field(
        None,
        description="% Reads from demux stats",
    )
    perfectIndexReadPercent: float | None = Field(
        None,
        description="% Perfect Index Reads from demux stats",
    )

    oneMismatchIndexReadPercent: float | None = Field(
        None,
        description="% One Mismatch Index Reads from demux stats",
    )

    yieldPfGb: float | None = Field(
        None,
        description="Yield (in Gb) - sum of R1 and R2 yield",
    )

    basesQ30Percent: float | None = Field(
        None,
        description="% Bases with quality score >= Q30",
    )

    averageQScore: float | None = Field(
        None,
        description="Quality score sum / yield",
    )

    @field_validator(
        "fastq_path_R1",
        "fastq_path_R2",
        "fastq_path_I1",
        "fastq_path_I2",
        mode="before",
    )
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @computed_field
    @property
    def dataReadPasses(self) -> None | int:
        "Return the number of data reads (1 or 2) based on available FASTQ paths."
        if self.fastq_path_R1 and self.fastq_path_R2:
            return 2
        if self.fastq_path_R1:
            return 1
        return None

    @computed_field
    @property
    def oraCompressionEnabled(self) -> None | bool:
        "Return True if ORA compression is enabled (deduced from R1 file extension)."
        if not self.fastq_path_R1:
            return None

        return ".ora" in self.fastq_path_R1.name

    @computed_field
    @property
    def sampleSheetPosition(self) -> int | None:
        "Return the sample sheet position (S##) extracted from R1 file name."
        if not self.fastq_path_R1:
            return None
        position_re = r".*?_S(\d+)_.*?"
        m = re.match(position_re, self.fastq_path_R1.name)
        if m:
            return int(m.group(1))
        return None

    @computed_field
    @property
    def onboardAnalysisType(self) -> str | None:
        "Return the onboard analysis type based on the R1 file path."
        if not self.fastq_path_R1:
            return None

        if "/DragenGermline/" in str(self.fastq_path_R1):
            return "DragenGermline"
        if "/BCLConvert" in str(self.fastq_path_R1):
            return "BCLConvert"
        return None

    @classmethod
    def from_bclconvert(cls, combined_data: CombinedSampleData) -> SequencingFile:
        sample_guid = UUID_RE.search(combined_data.fastq.sample_id)
        if not sample_guid:
            raise ValueError(
                f"Unable to extract sample GUID from {combined_data.fastq.sample_id}"
            )

        qc1 = combined_data.quality_metrics_read1
        if combined_data.quality_metrics_read2 is None:
            # Create a dummy qc2 to simplify code below - but ensure that yield is zero
            qc2 = QualityMetrics(**qc1.model_dump(by_alias=True))
            qc2.read_number = 2
            qc2.yield_ = 0
            qc2.yield_q30 = 0
            qc2.quality_score_sum = 0

        else:
            qc2 = combined_data.quality_metrics_read2

        return cls(
            RecordId=None,
            SampleGuid=sample_guid.group(),
            FASTQ_path_R1=combined_data.fastq.read1_file,
            FASTQ_path_R2=combined_data.fastq.read2_file,
            FASTQ_path_I1=None,
            FASTQ_path_I2=None,
            SampleName=combined_data.fastq.sample_id,
            AllFilesAvailable=True,  # If we have a CombinedSampleData object, then this is True
            # QC metrics from demux stats:
            readsPf=combined_data.demux_stats.num_reads,
            perfectIndexReadPercent=100
            * combined_data.demux_stats.percent_perfect_index_reads,
            oneMismatchIndexReadPercent=100
            * combined_data.demux_stats.percent_one_mismatch_index_reads,
            pfClustersPercentPerLane=100 * combined_data.demux_stats.percent_reads,
            # Combined qc metrics from qc1 and qc2
            yieldPfGb=(qc1.yield_ + qc2.yield_) / 1_000_000_000,
            basesQ30Percent=100
            * (qc1.yield_q30 + qc2.yield_q30)
            / (qc1.yield_ + qc2.yield_),
            averageQScore=(qc1.quality_score_sum + qc2.quality_score_sum)
            / (qc1.yield_ + qc2.yield_),
        )
