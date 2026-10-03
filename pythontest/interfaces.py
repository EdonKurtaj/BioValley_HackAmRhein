"""Collector-to-ingestion contracts; database fields match supabase/schema.sql."""

from typing import NotRequired, Protocol, TypedDict


class FetchResult(TypedDict):
    source_id: str
    checked_at: str
    http_status: int | None
    request_ok: bool
    rate_limited: bool
    retry_after: str | None
    response_bytes: int | None
    error: str | None
    data: object
    source_last_modified: NotRequired[str | None]


class Observation(TypedDict):
    source_id: str
    observation_key: str
    observed_at: str
    station_id: str
    station_name: str | None
    metric: str
    value: float | int
    unit: str
    dimensions: dict
    raw_record: dict
    fetch_run_id: NotRequired[str]


class FetchRun(TypedDict):
    id: str
    source_id: str
    fetched_at: str
    http_status: int | None
    request_ok: bool
    rate_limited: bool
    retry_after: str | None
    response_bytes: int | None
    error: str | None
    source_last_modified: str | None
    raw_payload: object


class IngestionBatch(TypedDict):
    source: dict
    fetch_run: FetchRun
    observations: list[Observation]
    normalization_error: str | None


class IngestionSink(Protocol):
    """Persist each attempt, and successful measurements, without blocking polling."""

    def ingest(self, source: dict, result: FetchResult) -> None: ...
    def flush(self) -> None: ...
