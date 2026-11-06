"""agent_id remains a deprecated alias for Signals environment_id path params."""

import inspect
import re
import warnings

import pytest
import responses
from aioresponses import aioresponses

from pydo import Client
from pydo.aio import Client as aioClient
from pydo.custom_signals import with_agent_id_alias

_BODY = {"enabled": True}
_OPS = (
    ("get_consent", "GET", "/v1/consent/{id}"),
    ("update_consent", "PUT", "/v1/consent/{id}"),
    ("list_agent_sessions", "GET", "/v1/signals/agents/{id}/sessions"),
)
_STYLES = (
    "agent_id",
    "environment_id",
    "both_equal",
    "both_different",
    "positional",
)
_WARN_STYLES = ("agent_id", "both_equal")


def _invoke(signals, operation, style, value="env-1", other="env-2"):
    """Call a Signals operation using one id style."""
    method = getattr(signals, operation)
    extra = {"limit": 7} if operation == "list_agent_sessions" else {}
    if style == "positional":
        if operation == "update_consent":
            return method(value, _BODY)
        return method(value, **extra)
    kwargs = dict(extra)
    if operation == "update_consent":
        kwargs["body"] = _BODY
    if style == "agent_id":
        kwargs["agent_id"] = value
    elif style == "environment_id":
        kwargs["environment_id"] = value
    elif style == "both_equal":
        kwargs["agent_id"] = value
        kwargs["environment_id"] = value
    elif style == "both_different":
        kwargs["agent_id"] = value
        kwargs["environment_id"] = other
    else:
        raise AssertionError(style)
    return method(**kwargs)


def _alias_warnings(caught):
    return [
        item
        for item in caught
        if issubclass(item.category, DeprecationWarning)
        and "agent_id is deprecated" in str(item.message)
    ]


def _check_warning(style, call):
    """Run call and assert the deprecation warning only for agent_id=."""
    if style in _WARN_STYLES:
        with pytest.warns(DeprecationWarning, match="environment_id") as caught:
            result = call()
        alias = _alias_warnings(caught)
        assert alias
        assert alias[0].filename.endswith("test_signals_agent_id_alias.py")
        return result
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = call()
    assert not _alias_warnings(caught)
    return result


async def _check_warning_async(style, call):
    """Await call and assert the deprecation warning only for agent_id=."""
    if style in _WARN_STYLES:
        with pytest.warns(DeprecationWarning, match="environment_id") as caught:
            result = await call()
        alias = _alias_warnings(caught)
        assert alias
        assert alias[0].filename.endswith("test_signals_agent_id_alias.py")
        return result
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = await call()
    assert not _alias_warnings(caught)
    return result


@pytest.mark.parametrize("case", _OPS)
@pytest.mark.parametrize("style", _STYLES)
@responses.activate
def test_signals_environment_id_alias(
    mock_client: Client, mock_client_url, case, style
):
    """Current generated methods take environment_id and still accept agent_id=."""
    operation, http, path = case
    url = re.compile(re.escape(mock_client_url + path.format(id="env-1")))
    responses.add(
        {"GET": responses.GET, "PUT": responses.PUT}[http],
        url,
        json={"ok": True},
    )

    if style == "both_different":
        with pytest.raises(ValueError, match="environment_id"):
            _invoke(mock_client.signals, operation, style)
        assert not responses.calls
        return

    body = _check_warning(style, lambda: _invoke(mock_client.signals, operation, style))
    assert body == {"ok": True}
    assert path.format(id="env-1") in responses.calls[-1].request.url
    if operation == "list_agent_sessions":
        assert "limit=7" in responses.calls[-1].request.url


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _OPS)
@pytest.mark.parametrize("style", _STYLES)
async def test_signals_environment_id_alias_async(
    mock_aio_client: aioClient, mock_client_url, case, style
):
    """Async client matches the sync agent_id alias."""
    operation, http, path = case
    url = re.compile(re.escape(mock_client_url + path.format(id="env-1")))
    with aioresponses() as mocked:
        getattr(mocked, http.lower())(url, payload={"ok": True})

        if style == "both_different":
            with pytest.raises(ValueError, match="environment_id"):
                await _invoke(mock_aio_client.signals, operation, style)
            return

        async def _call():
            return await _invoke(mock_aio_client.signals, operation, style)

        body = await _check_warning_async(style, _call)
        assert body == {"ok": True}


def test_signals_operations_patch_is_used(mock_client: Client):
    """client.signals is the override that survives regeneration."""
    assert type(mock_client.signals).__module__ == "pydo.operations._patch"


def test_async_signals_operations_patch_is_used(mock_aio_client: aioClient):
    """async client.signals is the override that survives regeneration."""
    assert type(mock_aio_client.signals).__module__ == "pydo.aio.operations._patch"


def test_list_session_dialogues_takes_session_id_only(mock_client: Client):
    """Dialogues are addressed by session_id and need no id alias."""
    params = inspect.signature(mock_client.signals.list_session_dialogues).parameters
    assert "session_id" in params
    assert "environment_id" not in params
    assert "agent_id" not in params


def test_list_exports_keeps_separate_query_filters(mock_client: Client):
    """list_exports already accepts both names as independent query filters."""
    params = inspect.signature(mock_client.signals.list_exports).parameters
    assert "environment_id" in params
    assert "agent_id" in params


class _LegacySignals:
    """Stand-in for generated methods from before the environment_id rename."""

    def get_consent(self, agent_id, **kwargs):
        """Return the id the generated method received."""
        return {"id": agent_id, "kwargs": kwargs}

    def update_consent(self, agent_id, body, **kwargs):
        """Return the id and body the generated method received."""
        return {"id": agent_id, "body": body, "kwargs": kwargs}

    def list_agent_sessions(self, agent_id, *, limit=20, **kwargs):
        """Return the id and limit the generated method received."""
        return {"id": agent_id, "limit": limit, "kwargs": kwargs}


for _op_name in ("get_consent", "update_consent", "list_agent_sessions"):
    setattr(
        _LegacySignals,
        _op_name,
        with_agent_id_alias(getattr(_LegacySignals, _op_name)),
    )


@pytest.mark.parametrize("operation", [item[0] for item in _OPS])
@pytest.mark.parametrize("style", _STYLES)
def test_legacy_generated_shape_uses_agent_id_parameter(operation, style):
    """Forward either keyword onto a generated method whose parameter is agent_id."""
    legacy = _LegacySignals()
    if style == "both_different":
        with pytest.raises(ValueError, match="environment_id"):
            _invoke(legacy, operation, style)
        return

    result = _check_warning(style, lambda: _invoke(legacy, operation, style))
    assert result["id"] == "env-1"
    assert "agent_id" not in result["kwargs"]
    assert "environment_id" not in result["kwargs"]
    if operation == "update_consent":
        assert result["body"] == _BODY
    if operation == "list_agent_sessions":
        assert result["limit"] == 7
