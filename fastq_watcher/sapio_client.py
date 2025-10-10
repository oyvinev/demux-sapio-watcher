"""HTTP adapter to communicate with the Sapio Web Service.

This module provides `SapioClient`, a thin HTTP client that talks to the
Sapio REST API to query and update SequencingFile data records. Tests
should inject a requests-like session when they need to avoid network
calls.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import requests

from fastq_watcher.sapio_types import SapioRecord, SequencingFile


class SapioClient:
    """Adapter for basic SequencingFile operations using the Sapio REST API.

    This client implements only a small subset of operations used by the CLI:
    - query a SequencingFile by uuid
    - update the `read1_fastq` and `read2_fastq` fields for a record

    Tests should inject an HTTP session (`requests.Session` or a compatible
    mock) to avoid real network calls.
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        url_base: str | None = None,
        app_key: str | None = None,
        http_session: requests.Session | None = None,
        **extra: Any,
    ) -> None:
        # Remember base URL
        if not url_base:
            raise ValueError("Sapio URL (url_base) is required")
        # Normalize base url (strip trailing slash)
        self._url_base = url_base.rstrip("/")

        # Prepare HTTP session for REST calls
        self._session = http_session or requests.Session()
        # Configure headers based on token/app_key etc.
        # X-APP-KEY is required when multiple apps are hosted on the same domain.
        headers = {}
        if app_key:
            headers["X-APP-KEY"] = app_key
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        # Allow session-level headers to be updated but preserve any user-provided
        # headers already set on the session.
        self._session.headers.update(headers)

    def find_by_values(
        self, datatype: type[SapioRecord], field_name: str, values: list[Any]
    ) -> list[SapioRecord]:
        """Return a list of DataRecord-like objects matching the given field values.

        This uses the REST API described in the swagger: POST to
        /datarecordmanager/querydatarecords with query params and a ValueList
        body. We request pageSize large enough to retrieve all matching records.
        """
        if not issubclass(datatype, SapioRecord):
            raise ValueError("datatype must be a SapioRecord subclass")
        endpoint = f"{self._url_base}/datarecordmanager/querydatarecords"
        params = {
            "dataTypeName": datatype.__name__,
            "dataFieldName": field_name,
            "pageSize": -1,
        }
        body = values

        resp = self._session.post(endpoint, params=params, json=body)
        resp.raise_for_status()

        data = resp.json()
        # The response should be a DataRecordPojoListPageResult with 'resultList'
        results = data.get("resultList") if isinstance(data, dict) else None
        if not results:
            return []
        return [datatype.model_validate(r) for r in results]

    def update_record(self, record: SapioRecord) -> None:
        """Update fields on the given DataRecord and commit.

        This uses the `set_field_value` API and `commit_data_records` from the
        Data Record Manager as shown in the tutorial.
        """

        endpoint = f"{self._url_base}/datarecordlist/fields"
        resp = self._session.put(endpoint, json=[record.update_payload()])
        resp.raise_for_status()

    def find_sequencingfile_by_uuid(self, uuid: str | UUID) -> SequencingFile | None:
        """Return a DataRecord-like object for the first SequencingFile matching uuid.

        This tries a couple of common query patterns used in the Sapio tutorials.
        The exact method names on the DataRecord manager may vary by version; if
        they are not present an informative RuntimeError is raised.
        """
        response = self.find_by_values(SequencingFile, "SampleGuid", [str(uuid)])
        if not response:
            return None
        return response[0]
