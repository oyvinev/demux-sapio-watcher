"""Adapter to communicate with Sapio (sapiopylib).

This module isolates Sapio usage so tests can monkeypatch the client class.
If sapiopylib is not installed, the adapter will raise on use.
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID
from sapiopylib.rest.User import SapioUser
from sapiopylib.rest.DataMgmtService import DataMgmtServer


class SapioClient:
    """Adapter for basic SequencingFile operations using sapiopylib.

    This follows the patterns in the Sapio Python tutorials:
    - create a SapioUser
    - obtain a DataRecord manager via DataMgmtServer.get_data_record_manager(user)
    - query records, set fields via `set_field_value`, and commit via
      `commit_data_records`.

    This module imports the required sapiopylib classes at module import time
    (no lazy imports). Tests should ensure a fake `sapiopylib` package is
    available in `sys.modules` before importing this module when running in
    environments without the real package installed.
    """

    def __init__(
        self,
        *,
        api_token: str | None = None,
        url_base: str | None = None,
        app_key: str | None = None,
        guid: str | None = None,
        username: str | None = None,
        password: str | None = None,
        # Dependency injection hooks for testing: a callable that returns
        # a SapioUser-like object and a DataMgmtServer-like class/object.
        sapio_user_factory: Callable[..., Any] | None = None,
        data_mgmt_server_cls: Any | None = None,
        **extra: Any,
    ) -> None:
        # Select the classes/factories to use (injection for tests or real
        # sapiopylib types by default).
        user_cls = sapio_user_factory or SapioUser
        dms_cls = data_mgmt_server_cls or DataMgmtServer

        # Map parameters to the SapioUser signature exactly. The SapioUser
        # constructor requires `url` as the first argument. If it's missing
        # we raise a clear error to the caller.
        user_kwargs: dict[str, Any] = {}
        if url_base:
            user_kwargs["url"] = url_base
        else:
            raise ValueError("Sapio URL (url_base) is required to construct SapioUser")

        # Match SapioUser parameter names
        if api_token:
            user_kwargs["api_token"] = api_token
        if guid:
            user_kwargs["guid"] = guid
        if app_key:
            user_kwargs["account_name"] = app_key
        if username:
            user_kwargs["username"] = username
        if password:
            user_kwargs["password"] = password

        # Allow extra kwargs to be forwarded as well
        user_kwargs.update(extra)

        # Create SapioUser (or fallback to no-arg constructor)
        self._user = user_cls(**user_kwargs) if user_kwargs else user_cls()
        # Resolve the data record manager using the selected DataMgmtServer
        # class/object.
        self._drm = dms_cls.get_data_record_manager(self._user)

    def find_sequencingfile_by_uuid(self, uuid: str | UUID) -> Any | None:
        """Return a DataRecord-like object for the first SequencingFile matching uuid.

        This tries a couple of common query patterns used in the Sapio tutorials.
        The exact method names on the DataRecord manager may vary by version; if
        they are not present an informative RuntimeError is raised.
        """
        # Common pattern: a query by field. Some DataRecord managers expose
        # `query_records` or `query` methods. Try a best-effort approach.
        try:
            # Attempt a generic query_records(filters=...)
            uuid_str = str(uuid)
            if hasattr(self._drm, "query_records"):
                results = self._drm.query_records("SequencingFile", filters={"uuid": uuid_str})
            elif hasattr(self._drm, "query"):
                results = self._drm.query("SequencingFile", {"uuid": uuid_str})
            else:
                # Fall back to a less structured API if available.
                raise AttributeError("no query API found on data record manager")
        except AttributeError as exc:
            raise RuntimeError(
                "DataRecord manager does not expose a query API; check sapiopylib version"
            ) from exc

        if not results:
            return None

        # Return the first matching record. In the Sapio tutorials this is a
        # DataRecord object which supports `set_field_value` and other helpers.
        return results[0]

    def update_sequencingfile_paths(self, record: Any, r1_path: str, r2_path: str) -> None:
        """Set fields `read1_fastq` and `read2_fastq` on the given DataRecord and commit.

        This uses the `set_field_value` API and `commit_data_records` from the
        Data Record Manager as shown in the tutorial.
        """
        # The DataRecord object in sapiopylib exposes `set_field_value`.
        if not hasattr(record, "set_field_value"):
            # Some APIs may return plain dicts; try to set attributes as fallback.
            try:
                setattr(record, "read1_fastq", r1_path)
                setattr(record, "read2_fastq", r2_path)
            except Exception as exc:
                raise RuntimeError("Record object doesn't support field setting") from exc
            # If we cannot call commit_data_records without the original manager,
            # attempt to detect a manager on the record or raise.
            if hasattr(self._drm, "commit_data_records"):
                try:
                    self._drm.commit_data_records([record])
                    return
                except Exception:
                    raise RuntimeError("Failed to commit changes to record")
            raise RuntimeError("Cannot commit changes: no commit API available")

        # Preferred path: use set_field_value and commit via the manager
        record.set_field_value("read1_fastq", r1_path)
        record.set_field_value("read2_fastq", r2_path)
        # Commit via data record manager
        if not hasattr(self._drm, "commit_data_records"):
            raise RuntimeError("DataRecord manager missing commit_data_records method")
        self._drm.commit_data_records([record])
