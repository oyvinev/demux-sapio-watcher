import fnmatch
import logging
from pathlib import Path

from pydantic import ValidationError

from demux_sapio_watcher.bclconvert.models import BCLConvertFolder

logger = logging.getLogger("demux-sapio-watcher")


def matches(p: str, patterns: list[str]) -> bool:
    """Determine if the given path matches any of the provided patterns."""

    return any(fnmatch.fnmatch(p, pat) for pat in patterns)


def filter_folders(
    root_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    _top_level: Path | None = None,
) -> list[Path]:
    """
    Filter folders based on include and exclude patterns.

    Args:
        root_path: The root directory to scan
        include_patterns: List of glob patterns to include (if None, includes all)
        exclude_patterns: List of glob patterns to exclude

    Returns:
        List of Path objects for folders that match criteria
    """
    filtered_folders = []
    if not root_path.exists():
        logger.warning(f"Root path {root_path} does not exist")
        return []
    if not root_path.is_dir():
        logger.warning(f"Root path {root_path} is not a directory")
        return []
    if not _top_level:
        included = matches(str(root_path), include_patterns or ["*"])
        if included:
            filtered_folders.append(root_path.resolve())
        _top_level = root_path

    include_patterns = include_patterns or ["*"]
    exclude_patterns = exclude_patterns or []

    # Get all direct subdirectories
    for item in root_path.iterdir():
        if not item.is_dir():
            continue

        relative_path = item.relative_to(_top_level)

        # Check if folder matches any exclude pattern
        excluded = matches(str(relative_path), exclude_patterns)

        if excluded:
            continue

        # Check if folder matches any include pattern
        included = matches(str(relative_path), include_patterns)
        if included:
            filtered_folders.append(item.resolve())
        filtered_folders += filter_folders(
            item, include_patterns, exclude_patterns, _top_level=_top_level
        )

    return sorted(filtered_folders)


def find_bclconvert_folders(
    root_paths: list[Path],
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> set[BCLConvertFolder]:
    """
    Find folders that match the BCL conversion pattern.

    Args:
        root_paths: The root directories to scan

    Returns:
        List of Path objects for folders that match the BCL conversion pattern
    """
    bcl_convert_folders = set()
    for root_path in root_paths:
        for folder in filter_folders(
            root_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        ):
            if (folder / "BCLConvert").is_dir():
                try:
                    bcl_convert_folders.add(BCLConvertFolder.from_path(folder))
                except ValidationError as e:
                    logger.error(f"Error parsing BCLConvert folder at {folder}: {e}")
                    continue

    return bcl_convert_folders
