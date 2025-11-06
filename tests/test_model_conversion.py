from pathlib import Path
from src.bclconvert.parse_folder import parse_bclconvert_folder
from src.bclconvert.find_folders import find_bclconvert_folders
from src.sapio_types import SequencingFile
from tests.conftest import runfolder
from tests.data_generation import PairedReadSampleTestData, build_samples

import hypothesis as ht
@ht.given(build_samples())
def test_conversion(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        converted = [SequencingFile.from_bclconvert(item) for item in data]
        assert len(converted) == len(data)

@ht.given(build_samples())
def test_payload(samples: list[PairedReadSampleTestData]):
    with runfolder(samples) as rf:
        bclconvert_folders = find_bclconvert_folders([Path(rf.root)])
        assert len(bclconvert_folders) == 1
        bclconvert_folder = bclconvert_folders.pop()
        data = list(parse_bclconvert_folder(bclconvert_folder))
        converted = [SequencingFile.from_bclconvert(item) for item in data]
        assert len(converted) == len(data)
        for item in converted:
            payload = item.update_payload()
            assert "dataTypeName" in payload
            assert "recordId" in payload
            assert "fields" in payload