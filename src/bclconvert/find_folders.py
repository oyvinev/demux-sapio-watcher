import fnmatch
from pathlib import Path


def filter_folders(
    root_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
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
    if not root_path.exists() or not root_path.is_dir():
        return []

    include_patterns = include_patterns or ["*"]
    exclude_patterns = exclude_patterns or []

    filtered_folders = []

    # Get all direct subdirectories
    for item in root_path.iterdir():
        if not item.is_dir():
            continue

        folder_name = item.name

        # Check if folder matches any exclude pattern
        excluded = any(
            fnmatch.fnmatch(folder_name, pattern) for pattern in exclude_patterns
        )
        if excluded:
            continue

        # Check if folder matches any include pattern
        included = any(
            fnmatch.fnmatch(folder_name, pattern) for pattern in include_patterns
        )
        if included:
            filtered_folders.append(item.resolve())
        else:
            # Recursively search in subdirectories
            filtered_folders += filter_folders(item, include_patterns, exclude_patterns)

    return sorted(filtered_folders)


def find_bclconvert_folders(
    root_paths: list[Path], exclude_patterns: list[str] | None = None
) -> set[Path]:
    """
    Find folders that match the BCL conversion pattern.

    Args:
        root_paths: The root directories to scan

    Returns:
        List of Path objects for folders that match the BCL conversion pattern
    """
    return {
        folder
        for root_path in root_paths
        for folder in filter_folders(
            root_path,
            include_patterns=["BCLConvert"],
            exclude_patterns=exclude_patterns,
        )
    }
