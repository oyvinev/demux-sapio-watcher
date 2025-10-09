from unittest.mock import MagicMock
from uuid import UUID

import importlib
import pytest
import sys
import types


def make_fake_drm_with_query_records(result_list):
    drm = MagicMock()
    drm.query_records = MagicMock(return_value=result_list)
    return drm


def make_fake_drm_with_query(result_list):
    class DRM:
        def query(self, *a, **k):
            return result_list

    return DRM()


# (Assume sapiopylib is installed in the runtime; no test for missing package.)


def test_find_by_uuid_uses_query_records(monkeypatch):
    # Patch SapioUser and DataMgmtServer
    fake_user = MagicMock()
    fake_record = MagicMock()
    fake_record.id = 1
    drm = make_fake_drm_with_query_records([fake_record])

    fake_dms = MagicMock()
    fake_dms.get_data_record_manager = MagicMock(return_value=drm)

    # Use dependency injection to pass fake SapioUser factory and DataMgmtServer
    SapioClient = importlib.import_module('fastq_watcher.sapio_client').SapioClient
    client = SapioClient(url_base='https://sapio.example/webservice/api', sapio_user_factory=lambda **k: fake_user, data_mgmt_server_cls=fake_dms)
    res = client.find_sequencingfile_by_uuid(UUID('123e4567-e89b-12d3-a456-426614174000'))
    assert res is fake_record


def test_find_by_uuid_uses_query(monkeypatch):
    fake_user = MagicMock()
    fake_record = MagicMock()
    drm = make_fake_drm_with_query([fake_record])

    fake_dms = MagicMock()
    fake_dms.get_data_record_manager = MagicMock(return_value=drm)

    SapioClient = importlib.import_module('fastq_watcher.sapio_client').SapioClient
    client = SapioClient(url_base='https://sapio.example/webservice/api', sapio_user_factory=lambda **k: fake_user, data_mgmt_server_cls=fake_dms)
    res = client.find_sequencingfile_by_uuid('123e4567-e89b-12d3-a456-426614174000')
    assert res is fake_record


def test_find_by_uuid_not_found(monkeypatch):
    fake_user = MagicMock()
    drm = make_fake_drm_with_query_records([])

    fake_dms = MagicMock()
    fake_dms.get_data_record_manager = MagicMock(return_value=drm)

    SapioClient = importlib.import_module('fastq_watcher.sapio_client').SapioClient
    client = SapioClient(url_base='https://sapio.example/webservice/api', sapio_user_factory=lambda **k: fake_user, data_mgmt_server_cls=fake_dms)
    res = client.find_sequencingfile_by_uuid('00000000-0000-0000-0000-000000000000')
    assert res is None


def test_update_sequencingfile_paths_set_field_and_commit(monkeypatch):
    fake_user = MagicMock()
    fake_record = MagicMock()
    drm = MagicMock()
    drm.commit_data_records = MagicMock()
    # Data record supports set_field_value
    fake_record.set_field_value = MagicMock()

    fake_dms = MagicMock()
    fake_dms.get_data_record_manager = MagicMock(return_value=drm)

    # Use DI for SapioClient to provide the fake data management server
    SapioClient = importlib.import_module('fastq_watcher.sapio_client').SapioClient
    client = SapioClient(url_base='https://sapio.example/webservice/api', sapio_user_factory=lambda **k: fake_user, data_mgmt_server_cls=fake_dms)
    client.update_sequencingfile_paths(fake_record, '/tmp/r1.fastq', '/tmp/r2.fastq')
    fake_record.set_field_value.assert_any_call('read1_fastq', '/tmp/r1.fastq')
    fake_record.set_field_value.assert_any_call('read2_fastq', '/tmp/r2.fastq')
    drm.commit_data_records.assert_called()


def test_update_sequencingfile_paths_fallback_attribute_and_commit(monkeypatch):
    fake_user = MagicMock()
    # make a simple object without set_field_value
    class Plain:
        pass

    plain = Plain()
    drm = MagicMock()
    drm.commit_data_records = MagicMock()

    fake_dms = MagicMock()
    fake_dms.get_data_record_manager = MagicMock(return_value=drm)

    SapioClient = importlib.import_module('fastq_watcher.sapio_client').SapioClient
    client = SapioClient(url_base='https://sapio.example/webservice/api', sapio_user_factory=lambda **k: fake_user, data_mgmt_server_cls=fake_dms)
    client.update_sequencingfile_paths(plain, '/tmp/r1.fastq', '/tmp/r2.fastq')
    assert getattr(plain, 'read1_fastq') == '/tmp/r1.fastq'
    assert getattr(plain, 'read2_fastq') == '/tmp/r2.fastq'
    drm.commit_data_records.assert_called()
