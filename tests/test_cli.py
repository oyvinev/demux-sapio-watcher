# from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import hypothesis as ht
from pydantic import BaseModel, ConfigDict
from pytest import MonkeyPatch

from demux_sapio_watcher import cli
from demux_sapio_watcher.sapio_types import SequencingFile
from tests.conftest import runfolder
from tests.data_generation import (
    PairedReadSampleTestData,
    build_paired_read_sample,
    build_samples,
)


class SimpleNamespace(BaseModel):
    record_id: int
    uuid: UUID

    model_config = ConfigDict(extra="allow")


@ht.given(build_paired_read_sample())
def test_cli_updates_sapio(sample: PairedReadSampleTestData):
    with runfolder([sample]) as rf, MonkeyPatch().context() as mp:
        # Use a MagicMock for SapioClient so we can assert calls directly.
        record_obj = SimpleNamespace(record_id=1, uuid=sample.uuid)
        client_mock = MagicMock()
        # Patch the CLI to use our mock client instance
        mp.setattr(cli, "SapioClient", lambda *a, **k: client_mock)

        client_mock.find_sequencingfile_by_uuid.return_value = record_obj

        # Provide a dummy API token so the CLI validation accepts authentication
        # Run — DummyClient asserts update was called; logging is side-effect only.
        cli.main(
            [
                "--url-base",
                "http://not-used",
                "--api-token",
                "dummy-token",
                rf.root.as_posix(),
            ]
        )

        # Assert the client methods were called as expected
        client_mock.find_sequencingfile_by_uuid.assert_called_once()
        client_mock.update_record.assert_called_once()

        # Check the arguments update_record was called with
        called_args = client_mock.update_record.call_args[0]
        update_record = called_args[0]
        assert isinstance(update_record, SequencingFile)
        assert update_record.sample_guid == sample.uuid
        assert update_record.fastq_path_R1
        assert update_record.fastq_path_R2
        assert update_record.fastq_path_R1.name == sample.fastq_read1_path.name
        assert update_record.fastq_path_R2.name == sample.fastq_read2_path.name


@ht.given(build_samples())
def test_cli_processes_all_samples(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf, MonkeyPatch().context() as mp:
        # Patch the CLI to use our mock client instance

        # Use a MagicMock for SapioClient so we can assert calls directly.
        client_mock = MagicMock()
        mp.setattr(cli, "SapioClient", lambda *a, **k: client_mock)
        record_objs = {
            sample.uuid: SimpleNamespace(record_id=i, uuid=sample.uuid)
            for i, sample in enumerate(samples, start=1)
        }
        client_mock.find_sequencingfile_by_uuid.side_effect = lambda uuid: record_objs[
            uuid
        ]

        # Provide a dummy API token so the CLI validation accepts authentication
        # Run — DummyClient asserts update was called; logging is side-effect only.
        cli.main(
            [
                "--url-base",
                "http://not-used",
                "--api-token",
                "dummy-token",
                rf.root.as_posix(),
            ]
        )
        assert client_mock.find_sequencingfile_by_uuid.call_count == len(samples)
        assert client_mock.update_record.call_count == len(samples)

        update_records = [arg[0][0] for arg in client_mock.update_record.call_args_list]
        assert len(update_records) == len(samples)
        assert all(isinstance(arg, SequencingFile) for arg in update_records)
        for arg in update_records:
            corresponding_sample = next(
                sample for sample in samples if sample.uuid == arg.sample_guid
            )
            assert corresponding_sample.fastq_read1_path.name == arg.fastq_path_R1.name
            assert corresponding_sample.fastq_read2_path.name == arg.fastq_path_R2.name


@ht.given(build_samples())
def test_cli_does_not_update_non_existing_sapio_records(
    samples: list[PairedReadSampleTestData],
):
    with runfolder(samples) as rf, MonkeyPatch().context() as mp:
        # Use a MagicMock for SapioClient so we can assert calls directly.
        client_mock = MagicMock()
        client_mock.find_sequencingfile_by_uuid.return_value = None

        # Patch the CLI to use our mock client instance
        mp.setattr(cli, "SapioClient", lambda *a, **k: client_mock)

        cli.main(
            [
                "--url-base",
                "http://not-used",
                "--api-token",
                "dummy-token",
                rf.root.as_posix(),
            ]
        )
        assert client_mock.find_sequencingfile_by_uuid.call_count == len(samples)
        client_mock.update_record.assert_not_called()


@ht.given(build_samples())
def test_cli_does_not_update_already_updated_records(
    samples: list[PairedReadSampleTestData],
):
    with runfolder(samples) as rf, MonkeyPatch().context() as mp:
        # Use a MagicMock for SapioClient so we can assert calls directly.
        client_mock = MagicMock()
        record_objs = {
            sample.uuid: SimpleNamespace(record_id=1, uuid=sample.uuid)
            for sample in samples
        }
        client_mock.find_sequencingfile_by_uuid.side_effect = lambda uuid: record_objs[
            uuid
        ]

        # Patch the CLI to use our mock client instance
        mp.setattr(cli, "SapioClient", lambda *a, **k: client_mock)

        cli.main(
            [
                "--url-base",
                "http://not-used",
                "--api-token",
                "dummy-token",
                rf.root.as_posix(),
            ]
        )
        assert client_mock.find_sequencingfile_by_uuid.call_count == len(samples)

        # Extract the SequencingFile instances passed to update_record
        update_records = [arg[0][0] for arg in client_mock.update_record.call_args_list]
        assert len(update_records) == len(samples)

        # Now, run it again, simulating that the records are already updated
        client_mock2 = MagicMock()
        client_mock2.find_sequencingfile_by_uuid.side_effect = lambda uuid: next(
            r for r in update_records if r.sample_guid == uuid
        )
        mp.setattr(cli, "SapioClient", lambda *a, **k: client_mock2)
        cli.main(
            [
                "--url-base",
                "http://not-used",
                "--api-token",
                "dummy-token",
                rf.root.as_posix(),
            ]
        )
        assert client_mock2.find_sequencingfile_by_uuid.call_count == len(samples)
        # Ensure update_record was not called again
        client_mock2.update_record.assert_not_called()
