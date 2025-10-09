"""CLI to locate FASTQ R1/R2 pairs and update Sapio SequencingFile records.

This CLI is intentionally small and testable. It accepts glob patterns and
walks the filesystem for files matching `*_R1.fastq` and corresponding
`*_R2.fastq`.
"""

from __future__ import annotations


import argparse
import glob
import os
from pathlib import Path
import re
from typing import Iterable, Iterator, Tuple, Optional, List
from uuid import UUID

from .sapio_client import SapioClient

import logging
import sys

# Configure module-level logger
logger = logging.getLogger("fastq-sapio-watcher")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def find_fastq_pairs(globs: Iterable[str]) -> Iterator[Tuple[UUID, str, str]]:
    """Yield tuples (uuid, r1_path, r2_path) for discovered FASTQ pairs.

    The expected filename format is <prefix>_R1.fastq and <prefix>_R2.fastq where
    <prefix> contains a UUID which will be extracted.
    """
    r1_files: List[str] = []
    for pattern in globs:
        r1_files.extend(glob.glob(pattern, recursive=True))

    seen = set()
    for path_str in r1_files:
        p: Path = Path(path_str)
        if not p.name.endswith("_R1.fastq"):
            continue
        prefix = p.name[:-len("_R1.fastq")]
        r2_path = p.with_name(prefix + "_R2.fastq")
        if not r2_path.exists():
            continue
        m = UUID_RE.search(prefix)
        if not m:
            continue
        uuid = UUID(m.group(0))
        r1_abs = str(p.resolve())
        r2_abs = str(r2_path.resolve())
        key = (uuid, r1_abs, r2_abs)
        if key in seen:
            continue
        seen.add(key)
    yield uuid, r1_abs, r2_abs


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="fastq-watcher")
    parser.add_argument("patterns", nargs="+", help="glob patterns to search")
    parser.add_argument("--dry-run", action="store_true", help="don't call Sapio, just print")
    parser.add_argument("--api-token", default=os.environ.get("SAPIO_API_TOKEN"), help="Sapio API token (defaults to SAPIO_API_TOKEN env)")
    parser.add_argument("--url-base", default=os.environ.get("SAPIO_URL_BASE"), help="Sapio base URL (defaults to SAPIO_URL_BASE env)")
    parser.add_argument("--app-key", default=os.environ.get("SAPIO_APP_KEY"), help="Sapio app key (defaults to SAPIO_APP_KEY env)")
    parser.add_argument("--username", default=os.environ.get("SAPIO_USERNAME"), help="Sapio username (defaults to SAPIO_USERNAME env)")
    parser.add_argument("--password", default=os.environ.get("SAPIO_PASSWORD"), help="Sapio password (defaults to SAPIO_PASSWORD env)")
    parser.add_argument("--log-level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set log level")
    args = parser.parse_args(argv)

    # Require authentication: either an API token, or username+password.
    if not (args.api_token or (args.username and args.password)):
        parser.error("Authentication required: provide --api-token or both --username and --password")

    # Configure logger level if requested
    if args.log_level:
        try:
            logger.setLevel(getattr(logging, args.log_level))
        except Exception:
            parser.error(f"invalid log level: {args.log_level}")

    # If API token is provided, prefer it and don't send username/password.
    if args.api_token:
        client = SapioClient(api_token=args.api_token, url_base=args.url_base, app_key=args.app_key)
    else:
        client = SapioClient(url_base=args.url_base, app_key=args.app_key, username=args.username, password=args.password)

    for uuid, r1, r2 in find_fastq_pairs(args.patterns):
        if args.dry_run:
            logger.info("Found UUID=%s, R1=%s, R2=%s", uuid, r1, r2)
            continue
        record = client.find_sequencingfile_by_uuid(uuid)
        if record is None:
            logger.warning("UUID %s not found in Sapio", uuid)
            continue
        client.update_sequencingfile_paths(record, r1, r2)
        logger.info("Updated SequencingFile %s with R1=%s R2=%s", uuid, r1, r2)
