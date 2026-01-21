import tempfile
from pathlib import Path

from demux_sapio_watcher.bclconvert.find_folders import find_bclconvert_folders
from tests.conftest import runfolder


def test_find_bclconvert_folders():
    with runfolder([]) as rf:
        folders = list(find_bclconvert_folders([Path(rf.root)]))
        assert len(folders) == 1
        assert (folders[0].path / "BCLConvert").is_dir()

    with runfolder([]) as rf:
        # create another BCLConvert folder
        another_bclconvert = Path(rf.root, "Another", "Path", "BCLConvert")
        another_bclconvert.mkdir(parents=True, exist_ok=True)
        (another_bclconvert / "../Demultiplex_Stats.csv").touch()
        (another_bclconvert / "../Quality_Metrics.csv").touch()
        (another_bclconvert / "../fastq_list.csv").touch()
        (another_bclconvert / "../../CopyComplete.txt").touch()

        incomplete_bclconvert = Path(rf.root, "Incomplete", "Folder", "BCLConvert")
        incomplete_bclconvert.mkdir(parents=True, exist_ok=True)
        (incomplete_bclconvert / "../Demultiplex_Stats.csv").touch()
        (incomplete_bclconvert / "../Quality_Metrics.csv").touch()

        no_marker_bclconvert = Path(rf.root, "NoMarker", "Folder", "BCLConvert")
        no_marker_bclconvert.mkdir(parents=True, exist_ok=True)
        (no_marker_bclconvert / "../Demultiplex_Stats.csv").touch()
        (no_marker_bclconvert / "../Quality_Metrics.csv").touch()
        (no_marker_bclconvert / "../fastq_list.csv").touch()

        folders = list(find_bclconvert_folders([Path(rf.root)]))
        assert len(folders) == 2
        assert (folders[0].path / "BCLConvert").is_dir()
        assert (folders[1].path / "BCLConvert").is_dir()

    with tempfile.TemporaryDirectory() as tmpdirname:
        with runfolder([], tmpdirname), runfolder([], tmpdirname):
            # Find common root for both runfolders
            folders = list(find_bclconvert_folders([Path(tmpdirname)]))
            assert len(folders) == 2
            assert (folders[0].path / "BCLConvert").is_dir()
            assert (folders[1].path / "BCLConvert").is_dir()
            assert folders[0] != folders[1]  # different paths


def test_find_bclconvert_folders_basic(tmp_path: Path):
    """Test basic BCLConvert folder discovery."""
    # Create test directory structure
    bcl_folder1 = tmp_path / "run1" / "foo" / "bar" / "BCLConvert"
    bcl_folder2 = tmp_path / "run2" / "dabla" / "baz" / "BCLConvert"
    other_folder = tmp_path / "run3" / "OtherFolder"

    bcl_folder1.mkdir(parents=True)
    bcl_folder2.mkdir(parents=True)
    other_folder.mkdir(parents=True)

    for folder in [bcl_folder1, bcl_folder2, other_folder]:
        (folder / "../Demultiplex_Stats.csv").touch()
        (folder / "../Quality_Metrics.csv").touch()
        (folder / "../fastq_list.csv").touch()
        (folder / "../../CopyComplete.txt").touch()

    # Test finding BCLConvert folders
    root_paths = [tmp_path / "run1", tmp_path / "run2", tmp_path / "run3"]
    bcl_folders = find_bclconvert_folders(root_paths)

    assert len(bcl_folders) == 2
    assert bcl_folder1.parent in [b.path for b in bcl_folders]
    assert bcl_folder2.parent in [b.path for b in bcl_folders]
    assert other_folder not in [b.path for b in bcl_folders]

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

    for folder in [bcl_folder1, bcl_folder2, bcl_folder3]:
        (folder / "../Demultiplex_Stats.csv").touch()
        (folder / "../Quality_Metrics.csv").touch()
        (folder / "../fastq_list.csv").touch()
        (folder / "../../CopyComplete.txt").touch()

    # Test with exclude patterns
    # root_paths = [tmp_path / "run1", tmp_path / "processed", tmp_path / "backup"]
    root_paths = [tmp_path]
    bcl_folders = find_bclconvert_folders(
        root_paths, exclude_patterns=["processed", "backup"]
    )

    assert len(bcl_folders) == 1
    assert [b.path for b in bcl_folders] == [bcl_folder1.parent]


def test_find_bclconvert_folders_empty_roots(tmp_path: Path):
    """Test BCLConvert folder discovery with empty or non-existent root paths."""
    # Create one valid BCL folder
    bcl_folder = tmp_path / "run1" / "BCLConvert"
    bcl_folder.mkdir(parents=True)
    (bcl_folder / "../Demultiplex_Stats.csv").touch()
    (bcl_folder / "../Quality_Metrics.csv").touch()
    (bcl_folder / "../fastq_list.csv").touch()
    (bcl_folder / "../../CopyComplete.txt").touch()

    # Create empty directory
    (tmp_path / "empty").mkdir()
    # Test with mix of valid and invalid paths
    root_paths = [
        tmp_path / "run1",  # Valid with BCLConvert
        tmp_path / "nonexistent",  # Non-existent path
        tmp_path / "empty",  # Empty directory
    ]

    bcl_folders = find_bclconvert_folders(root_paths)

    assert len(bcl_folders) == 1
    assert [b.path for b in bcl_folders] == [bcl_folder.parent]


def test_find_bclconvert_folders_no_matches(tmp_path: Path):
    """Test BCLConvert folder discovery when no BCLConvert folders exist."""
    # Create directories without BCLConvert folders
    other_folder1 = tmp_path / "run1" / "SomethingElse"
    other_folder2 = tmp_path / "run2" / "AnotherFolder"

    other_folder1.mkdir(parents=True)
    other_folder2.mkdir(parents=True)

    # other_folder1 contains required files but no BCLConvert folder
    (other_folder1 / "Demultiplex_Stats.csv").touch()
    (other_folder1 / "Quality_Metrics.csv").touch()
    (other_folder1 / "fastq_list.csv").touch()

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

    for folder in [correct_case, wrong_case1, wrong_case2]:
        (folder / "../Demultiplex_Stats.csv").touch()
        (folder / "../Quality_Metrics.csv").touch()
        (folder / "../fastq_list.csv").touch()
        (folder / "../../CopyComplete.txt").touch()

    root_paths = [tmp_path / "run1", tmp_path / "run2", tmp_path / "run3"]
    bcl_folders = find_bclconvert_folders(root_paths)

    # Should only find the correctly cased folder
    assert len(bcl_folders) == 1
    assert [b.path for b in bcl_folders] == [correct_case.parent]
