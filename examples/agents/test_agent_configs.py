#!/usr/bin/env python3
"""Exercise Agent Config endpoints against a live Harness API.

Flow:
  1. POST /v2/agents/configs           — create durable config from agents.yaml
  2. GET  /v2/agents/configs           — list team configs
  3. GET  /v2/agents/configs/{id}      — fetch config + sanitized manifest
  4. POST /v2/agents/sessions          — start session from config (JSON body)
  5. GET  /v2/agents/configs/{id}/sessions — list sessions for this config

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   optional (default: https://api.digitalocean.com)

Optional env:
  AGENT_SPEC             path to agents.yaml (default: examples/agents/agent-spec.yaml)
  CONFIG_NAME            config name (default: pydo-config-test-<timestamp>)

Examples:
  PYTHONPATH=src python examples/agents/test_agent_configs.py
  PYTHONPATH=src python examples/agents/test_agent_configs.py --spec examples/agents/openai-agents.yaml
  PYTHONPATH=src python examples/agents/test_agent_configs.py --config-id <uuid> --skip-create
  PYTHONPATH=src python examples/agents/test_agent_configs.py --delete-config
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

_DEFAULT_SPEC = os.path.join(os.path.dirname(__file__), "agent-spec.yaml")

from azure.core.exceptions import (  # noqa: E402
    ClientAuthenticationError,
    HttpResponseError,
)

from pydo import Client  # noqa: E402
from pydo.agents import SessionStatus  # noqa: E402


def _print_json(label: str, obj) -> None:
    print(f"\n[{label}]", file=sys.stderr)
    print(json.dumps(obj, indent=2, default=str))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=os.environ.get("AGENT_SPEC", _DEFAULT_SPEC),
        help="Path to agents.yaml used when creating a new config",
    )
    parser.add_argument(
        "--config-name",
        default=os.environ.get("CONFIG_NAME"),
        help="Name for a newly created config (must be unique per team)",
    )
    parser.add_argument(
        "--config-id",
        default=os.environ.get("CONFIG_ID"),
        help="Use an existing config instead of creating one",
    )
    parser.add_argument(
        "--session-name",
        default=os.environ.get("SESSION_NAME"),
        help="Session name when starting from config (default: pydo-run-<timestamp>)",
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Skip config create; requires --config-id",
    )
    parser.add_argument(
        "--skip-session",
        action="store_true",
        help="Only exercise config CRUD/list (no session create)",
    )
    parser.add_argument(
        "--delete-config",
        action="store_true",
        help="Soft-delete the config at the end (fails if active sessions remain)",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("DIGITALOCEAN_TOKEN")
    if not token:
        print("DIGITALOCEAN_TOKEN is required", file=sys.stderr)
        return 2

    client = Client(
        token=token,
        agents_endpoint=os.environ.get("PYDO_AGENTS_ENDPOINT"),
        timeout=600,
    )
    print(f"[endpoint] {client.agents.base_url}", file=sys.stderr)

    config_id = args.config_id

    # ------------------------------------------------------------------
    # Create config (unless skipped)
    # ------------------------------------------------------------------
    if not args.skip_create:
        if not os.path.exists(args.spec):
            print(f"manifest not found: {args.spec}", file=sys.stderr)
            return 2
        with open(args.spec, "r", encoding="utf-8") as fh:
            manifest_yaml = fh.read()

        config_name = args.config_name or f"pydo-config-test-{int(time.time())}"
        print(f"[1/5] creating config name={config_name!r} spec={args.spec}", file=sys.stderr)
        try:
            created = client.agents.configs.create(
                {"name": config_name, "manifest_yaml": manifest_yaml},
            )
        except ClientAuthenticationError as exc:
            print(f"[error] auth failed: {exc}", file=sys.stderr)
            return 1
        except HttpResponseError as exc:
            print(f"[error] create config failed: {exc}", file=sys.stderr)
            if "409" in str(exc) or "already exists" in str(exc).lower():
                print(
                    "[hint] Pick a new --config-name or delete the existing config first.",
                    file=sys.stderr,
                )
            return 1

        get = getattr(created, "get", None)
        cfg = (get("config") if get else None) or created
        config_id = (getattr(cfg, "get", lambda *_: None))("id")
        if not config_id:
            print(f"[error] create response missing config.id: {created}", file=sys.stderr)
            return 1
        _print_json("create config", created)
    else:
        if not config_id:
            print("--skip-create requires --config-id", file=sys.stderr)
            return 2
        print(f"[1/5] skipped create; using config_id={config_id}", file=sys.stderr)

    # ------------------------------------------------------------------
    # List configs
    # ------------------------------------------------------------------
    print("[2/5] listing configs…", file=sys.stderr)
    try:
        listed = client.agents.configs.list(page_size=50)
    except HttpResponseError as exc:
        print(f"[error] list configs failed: {exc}", file=sys.stderr)
        return 1
    _print_json("list configs", listed)

    # ------------------------------------------------------------------
    # Get config
    # ------------------------------------------------------------------
    print(f"[3/5] getting config {config_id}…", file=sys.stderr)
    try:
        fetched = client.agents.configs.get(config_id)
    except HttpResponseError as exc:
        print(f"[error] get config failed: {exc}", file=sys.stderr)
        return 1
    _print_json("get config", fetched)

    session_id = None

    if not args.skip_session:
        # ------------------------------------------------------------------
        # Create session from config
        # ------------------------------------------------------------------
        session_name = args.session_name or f"pydo-run-{int(time.time())}"
        print(
            f"[4/5] creating session name={session_name!r} from config…",
            file=sys.stderr,
        )
        try:
            session_resp = client.agents.sessions.create_from_config(
                name=session_name,
                config_id=config_id,
                timeout=600,
            )
        except HttpResponseError as exc:
            print(f"[error] create session from config failed: {exc}", file=sys.stderr)
            return 1

        get = getattr(session_resp, "get", None)
        info = (get("session") if get else None) or session_resp
        session_id = (getattr(info, "get", lambda *_: None))("session_id")
        _print_json("create session from config", session_resp)

        # ------------------------------------------------------------------
        # List sessions for config
        # ------------------------------------------------------------------
        print(f"[5/5] listing sessions for config {config_id}…", file=sys.stderr)
        try:
            config_sessions = client.agents.configs.list_sessions(
                config_id,
                page_size=50,
                status=SessionStatus.ALL,
            )
        except HttpResponseError as exc:
            print(f"[error] list config sessions failed: {exc}", file=sys.stderr)
            return 1
        _print_json("config sessions", config_sessions)
    else:
        print("[4/5] skipped session create", file=sys.stderr)
        print("[5/5] skipped config session list", file=sys.stderr)

    if args.delete_config:
        print(f"[cleanup] deleting config {config_id}…", file=sys.stderr)
        try:
            client.agents.configs.delete(config_id)
        except HttpResponseError as exc:
            print(f"[error] delete config failed: {exc}", file=sys.stderr)
            if session_id:
                print(
                    f"[hint] Destroy the session first:\n"
                    f"  PYTHONPATH=src python examples/agents/destroy_session.py "
                    f"(session_id={session_id})",
                    file=sys.stderr,
                )
            return 1
        print("[cleanup] config deleted (204)", file=sys.stderr)

    print(
        f"\n[done] config_id={config_id}"
        + (f" session_id={session_id}" if session_id else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
