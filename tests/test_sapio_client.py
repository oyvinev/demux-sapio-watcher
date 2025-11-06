from unittest.mock import MagicMock
from uuid import uuid4

from src.sapio_client import SapioClient
from src.sapio_types import SapioRecord


def make_fake_response(result_list):
    class FakeResp:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    return FakeResp({"resultList": result_list})


def test_find_by_uuid():
    uuid = uuid4()
    fake_record = {
        "RecordId": 2,
        "SampleGuid": str(uuid),
        "dataTypeName": "SequencingFile",
        "AllFilesAvailable": False,
    }
    fake_session = MagicMock()
    fake_session.post = MagicMock(return_value=make_fake_response([fake_record]))

    client = SapioClient(
        url_base="https://sapio.example/webservice/api", http_session=fake_session
    )
    res = client.find_sequencingfile_by_uuid(uuid)
    assert res.record_id == 2
    assert res.sample_guid == uuid
    fake_session.post.assert_called()


def test_find_by_uuid_not_found():
    fake_session = MagicMock()
    fake_session.post = MagicMock(return_value=make_fake_response([]))

    client = SapioClient(
        url_base="https://sapio.example/webservice/api", http_session=fake_session
    )
    res = client.find_sequencingfile_by_uuid(uuid4())
    assert res is None


def test_update_record():
    # For REST path, allow passing an object with an 'id' attribute as record id

    plain = SapioRecord(RecordId=11)
    fake_session = MagicMock()
    fake_session.put = MagicMock(
        return_value=MagicMock(raise_for_status=MagicMock(return_value=None))
    )

    client = SapioClient(
        url_base="https://sapio.example/webservice/api", http_session=fake_session
    )
    client.update_record(plain)
    fake_session.put.assert_called()
