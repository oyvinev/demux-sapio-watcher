from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from src import cli


def make_fastq_pair(tmpdir: Path, uuid: str):
    prefix = f"sample-{uuid}"
    r1 = tmpdir / f"{prefix}_R1.fastq"
    r2 = tmpdir / f"{prefix}_R2.fastq"
    r1.write_text("@SEQ\nACGT\n+\n!!!!\n")
    r2.write_text("@SEQ\nTGCA\n+\n!!!!\n")
    return r1, r2


def test_find_fastq_pairs_and_dry_run(tmp_path: Path):
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    r1, r2 = make_fastq_pair(tmp_path, uuid)

    patterns = [str(tmp_path / "**" / "*_R1.fastq")]
    pairs = list(cli.find_fastq_pairs(patterns))
    assert len(pairs) == 1
    found_uuid, found_r1, found_r2 = pairs[0]
    assert found_uuid == UUID(uuid)
    assert Path(found_r1).resolve() == r1.resolve()
    assert Path(found_r2).resolve() == r2.resolve()


def test_cli_updates_sapio(monkeypatch, tmp_path: Path, capsys):
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    r1, r2 = make_fastq_pair(tmp_path, uuid)

    # Use a MagicMock for SapioClient so we can assert calls directly.
    record_obj = SimpleNamespace(uuid=uuid)
    client_mock = MagicMock()
    client_mock.find_sequencingfile_by_uuid.return_value = record_obj

    # Patch the CLI to use our mock client instance
    monkeypatch.setattr(cli, "SapioClient", lambda *a, **k: client_mock)

    patterns = [str(tmp_path / "**" / "*_R1.fastq")]
    # Provide a dummy API token so the CLI validation accepts authentication
    # Run — DummyClient asserts update was called; logging is side-effect only.
    cli.main(["--api-token", "dummy-token", *patterns])

    # Assert the client methods were called as expected
    client_mock.find_sequencingfile_by_uuid.assert_called_once()
    client_mock.update_record.assert_called_once()

    # Check the arguments update_record was called with
    called_args = client_mock.update_record.call_args[0]
    called_record = called_args[0]
    assert called_record.uuid == uuid
    assert Path(called_record.read1_fastq).resolve() == r1.resolve()
    assert Path(called_record.read2_fastq).resolve() == r2.resolve()
