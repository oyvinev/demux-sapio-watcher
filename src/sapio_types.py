import re
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.bclconvert.models import CombinedSampleData

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
            "fields": self.model_dump(by_alias=True, exclude={"record_id"}),
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

    @classmethod
    def from_bclconvert(cls, combined_data: CombinedSampleData) -> "SequencingFile":
        sample_guid = UUID_RE.search(combined_data.fastq.sample_id)
        if not sample_guid:
            raise ValueError(
                f"Unable to extract sample GUID from {combined_data.fastq.sample_id}"
            )
        return cls(
            RecordId=None,
            SampleGuid=sample_guid.group(),
            FASTQ_path_R1=combined_data.fastq.read1_file,
            FASTQ_path_R2=combined_data.fastq.read2_file,
            FASTQ_path_I1=None,
            FASTQ_path_I2=None,
            SampleName=combined_data.fastq.sample_id,
            AllFilesAvailable=True,  # If we have a CombinedSampleData object, then this is True
        )
