# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Client-side OpenAI Agents API helpers for the DO sandbox-provider path.

Mirrors doctl's orchestration for ``openai-agent-codex`` / ``codex-agentapi``
sessions (design §4 / §5):

1. Extract ``spec.openai`` (opaque create-session body) from the manifest.
2. ``POST api.openai.com/v1/agents/sessions`` with ``$OPENAI_API_KEY``.
3. Resolve ``${ENV_ID}`` / ``${OPENAI_API_KEY}`` into ``spec.env``.
4. Create the DO session with ``openai_session_id`` as a query param.

Attach never uses DO's SSE stream for this agent kind — callers bridge to
OpenAI with the persisted ``openai_session_id``.
"""
from __future__ import annotations

import http.client
import json
import os
import re
import select
import ssl
import time
from typing import Any, Callable, Dict, Iterator, Mapping, Optional, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .custom_models import AgentKind

# Adapters that select the OpenAI sandbox-provider image (no managed loop).
OPENAI_CODEX_ADAPTERS = frozenset(
    {
        "openai-agent-codex",
        "codex-agentapi",  # POC branch name on syed/openai_poc
    }
)

_DEFAULT_OPENAI_BASE = "https://api.openai.com"
_ENV_OPENAI_BASE = "OPENAI_API_BASE"
_ENV_OPENAI_KEY = "OPENAI_API_KEY"
_ENV_AGENT_API_BASE = "AGENT_API_BASE_URL"
_ENV_OPENAI_BASE_URL = "OPENAI_BASE_URL"

# Placeholders doctl / pydo resolve client-side before CreateSession.
_PLACEHOLDER_ENV_ID = "ENV_ID"
_PLACEHOLDER_OPENAI_KEY = "OPENAI_API_KEY"

_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class OpenAIAgentsError(RuntimeError):
    """OpenAI Agents API request failed or returned an unexpected body."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        body: Optional[str] = None,
    ):
        self.status = status
        self.body = body
        super().__init__(message)


def _require_yaml():
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep path
        raise ImportError(
            "PyYAML is required to orchestrate OpenAI sandbox sessions from "
            "an agents.yaml manifest; install with: pip install pyyaml"
        ) from exc
    return yaml


def _openai_base_url(explicit: Optional[str] = None) -> str:
    """Return the Agents API root (``…/v1/agents``), matching doctl / preview SDK."""
    raw = (
        explicit
        or os.environ.get(_ENV_AGENT_API_BASE)
        or os.environ.get(_ENV_OPENAI_BASE)
        or os.environ.get(_ENV_OPENAI_BASE_URL)
        or _DEFAULT_OPENAI_BASE
    )
    url = raw.rstrip("/")
    if "://" not in url:
        url = f"https://{url}"
    if url.endswith("/v1/agents"):
        return url
    if url.endswith("/v1"):
        return f"{url}/agents"
    if url in ("https://api.openai.com", "http://api.openai.com"):
        return f"{url}/v1/agents"
    # Caller already pointed at the agents root (or a custom preview host).
    if url.rstrip("/").endswith("/agents"):
        return url
    return f"{url}/v1/agents"


def _sessions_url(base_url: Optional[str] = None, *parts: str) -> str:
    root = _openai_base_url(base_url)
    path = "/sessions"
    for part in parts:
        path = f"{path}/{part}"
    return f"{root}{path}"

def resolve_openai_api_key(explicit: Optional[str] = None) -> str:
    key = explicit if explicit is not None else os.environ.get(_ENV_OPENAI_KEY)
    if not key:
        raise ValueError(
            f"{_ENV_OPENAI_KEY} is required for OpenAI Agents sandbox sessions "
            "(pass openai_api_key= or set the env var)"
        )
    return key


def load_manifest_doc(manifest: Union[str, bytes]) -> Dict[str, Any]:
    """Parse an agents.yaml document into a plain dict."""
    yaml = _require_yaml()
    if isinstance(manifest, (bytes, bytearray)):
        text = bytes(manifest).decode("utf-8")
    else:
        text = str(manifest)
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError("agents.yaml must deserialize to a mapping")
    return doc


def manifest_adapter(doc: Mapping[str, Any]) -> str:
    spec = doc.get("spec") if isinstance(doc.get("spec"), Mapping) else {}
    runtime = spec.get("runtime") if isinstance(spec.get("runtime"), Mapping) else {}
    adapter = runtime.get("adapter") or ""
    return str(adapter)


def extract_openai_create_body(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the opaque OpenAI ``POST /v1/agents/sessions`` body.

    Prefer ``spec.openai`` (design §3). Fall back to ``spec.runtime.config``
    for the interim POC shape used on ``syed/openai_poc``.
    """
    spec = doc.get("spec") if isinstance(doc.get("spec"), Mapping) else {}
    openai = spec.get("openai")
    if isinstance(openai, Mapping):
        return dict(openai)

    runtime = spec.get("runtime") if isinstance(spec.get("runtime"), Mapping) else {}
    config = runtime.get("config")
    if isinstance(config, Mapping) and (
        "agent" in config or "environment" in config or "input" in config
    ):
        return dict(config)

    raise ValueError(
        "OpenAI sandbox manifest must include spec.openai (or "
        "spec.runtime.config with agent/environment/input)"
    )


def is_openai_codex_manifest(doc: Mapping[str, Any]) -> bool:
    """True when the manifest selects the OpenAI sandbox-provider path."""
    if not isinstance(doc, Mapping):
        return False
    spec = doc.get("spec") if isinstance(doc.get("spec"), Mapping) else {}
    if isinstance(spec.get("openai"), Mapping):
        return True
    return manifest_adapter(doc) in OPENAI_CODEX_ADAPTERS


def is_openai_codex_session(session_info: Any) -> bool:
    """True when a DO session read model is the OpenAI sandbox-provider kind.

    Discriminator (design §5): ``agent_kind == AGENT_KIND_OPENAI_CODEX`` or a
    non-empty ``openai_session_id``.
    """
    if session_info is None:
        return False
    get = getattr(session_info, "get", None)

    def _get(key: str, default=None):
        if get is not None:
            return get(key, default)
        return getattr(session_info, key, default)

    kind = _get("agent_kind") or ""
    if kind == AgentKind.OPENAI_CODEX:
        return True
    openai_session_id = _get("openai_session_id") or ""
    return bool(str(openai_session_id).strip())


def resolve_placeholders(
    text: str,
    replacements: Mapping[str, str],
    *,
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    """Expand ``${VAR}`` placeholders using *replacements*, then *environ*."""
    env = environ if environ is not None else os.environ

    def _sub(match: re.Match) -> str:
        name = match.group(1)
        if name in replacements:
            return replacements[name]
        if name in env:
            return env[name]
        return match.group(0)

    return _PLACEHOLDER_RE.sub(_sub, text)


def _http_json(
    method: str,
    url: str,
    *,
    api_key: str,
    body: Optional[Mapping[str, Any]] = None,
    timeout: float = 60.0,
) -> Any:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as resp:  # noqa: S310 — fixed API host
            raw = resp.read()
            status = getattr(resp, "status", None) or resp.getcode()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise OpenAIAgentsError(
            f"OpenAI Agents API {method} {url} failed: HTTP {exc.code}"
            + (f": {detail.strip()}" if detail.strip() else ""),
            status=exc.code,
            body=detail,
        ) from exc
    except URLError as exc:
        raise OpenAIAgentsError(
            f"OpenAI Agents API {method} {url} failed: {exc.reason}"
        ) from exc
    if status not in (200, 201, 202):
        raise OpenAIAgentsError(
            f"OpenAI Agents API {method} {url} failed: HTTP {status}",
            status=status,
            body=raw.decode("utf-8", errors="replace") if raw else None,
        )
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenAIAgentsError(
            "OpenAI Agents API returned non-JSON body",
            status=status,
            body=raw.decode("utf-8", errors="replace"),
        ) from exc


def _pick_session_id(payload: Mapping[str, Any]) -> str:
    for key in ("session_id", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    nested = payload.get("session")
    if isinstance(nested, Mapping):
        for key in ("session_id", "id"):
            value = nested.get(key)
            if value:
                return str(value)
    raise OpenAIAgentsError(
        "OpenAI create-session response missing session_id",
        body=json.dumps(payload),
    )


def _pick_environment_id(payload: Mapping[str, Any]) -> str:
    for key in ("environment_id", "openai_environment_id"):
        value = payload.get(key)
        if value:
            return str(value)
    env = payload.get("environment")
    if isinstance(env, Mapping):
        for key in ("environment_id", "id"):
            value = env.get(key)
            if value:
                return str(value)
    raise OpenAIAgentsError(
        "OpenAI create-session response missing environment.environment_id",
        body=json.dumps(payload),
    )


def create_openai_agents_session(
    create_body: Mapping[str, Any],
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
) -> Tuple[str, str, Any]:
    """``POST …/v1/agents/sessions``; return ``(session_id, environment_id, raw)``."""
    key = resolve_openai_api_key(api_key)
    url = _sessions_url(base_url)
    payload = _http_json(
        "POST", url, api_key=key, body=dict(create_body), timeout=timeout
    )
    if not isinstance(payload, Mapping):
        raise OpenAIAgentsError(
            "OpenAI create-session returned a non-object body",
            body=repr(payload),
        )
    return _pick_session_id(payload), _pick_environment_id(payload), payload


def retrieve_openai_agents_session(
    openai_session_id: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 60.0,
) -> Any:
    """``GET …/v1/agents/sessions/{id}``."""
    if not openai_session_id:
        raise ValueError("openai_session_id is required")
    key = resolve_openai_api_key(api_key)
    url = _sessions_url(base_url, openai_session_id)
    return _http_json("GET", url, api_key=key, timeout=timeout)


def send_openai_session_input(
    openai_session_id: str,
    *,
    text: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 180.0,
    should_abort: Optional[Callable[[], bool]] = None,
    on_request_sent: Optional[Callable[[], None]] = None,
) -> Any:
    """Submit user text via ``POST …/sessions/{id}/events`` (doctl / preview SDK).

    There is no ``/input`` route — that path 404s. Self-hosted turns often block
    until the sandbox executor connects; callers should open the SSE stream
    concurrently and treat SSE as authoritative.

    *should_abort*: optional pollable predicate. When it becomes true (turn
    finished / stream closed), the POST socket is closed so a hung wait does
    not pin the OpenAI session for the next ``run()``.

    *on_request_sent*: called once the POST body has been written (before the
    response returns) so callers can ignore SSE history from earlier turns.
    """
    if not openai_session_id:
        raise ValueError("openai_session_id is required")
    key = resolve_openai_api_key(api_key)
    url = _sessions_url(base_url, openai_session_id, "events")
    body = {
        "events": [
            {
                "type": "session.input.message",
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": text}],
                    }
                ],
            }
        ]
    }
    if should_abort is None and on_request_sent is None:
        return _http_json("POST", url, api_key=key, body=body, timeout=timeout)
    return _http_json_cancellable(
        "POST",
        url,
        api_key=key,
        body=body,
        timeout=timeout,
        should_abort=should_abort,
        on_request_sent=on_request_sent,
    )


def _http_json_cancellable(
    method: str,
    url: str,
    *,
    api_key: str,
    body: Optional[Mapping[str, Any]] = None,
    timeout: float = 60.0,
    should_abort: Optional[Callable[[], bool]] = None,
    on_request_sent: Optional[Callable[[], None]] = None,
) -> Any:
    """Like ``_http_json`` but can abandon a hung response via *should_abort*."""
    abort = should_abort or (lambda: False)

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise OpenAIAgentsError(f"unsupported OpenAI Agents URL: {url}")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Host": parsed.hostname,
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    deadline = None
    if timeout is not None and timeout > 0:
        deadline = time.monotonic() + float(timeout)

    conn = http.client.HTTPSConnection(
        parsed.hostname,
        parsed.port or 443,
        timeout=min(30.0, float(timeout) if timeout else 30.0),
        context=ssl.create_default_context(),
    )
    try:
        conn.request(method, path, body=data, headers=headers)
        if on_request_sent is not None:
            try:
                on_request_sent()
            except Exception:  # noqa: BLE001 - never fail the POST on hook errors
                pass
        sock = conn.sock
        if sock is None:
            raise OpenAIAgentsError(f"OpenAI Agents API {method} {url}: no socket")
        while True:
            if abort():
                return None
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError(f"OpenAI Agents API {method} {url} timed out")
            ready, _, _ = select.select([sock], [], [], 0.5)
            if not ready:
                continue
            resp = conn.getresponse()
            raw = resp.read()
            status = resp.status
            break
    except OpenAIAgentsError:
        raise
    except TimeoutError:
        raise
    except Exception as exc:  # noqa: BLE001
        if abort():
            return None
        raise OpenAIAgentsError(
            f"OpenAI Agents API {method} {url} failed: {exc}"
        ) from exc
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    if status not in (200, 201, 202):
        detail = raw.decode("utf-8", errors="replace") if raw else ""
        raise OpenAIAgentsError(
            f"OpenAI Agents API {method} {url} failed: HTTP {status}"
            + (f": {detail.strip()}" if detail.strip() else ""),
            status=status,
            body=detail or None,
        )
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise OpenAIAgentsError(
            "OpenAI Agents API returned non-JSON body",
            status=status,
            body=raw.decode("utf-8", errors="replace"),
        ) from exc


class _OpenAIEventStream:
    """Closable SSE iterator over an open ``urlopen`` response."""

    def __init__(self, resp: Any) -> None:
        self._resp = resp
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._resp.close()
        except Exception:  # noqa: BLE001
            pass

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        data_buf: list = []
        try:
            while not self._closed:
                line = self._resp.readline()
                if not line:
                    break
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="replace")
                line = line.rstrip("\r\n")
                if line == "":
                    if not data_buf:
                        continue
                    payload = "\n".join(data_buf)
                    data_buf = []
                    if payload == "[DONE]":
                        break
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        yield event
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data_buf.append(line[5:].lstrip())
        finally:
            self.close()


def stream_openai_session_events(
    openai_session_id: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 300.0,
) -> _OpenAIEventStream:
    """Yield JSON events from ``GET …/sessions/{id}/events?stream=true``.

    The HTTP connection is opened immediately (before the generator is
    iterated) so callers can ``POST`` input afterward without missing events.
    Call :meth:`_OpenAIEventStream.close` when the turn ends so the socket is
    released (required before the next ``run()``).
    """
    if not openai_session_id:
        raise ValueError("openai_session_id is required")
    key = resolve_openai_api_key(api_key)
    url = _sessions_url(base_url, openai_session_id, "events") + "?stream=true"
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "text/event-stream, application/json",
        },
    )
    # Long-lived stream: no hard socket timeout (doctl uses Timeout: 0).
    del timeout  # reserved for future soft-deadline use
    try:
        resp = urlopen(request, timeout=None)  # noqa: S310 — fixed API host
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise OpenAIAgentsError(
            f"OpenAI Agents stream failed: HTTP {exc.code}"
            + (f": {detail.strip()}" if detail.strip() else ""),
            status=exc.code,
            body=detail,
        ) from exc
    except URLError as exc:
        raise OpenAIAgentsError(f"OpenAI Agents stream failed: {exc.reason}") from exc

    return _OpenAIEventStream(resp)


def prepare_openai_codex_manifest(
    manifest: Union[str, bytes],
    *,
    openai_api_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    openai_session_id: Optional[str] = None,
    openai_environment_id: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Resolve OpenAI ids into the manifest and return create inputs.

    Returns ``(resolved_yaml, openai_session_id, openai_environment_id)``.

    If *openai_session_id* and *openai_environment_id* are already known
    (caller created the OpenAI session), only placeholder resolution runs.
    Otherwise this creates the OpenAI session from ``spec.openai``.
    """
    if isinstance(manifest, (bytes, bytearray)):
        text = bytes(manifest).decode("utf-8")
    else:
        text = str(manifest)
    if not text.strip():
        raise ValueError("manifest is empty")

    doc = load_manifest_doc(text)
    if not is_openai_codex_manifest(doc):
        raise ValueError(
            "manifest is not an OpenAI sandbox-provider agent "
            f"(adapter must be one of {sorted(OPENAI_CODEX_ADAPTERS)} "
            "or include spec.openai)"
        )

    key = resolve_openai_api_key(openai_api_key)
    session_id = openai_session_id
    environment_id = openai_environment_id

    if not session_id or not environment_id:
        create_body = extract_openai_create_body(doc)
        session_id, environment_id, _ = create_openai_agents_session(
            create_body,
            api_key=key,
            base_url=openai_base_url,
        )

    resolved = resolve_placeholders(
        text,
        {
            _PLACEHOLDER_ENV_ID: environment_id,
            _PLACEHOLDER_OPENAI_KEY: key,
        },
    )
    return resolved, session_id, environment_id


__all__ = [
    "OPENAI_CODEX_ADAPTERS",
    "OpenAIAgentsError",
    "create_openai_agents_session",
    "extract_openai_create_body",
    "is_openai_codex_manifest",
    "is_openai_codex_session",
    "load_manifest_doc",
    "manifest_adapter",
    "prepare_openai_codex_manifest",
    "resolve_openai_api_key",
    "resolve_placeholders",
    "retrieve_openai_agents_session",
    "send_openai_session_input",
    "stream_openai_session_events",
]
