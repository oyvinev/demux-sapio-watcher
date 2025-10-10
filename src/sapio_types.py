from pathlib import Path
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class SapioRecord(BaseModel):
    record_id: int = Field(
        ...,
        alias="RecordId",
        description="The system-wide unique ID of this data record",
    )

    def update_payload(self) -> dict:
        "Return a dict suitable for the 'fields' in the set_field_value API."
        return {
            "dataTypeName": self.__class__.__name__,
            "recordId": self.record_id,
            "fields": self.model_dump(by_alias=True),
            "deleted": False,
            "new": False,
        }


class SequencingFile(SapioRecord):
    sample_guid: UUID = Field(
        ...,
        alias="SampleGuid",
        description="The UUID associated with this sequencing file",
    )
    read1_fastq: Path | None = Field(
        None, alias="read1_fastq", description="Path to the R1 FASTQ file"
    )
    read2_fastq: Path | None = Field(
        None, alias="read2_fastq", description="Path to the R2 FASTQ file"
    )
    sample_name: str | None = Field(
        None, alias="SampleName", description="The name of the sample"
    )

    model_config = ConfigDict(extra="ignore")
