import tempfile
from pathlib import Path

from demux_sapio_watcher.bclconvert.find_folders import find_bclconvert_folders
from tests.conftest import runfolder


def test_find_bclconvert_folders():
    with runfolder([]) as rf:
        folders = list(find_bclconvert_folders([Path(rf.root)]))
        assert len(folders) == 1
        assert folders[0].name == "BCLConvert"

    with runfolder([]) as rf:
        # create another BCLConvert folder
        another_bclconvert = Path(rf.root, "Another", "Path", "BCLConvert")
        another_bclconvert.mkdir(parents=True, exist_ok=True)
        folders = list(find_bclconvert_folders([Path(rf.root)]))
        assert len(folders) == 2
        assert all(folder.name == "BCLConvert" for folder in folders)

    with tempfile.TemporaryDirectory() as tmpdirname:
        with runfolder([], tmpdirname), runfolder([], tmpdirname):
            # Find common root for both runfolders
            folders = list(find_bclconvert_folders([Path(tmpdirname)]))
            assert len(folders) == 2
            assert folders[0].name == "BCLConvert"
            assert folders[1].name == "BCLConvert"
            assert folders[0] != folders[1]  # different paths


def test_find_bclconvert_folders_basic(tmp_path: Path):
    """Test basic BCLConvert folder discovery."""
    # Create test directory structure
    bcl_folder1 = tmp_path / "run1" / "BCLConvert"
    bcl_folder2 = tmp_path / "run2" / "BCLConvert"
    other_folder = tmp_path / "run3" / "OtherFolder"

    bcl_folder1.mkdir(parents=True)
    bcl_folder2.mkdir(parents=True)
    other_folder.mkdir(parents=True)

    # Test finding BCLConvert folders
    root_paths = [tmp_path / "run1", tmp_path / "run2", tmp_path / "run3"]
    bcl_folders = find_bclconvert_folders(root_paths)

    assert len(bcl_folders) == 2
    assert bcl_folder1 in bcl_folders
    assert bcl_folder2 in bcl_folders
    assert other_folder not in bcl_folders

    root_paths = [tmp_path]
    bcl_folders_recursive = find_bclconvert_folders(root_paths)
    assert bcl_folders_recursive == bcl_folders


def test_find_bclconvert_folders_with_excludes(tmp_path: Path):
    """Test BCLConvert folder discovery with exclude patterns."""
    # Create test directory structure
    bcl_folder1 = tmp_path / "run1" / "BCLConvert"
    bcl_folder2 = tmp_path / "processed" / "BCLConvert"  # This should be excluded
    bcl_folder3 = tmp_path / "backup" / "BCLConvert"  # This should be excluded

    bcl_folder1.mkdir(parents=True)
    bcl_folder2.mkdir(parents=True)
    bcl_folder3.mkdir(parents=True)

    # Test with exclude patterns
    # root_paths = [tmp_path / "run1", tmp_path / "processed", tmp_path / "backup"]
    root_paths = [tmp_path]
    bcl_folders = find_bclconvert_folders(
        root_paths, exclude_patterns=["processed", "backup"]
    )

    assert len(bcl_folders) == 1
    assert bcl_folder1 in bcl_folders
    assert bcl_folder2 not in bcl_folders
    assert bcl_folder3 not in bcl_folders


def test_find_bclconvert_folders_empty_roots(tmp_path: Path):
    """Test BCLConvert folder discovery with empty or non-existent root paths."""
    # Create one valid BCL folder
    bcl_folder = tmp_path / "run1" / "BCLConvert"
    bcl_folder.mkdir(parents=True)

    # Test with mix of valid and invalid paths
    root_paths = [
        tmp_path / "run1",  # Valid with BCLConvert
        tmp_path / "nonexistent",  # Non-existent path
        tmp_path / "empty",  # Empty directory
    ]

    # Create empty directory
    (tmp_path / "empty").mkdir()

    bcl_folders = find_bclconvert_folders(root_paths)

    assert len(bcl_folders) == 1
    assert bcl_folder in bcl_folders


def test_find_bclconvert_folders_no_matches(tmp_path: Path):
    """Test BCLConvert folder discovery when no BCLConvert folders exist."""
    # Create directories without BCLConvert folders
    other_folder1 = tmp_path / "run1" / "SomethingElse"
    other_folder2 = tmp_path / "run2" / "AnotherFolder"

    other_folder1.mkdir(parents=True)
    other_folder2.mkdir(parents=True)

    root_paths = [tmp_path / "run1", tmp_path / "run2"]
    bcl_folders = find_bclconvert_folders(root_paths)

    assert len(bcl_folders) == 0


def test_find_bclconvert_folders_case_sensitive(tmp_path: Path):
    """Test that BCLConvert folder discovery is case sensitive."""
    # Create folders with different cases
    correct_case = tmp_path / "run1" / "BCLConvert"
    wrong_case1 = tmp_path / "run2" / "bclconvert"
    wrong_case2 = tmp_path / "run3" / "BclConvert"

    correct_case.mkdir(parents=True)
    wrong_case1.mkdir(parents=True)
    wrong_case2.mkdir(parents=True)

    root_paths = [tmp_path / "run1", tmp_path / "run2", tmp_path / "run3"]
    bcl_folders = find_bclconvert_folders(root_paths)

    # Should only find the correctly cased folder
    assert len(bcl_folders) == 1
    assert correct_case in bcl_folders
    assert wrong_case1 not in bcl_folders
    assert wrong_case2 not in bcl_folders
