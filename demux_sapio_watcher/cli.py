import argparse
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

from demux_sapio_watcher.bclconvert.find_folders import find_bclconvert_folders
from demux_sapio_watcher.bclconvert.parse_folder import parse_bclconvert_folder
from demux_sapio_watcher.sapio_types import SequencingFile

from .sapio_client import SapioClient

# Configure module-level logger
logger = logging.getLogger("demux-sapio-watcher")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def cli(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="fastq-watcher")
    parser.add_argument("root_paths", nargs="+", help="root paths to search")
    parser.add_argument("--exclude-patterns", nargs="+", help="patterns to exclude")
    parser.add_argument("--include-patterns", nargs="+", help="patterns to include")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't update Sapio, just log actions"
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("SAPIO_API_TOKEN"),
        help="Sapio API token (defaults to SAPIO_API_TOKEN env)",
    )
    parser.add_argument(
        "--url-base",
        default=os.environ.get("SAPIO_URL_BASE"),
        help="Sapio base URL (defaults to SAPIO_URL_BASE env)",
    )
    parser.add_argument(
        "--app-key",
        default=os.environ.get("SAPIO_APP_KEY"),
        help="Sapio app key (defaults to SAPIO_APP_KEY env)",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("SAPIO_USERNAME"),
        help="Sapio username (defaults to SAPIO_USERNAME env)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SAPIO_PASSWORD"),
        help="Sapio password (defaults to SAPIO_PASSWORD env)",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set log level",
    )
    parser.add_argument(
        "--no-sapio",
        action="store_true",
        help="Do not call Sapio API at all",
    )
    args = parser.parse_args(argv)

    args.root_paths = [Path(p).resolve() for p in args.root_paths]
    if not args.root_paths:
        raise parser.error("at least one root path is required")

    # Require authentication: either an API token, or username+password.
    if not args.no_sapio:
        if not (args.api_token or (args.username and args.password)):
            parser.error(
                "Authentication required: provide --api-token or both --username and --password"
            )
        if not args.url_base:
            parser.error("Sapio base URL is required: provide --url-base")

    # Configure logger level if requested
    if args.log_level:
        try:
            logger.setLevel(getattr(logging, args.log_level))
        except Exception:
            parser.error(f"invalid log level: {args.log_level}")

    # If API token is provided, prefer it and don't send username/password.
    if not args.no_sapio:
        if args.api_token:
            client = SapioClient(
                api_token=args.api_token, url_base=args.url_base, app_key=args.app_key
            )
        else:
            client = SapioClient(
                url_base=args.url_base,
                app_key=args.app_key,
                # username=args.username,
                # password=args.password,
            )
    else:
        logger.debug("Mocking Sapio, --no-sapio specified")
        client = MagicMock()

    logger.info("Looking for BclConvert folders")
    logger.debug(f"Root paths: {args.root_paths}")
    total_parsed_samples = 0
    total_processed_folders = 0
    for bcl_convert_folder in find_bclconvert_folders(
        args.root_paths,
        include_patterns=args.include_patterns,
        exclude_patterns=args.exclude_patterns,
    ):
        logger.debug(f"Processing BclConvert folder: {bcl_convert_folder}")
        total_processed_folders += 1
        it = parse_bclconvert_folder(bcl_convert_folder)
        num_parsed_samples = 0
        while True:
            try:
                sample_data = next(it)
            except StopIteration:
                break
            except Exception as e:
                logger.warning(f"Failed to parse sample data: {e}")
                continue
            num_parsed_samples += 1

            sequencing_file = SequencingFile.from_bclconvert(sample_data)
            uuid = sequencing_file.sample_guid
            if args.dry_run:
                logger.info(
                    f"DRY RUN: Found and parsed SequencingFile: {sequencing_file}"
                )
                continue
            logger.info(f"Found and parsed SequencingFile: {sequencing_file}")
            record = client.find_sequencingfile_by_uuid(uuid)
            if record is None:
                logger.warning(f"UUID {uuid} not found in Sapio")
                continue
            sequencing_file.record_id = record.record_id
            client.update_record(sequencing_file)
            # logger.info("Updated SequencingFile %s with R1=%s R2=%s", uuid, r1, r2)
        logger.info(
            f"Processed {num_parsed_samples} samples in {bcl_convert_folder.path}"
        )
        total_parsed_samples += num_parsed_samples
    logger.info(f"Total processed BCLConvert folders: {total_processed_folders}")
    logger.info(f"Total parsed samples: {total_parsed_samples}")
    logger.info("Done")


def main(*args) -> None:
    if not args:
        args = (sys.argv[1:],)
    cli(*args)
