"""HTTP adapter to communicate with the Sapio Web Service.

This module provides `SapioClient`, a thin HTTP client that talks to the
Sapio REST API to query and update SequencingFile data records. Tests
should inject a requests-like session when they need to avoid network
calls.
"""

import logging
from typing import Any, TypeVar, get_args
from uuid import UUID

import requests
from pydantic import BaseModel
from requests.auth import HTTPBasicAuth

from demux_sapio_watcher.sapio_types import SapioRecord, SequencingFile

logger = logging.getLogger("demux-sapio-watcher")

TSapioRecord = TypeVar("TSapioRecord", bound=SapioRecord)


class VeloxFieldListResponse(BaseModel):
    dataFieldType: str
    dataFieldName: str

    @property
    def valid_pydantic_types(self) -> tuple[type, ...]:
        """Return the corresponding Pydantic type for this field."""
        mapping = {
            "STRING": (str, UUID),
            "INTEGER": (int,),
            "LONG": (int,),
            "DOUBLE": (float,),
            "BOOLEAN": (bool,),
            "DATE": (str,),
            "IDENTIFIER": (str,),
        }
        return mapping[self.dataFieldType.upper()]


def get_invalid_sapiorecords(client: SapioClient) -> set[type[SapioRecord]]:
    """Verify that all SapioRecord datamodels can be used with the given client."""

    def recursive_subclasses(cls: type[SapioRecord]) -> list[type[SapioRecord]]:
        """Return a list of all subclasses of the given class, recursively."""
        subs = []
        for subclass in cls.__subclasses__():
            subs.append(subclass)
            subs.extend(recursive_subclasses(subclass))
        return subs

    all_subclasses = recursive_subclasses(SapioRecord)
    invalid_classes = set()
    for cls in all_subclasses:
        url = f"{client._api_base}/datatypemanager/veloxfieldlist/{cls.__name__}"
        response = client._session.get(
            url,
            verify=client._verify_certificates,
        )
        response.raise_for_status()
        if response.status_code != 200:
            invalid_classes.add(cls)
            logger.error(
                f"SapioRecord '{cls.__name__}' not found in Sapio (status code {response.status_code})"
            )
            continue
        sapio_fields = [VeloxFieldListResponse(**item) for item in response.json()]
        logger.debug(f"Available Sapio fields for '{cls.__name__}': {sapio_fields}")
        logger.debug(f"Pydantic fields for '{cls.__name__}': {cls.model_fields}")
        for field, field_info in cls.model_fields.items():
            try:
                matching_field = next(
                    f
                    for f in sapio_fields
                    if f.dataFieldName == field or f.dataFieldName == field_info.alias
                )
            except StopIteration:
                invalid_classes.add(cls)
                logger.error(
                    f"SapioRecord '{cls.__name__}' field '{field}' not found in Sapio"
                )
            field_annotation = set(get_args(field_info.annotation))

            # Check if there is any overlap between the Sapio field type and the Pydantic field types
            if not (field_annotation | set(matching_field.valid_pydantic_types)):
                invalid_classes.add(cls)
                logger.error(
                    f"SapioRecord '{cls.__name__}' field '{field}' has incompatible types: "
                    f"Sapio field type {matching_field.dataFieldType} "
                    f"vs Pydantic types {field_annotation}"
                )
    if invalid_classes:
        logger.error(
            f"Found incompatible SapioRecord datamodels: "
            f"{', '.join(cls.__name__ for cls in invalid_classes)}"
        )
    return invalid_classes


class SapioClient:
    """Adapter for basic SequencingFile operations using the Sapio REST API.

    This client implements only a small subset of operations used by the CLI:
    - Query for a record with a corresponding SapioRecord class
    - Update a record from a SapioRecord instance
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        url_base: str | None = None,
        app_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_certificates: bool = False,
        http_session: requests.Session | None = None,
    ) -> None:
        # Remember base URL
        if not url_base:
            raise ValueError("Sapio URL (url_base) is required")
        # Normalize base url (strip trailing slash)
        self._url_base = url_base.rstrip("/")
        self._api_base = self._url_base + "/webservice/api"

        # Prepare HTTP session for REST calls
        self._session = http_session or requests.Session()
        self._verify_certificates = verify_certificates
        self._session.verify = verify_certificates
        # Configure headers based on token/app_key etc.
        # X-APP-KEY is required when multiple apps are hosted on the same domain.
        headers = {}
        if app_key:
            headers["X-APP-KEY"] = app_key
        if api_token:
            if username or password:
                logger.warning(
                    "Both API token and username/password provided; using API token"
                )
            headers["X-API-TOKEN"] = api_token
        elif username and password:
            # Use basic auth header
            self._session.auth = HTTPBasicAuth(username, password)
        # Allow session-level headers to be updated but preserve any user-provided
        # headers already set on the session.
        self._session.headers.update(headers)
        if invalid_classes := get_invalid_sapiorecords(self):
            raise ValueError(
                f"SapioRecord datamodels '{invalid_classes}' are incompatible with Sapio"
            )

    def find_by_values(
        self, datatype: type[TSapioRecord], field_name: str, values: list[Any]
    ) -> list[TSapioRecord]:
        """Return a list of DataRecord-like objects matching the given field values.

        This uses the REST API described in the swagger: POST to
        /datarecordmanager/querydatarecords with query params and a ValueList
        body. We request pageSize large enough to retrieve all matching records.
        """
        if not issubclass(datatype, SapioRecord):
            raise ValueError("datatype must be a SapioRecord subclass")
        endpoint = f"{self._api_base}/datarecordmanager/querydatarecords"
        params: dict[str, int | str] = {
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
        return [datatype.model_validate(r["fields"]) for r in results]

    def update_record(self, record: SapioRecord) -> None:
        """Update fields on the given DataRecord and commit."""

        endpoint = f"{self._api_base}/datarecordlist/fields"
        resp = self._session.put(endpoint, json=[record.update_payload()])
        resp.raise_for_status()

    def find_sequencingfile_by_uuid(self, uuid: str | UUID) -> SequencingFile | None:
        """Return a DataRecord-like object for the first SequencingFile matching uuid."""
        response = self.find_by_values(SequencingFile, "SampleGuid", [str(uuid)])
        if not response:
            return None
        return response[0]
