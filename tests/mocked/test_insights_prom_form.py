"""Handwritten PromQL form posts that AutoRest leaves unimplemented."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,protected-access,unused-argument
# pylint: disable=invalid-overridden-method

import asyncio

import pytest
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

from pydo.custom_insights_prom import AsyncPromFormMixin, PromFormMixin


def _not_implemented(cls, methods):
    missing = [name for name in methods if not callable(getattr(cls, name, None))]
    if missing:
        raise NotImplementedError(missing)


class _Pipeline:
    def __init__(self, status_code=200, body=None):
        self.request = None
        self.kwargs = None
        self.status_code = status_code
        self.body = {"status": "success"} if body is None else body

    def run(self, request, **kwargs):
        self.request = request
        self.kwargs = kwargs
        return _PipelineResponse(self.status_code, self.body)


class _PipelineResponse:
    def __init__(self, status_code, body):
        self.http_response = _Response(status_code, body)


class _Response:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.reason = "error"
        self._body = body
        self.headers = {}
        self.content = b"{}" if body is not None else b""

    def json(self):
        return self._body


class _Client:
    def __init__(self, pipeline):
        self._pipeline = pipeline

    def format_url(self, url):
        return "https://api.digitalocean.com" + url


def _ops(status_code=200, body=None):
    pipeline = _Pipeline(status_code, body)
    return PromFormMixin(), pipeline, _Client(pipeline)


def _bind(ops, client):
    ops._client = client  # pylint: disable=protected-access
    ops._deserialize = (
        lambda *_args, **_kwargs: None
    )  # pylint: disable=protected-access
    return ops


def test_post_prom_query_sends_form_body():
    ops, pipeline, client = _ops()
    _bind(ops, client)

    body = ops.post_prom_query("nyc3", query="up", time="1620683817")

    request = pipeline.request
    assert body == {"status": "success"}
    assert request.method == "POST"
    assert (
        request.url
        == "https://api.digitalocean.com/v2/insights/query/nyc3/prom/api/v1/query"
    )
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.content == {"query": "up", "time": "1620683817"}
    assert pipeline.kwargs["stream"] is False


def test_post_prom_query_range_sends_required_fields():
    ops, pipeline, client = _ops()
    _bind(ops, client)

    ops.post_prom_query_range(
        "nyc3", query="up", start="1", end="2", step="15s", timeout="30s"
    )

    assert pipeline.request.url.endswith("/prom/api/v1/query_range")
    assert pipeline.request.content == {
        "query": "up",
        "start": "1",
        "end": "2",
        "step": "15s",
        "timeout": "30s",
    }


def test_post_prom_labels_omits_missing_fields():
    ops, pipeline, client = _ops()
    _bind(ops, client)

    ops.post_prom_labels("nyc3", match=["up"])

    assert pipeline.request.url.endswith("/prom/api/v1/labels")
    assert pipeline.request.content == {"match[]": ["up"]}


def test_post_prom_series_repeats_match_selectors():
    ops, pipeline, client = _ops()
    _bind(ops, client)

    ops.post_prom_series("nyc3", match=["up", "go_goroutines"], start="1")

    assert pipeline.request.url.endswith("/prom/api/v1/series")
    assert pipeline.request.content == {
        "match[]": ["up", "go_goroutines"],
        "start": "1",
    }


def test_prometheus_error_body_is_returned():
    ops, _pipeline, client = _ops(400, {"status": "error", "errorType": "bad_data"})
    _bind(ops, client)

    body = ops.post_prom_query("nyc3", query="???")

    assert body["errorType"] == "bad_data"


def test_unauthorized_raises():
    ops, _pipeline, client = _ops(401, {"id": "unauthorized"})
    _bind(ops, client)

    with pytest.raises(ClientAuthenticationError):
        ops.post_prom_query("nyc3", query="up")


def test_unexpected_status_raises():
    ops, _pipeline, client = _ops(418, {})
    _bind(ops, client)

    with pytest.raises(HttpResponseError):
        ops.post_prom_query("nyc3", query="up")


def test_subclass_satisfies_autorest_unimplemented_check():
    class _Generated:
        def __init__(self, *args, **kwargs):
            _not_implemented(
                self.__class__,
                [
                    "post_prom_query",
                    "post_prom_query_range",
                    "post_prom_labels",
                    "post_prom_series",
                ],
            )

    class InsightsOperations(PromFormMixin, _Generated):
        pass

    InsightsOperations(object(), object(), object(), object())


def test_async_post_prom_query_awaits_pipeline():
    class _AsyncPipeline(_Pipeline):
        async def run(self, request, **kwargs):
            self.request = request
            self.kwargs = kwargs
            return _PipelineResponse(self.status_code, self.body)

    pipeline = _AsyncPipeline()
    ops = _bind(AsyncPromFormMixin(), _Client(pipeline))

    body = asyncio.get_event_loop().run_until_complete(
        ops.post_prom_query("nyc3", query="up")
    )

    assert body == {"status": "success"}
    assert (
        pipeline.request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    )
