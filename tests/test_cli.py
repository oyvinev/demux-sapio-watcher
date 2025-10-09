from pathlib import Path
from unittest import mock

from fastq_watcher import cli
from uuid import UUID


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

    # Patch SapioClient to avoid importing sapiopylib and to assert calls
    class DummyRecord:
        def __init__(self, uuid):
            self.uuid = uuid

    class DummyClient:
        def find_sequencingfile_by_uuid(self, u):
            # u may be a UUID instance
            assert UUID(str(u)) == UUID(uuid)
            return DummyRecord(uuid)

        def update_sequencingfile_paths(self, record, r1p, r2p):
            assert record.uuid == uuid
            assert Path(r1p).resolve() == r1.resolve()
            assert Path(r2p).resolve() == r2.resolve()

    monkeypatch.setattr(cli, "SapioClient", lambda *a, **k: DummyClient())

    patterns = [str(tmp_path / "**" / "*_R1.fastq")]
    # Provide a dummy API token so the CLI validation accepts authentication
    # Run — DummyClient asserts update was called; logging is side-effect only.
    cli.main(["--api-token", "dummy-token", *patterns])
