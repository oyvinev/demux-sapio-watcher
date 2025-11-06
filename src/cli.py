import argparse
import logging
import os
import sys
from pathlib import Path

from src.bclconvert.find_folders import find_bclconvert_folders
from src.bclconvert.parse_folder import parse_bclconvert_folder
from src.sapio_types import SequencingFile


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="fastq-watcher")
    parser.add_argument("root_paths", nargs="+", help="root paths to search")
    parser.add_argument("--exclude-patterns", nargs="+", help="patterns to exclude")
    parser.add_argument(
        "--dry-run", action="store_true", help="don't call Sapio, just print"
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
    args = parser.parse_args()

    args.root_paths = [Path(p) for p in args.root_paths]

    # Require authentication: either an API token, or username+password.
    if not (args.api_token or (args.username and args.password)):
        parser.error(
            "Authentication required: provide --api-token or both --username and --password"
        )

    # Configure logger level if requested
    if args.log_level:
        try:
            logger.setLevel(getattr(logging, args.log_level))
        except Exception:
            parser.error(f"invalid log level: {args.log_level}")

    # If API token is provided, prefer it and don't send username/password.
    if args.api_token:
        client = SapioClient(
            api_token=args.api_token, url_base=args.url_base, app_key=args.app_key
        )
    else:
        client = SapioClient(
            url_base=args.url_base,
            app_key=args.app_key,
            username=args.username,
            password=args.password,
        )

    for bcl_convert_folder in find_bclconvert_folders(
        args.root_paths, exclude_patterns=args.exclude_patterns
    ):
        it = parse_bclconvert_folder(bcl_convert_folder)
        while True:
            try:
                sample_data = next(it)
            except StopIteration:
                break
            except Exception as e:
                logger.warning(f"Failed to parse sample data: {e}")
                continue

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


if __name__ == "__main__":
    main()
