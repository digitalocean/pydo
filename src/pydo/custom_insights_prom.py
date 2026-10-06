"""Form-urlencoded PromQL posts.

AutoRest's Python generator leaves ``application/x-www-form-urlencoded``
operations unimplemented. These mixins supply the four Insights posts.
"""

from typing import Any, Optional
from urllib.parse import quote

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ResourceNotModifiedError,
    map_error,
)
from azure.core.rest import HttpRequest

_FORM = "application/x-www-form-urlencoded"
_RETURNED = {200, 400, 403, 404, 422, 500, 503}
_QUERY = "/v2/insights/query/{region}/prom/api/v1/query"
_QUERY_RANGE = "/v2/insights/query/{region}/prom/api/v1/query_range"
_LABELS = "/v2/insights/query/{region}/prom/api/v1/labels"
_SERIES = "/v2/insights/query/{region}/prom/api/v1/series"


def _form_request(path, region, fields, kwargs):
    headers = dict(kwargs.pop("headers", {}) or {})
    params = kwargs.pop("params", None) or None
    cls = kwargs.pop("cls", None)
    error_map = {
        404: ResourceNotFoundError,
        409: ResourceExistsError,
        304: ResourceNotModifiedError,
        401: ClientAuthenticationError,
        429: HttpResponseError,
    }
    error_map.update(kwargs.pop("error_map", {}) or {})

    url = path.format(region=quote(str(region), safe=""))
    data = {key: value for key, value in fields.items() if value is not None}
    if not any(key.lower() == "accept" for key in headers):
        headers["Accept"] = "application/json"
    if data:
        request = HttpRequest("POST", url, params=params, headers=headers, data=data)
    else:
        headers["Content-Type"] = _FORM
        request = HttpRequest("POST", url, params=params, headers=headers)
    return request, cls, error_map


def _finish(ops, pipeline_response, cls, error_map):
    response = pipeline_response.http_response
    if response.status_code not in _RETURNED:
        map_error(
            status_code=response.status_code,
            response=response,
            error_map=error_map,
        )
        raise HttpResponseError(response=response)
    deserialized = response.json() if response.content else None
    if cls:
        headers = {
            name: ops._deserialize(  # pylint: disable=protected-access
                "int", response.headers.get(name)
            )
            for name in (
                "ratelimit-limit",
                "ratelimit-remaining",
                "ratelimit-reset",
            )
        }
        return cls(pipeline_response, deserialized, headers)
    return deserialized


class PromFormMixin:
    """Sync PromQL form posts. Subclass the generated Insights operations."""

    def _prom_post(self, path, region, fields, **kwargs):
        request, cls, error_map = _form_request(path, region, fields, kwargs)
        request.url = self._client.format_url(
            request.url
        )  # pylint: disable=protected-access
        pipeline_response = (
            self._client._pipeline.run(  # pylint: disable=protected-access
                request, stream=False, **kwargs
            )
        )
        return _finish(self, pipeline_response, cls, error_map)

    def post_prom_query(
        self,
        region: str,
        *,
        query: str,
        time: Optional[str] = None,
        timeout: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """POST an instant PromQL query as ``application/x-www-form-urlencoded``."""
        return self._prom_post(
            _QUERY,
            region,
            {"query": query, "time": time, "timeout": timeout},
            **kwargs,
        )

    def post_prom_query_range(
        self,
        region: str,
        *,
        query: str,
        start: str,
        end: str,
        step: str,
        timeout: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """POST a range PromQL query as ``application/x-www-form-urlencoded``."""
        return self._prom_post(
            _QUERY_RANGE,
            region,
            {
                "query": query,
                "start": start,
                "end": end,
                "step": step,
                "timeout": timeout,
            },
            **kwargs,
        )

    def post_prom_labels(
        self,
        region: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        match: Optional[list] = None,
        **kwargs: Any,
    ) -> Any:
        """POST label-name selectors as ``application/x-www-form-urlencoded``."""
        return self._prom_post(
            _LABELS,
            region,
            {"start": start, "end": end, "match[]": match},
            **kwargs,
        )

    def post_prom_series(
        self,
        region: str,
        *,
        match: list,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """POST series selectors as ``application/x-www-form-urlencoded``."""
        return self._prom_post(
            _SERIES,
            region,
            {"match[]": match, "start": start, "end": end},
            **kwargs,
        )


class AsyncPromFormMixin(PromFormMixin):
    """Async PromQL form posts. Public methods return awaitables."""

    async def _prom_post(  # pylint: disable=invalid-overridden-method
        self, path, region, fields, **kwargs
    ):
        request, cls, error_map = _form_request(path, region, fields, kwargs)
        request.url = self._client.format_url(
            request.url
        )  # pylint: disable=protected-access
        pipeline_response = (
            await self._client._pipeline.run(  # pylint: disable=protected-access
                request, stream=False, **kwargs
            )
        )
        return _finish(self, pipeline_response, cls, error_map)
