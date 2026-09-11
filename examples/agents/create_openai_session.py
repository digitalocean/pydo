#!/usr/bin/env python3
"""Create an OpenAI sandbox-provider session from ``openai-agents.yaml``.

Flow (same as doctl agents start):
  1. Read the manifest config file
  2. POST OpenAI create-session body → api.openai.com
  3. Resolve ${ENV_ID} / ${REMOTE_URL} / ${OPENAI_API_KEY} into the manifest
  4. POST resolved YAML → DO /v2/agents/sessions?openai_session_id=...

Required env:
  DIGITALOCEAN_TOKEN
  OPENAI_API_KEY
  PYDO_AGENTS_ENDPOINT   optional (default: https://api.digitalocean.com)
  AGENT_SPEC             optional (default: examples/agents/openai-agents.yaml)

Example:
  PYTHONPATH=src python examples/agents/create_openai_session.py
  PYTHONPATH=src python examples/agents/create_openai_session.py --name openai-codex-$(date +%s)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from azure.core.exceptions import (  # noqa: E402
    ClientAuthenticationError,
    HttpResponseError,
    ServiceResponseTimeoutError,
)

from pydo import Client  # noqa: E402
from pydo.agents.custom_openai_sandbox import prepare_openai_codex_manifest  # noqa: E402

DEFAULT_SPEC = os.path.join(os.path.dirname(__file__), "openai-agents.yaml")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=os.environ.get("AGENT_SPEC", DEFAULT_SPEC),
        help="Path to agents.yaml",
    )
    parser.add_argument(
        "--name",
        default=os.environ.get("AGENT_NAME"),
        help="Override metadata.name (avoids 409 if the name is already active)",
    )
    args = parser.parse_args(argv)

    if not os.path.exists(args.spec):
        print(f"manifest not found: {args.spec}", file=sys.stderr)
        return 2

    with open(args.spec, "r", encoding="utf-8") as fh:
        manifest = fh.read()

    if args.name:
        import re

        manifest, n = re.subn(
            r"(?m)^(\s*name:\s*).*$",
            rf"\g<1>{args.name}",
            manifest,
            count=1,
        )
        if n != 1:
            print(
                f"[error] could not set metadata.name to {args.name!r} in manifest",
                file=sys.stderr,
            )
            return 2
        print(f"[name] {args.name}", file=sys.stderr)
    token = os.environ.get("DIGITALOCEAN_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not token:
        print("DIGITALOCEAN_TOKEN is required", file=sys.stderr)
        return 2
    if not openai_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    endpoint = os.environ.get("PYDO_AGENTS_ENDPOINT")
    client = Client(
        token=token,
        agents_endpoint=endpoint,
        timeout=600,
    )
    print(f"[manifest] {args.spec}", file=sys.stderr)
    print(f"[endpoint] {client.agents.base_url}", file=sys.stderr)

    print("[1/3] creating OpenAI Agents session…", file=sys.stderr)
    t0 = time.monotonic()
    try:
        resolved, oai_session_id, oai_env_id = prepare_openai_codex_manifest(
            manifest,
            openai_api_key=openai_key,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[error] OpenAI create-session failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"[1/3] done in {time.monotonic() - t0:.1f}s "
        f"openai_session_id={oai_session_id} env={oai_env_id}",
        file=sys.stderr,
    )

    print(
        "[2/3] creating DO sandbox (may take several minutes; timeout=600s)…",
        file=sys.stderr,
    )
    t1 = time.monotonic()
    try:
        resp = client.agents.sessions.create_from_manifest(
            resolved,
            openai_session_id=oai_session_id,
            timeout=600,
        )
    except ClientAuthenticationError as exc:
        print(f"[error] DO auth failed: {exc}", file=sys.stderr)
        return 1
    except ServiceResponseTimeoutError as exc:
        print(
            f"[error] DO CreateSession timed out after "
            f"{time.monotonic() - t1:.0f}s: {exc}",
            file=sys.stderr,
        )
        return 1
    except HttpResponseError as exc:
        msg = str(exc)
        print(f"[error] DO CreateSession failed: {exc}", file=sys.stderr)
        if "credential storage" in msg.lower():
            print(
                "\n[hint] Harness Secrets Manager failed while storing "
                "CODEX_API_KEY (backend/onboarding issue, not pydo).",
                file=sys.stderr,
            )
        elif "already in use" in msg.lower() or "409" in msg:
            print(
                "\n[hint] Destroy the existing session or pick a new name:\n"
                "         PYTHONPATH=src python "
                "examples/agents/create_openai_session.py "
                "--name openai-codex-$(date +%s)",
                file=sys.stderr,
            )
        return 1

    get = getattr(resp, "get", None)
    info = get("session") if get else resp
    session_id = (getattr(info, "get", lambda *_: None))("session_id")
    if not session_id:
        print(f"[error] create response missing session_id: {resp}", file=sys.stderr)
        return 1

    agent = client.agents.attach(session_id, openai_api_key=openai_key)
    agent._raw = resp  # noqa: SLF001
    print(
        f"[2/3] done in {time.monotonic() - t1:.1f}s do_session_id={agent.session_id}",
        file=sys.stderr,
    )

    print("[3/3] waiting until READY…", file=sys.stderr)
    try:
        agent.wait_until_ready(timeout=180.0)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] wait_until_ready: {exc}", file=sys.stderr)

    info = agent.refresh() or agent.info
    print(
        f"[ready] do={agent.session_id} openai={agent.openai_session_id} "
        f"env={agent.openai_environment_id} kind={agent.agent_kind} "
        f"status={agent.status}",
        file=sys.stderr,
    )
    print(json.dumps(info, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
