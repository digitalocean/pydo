"""Identifies the AI agent, if any, driving the current process.

The rules live in agents.json, which is synced from digitalocean/openapi and
shared with the other DigitalOcean clients; see agents.schema.json for its
format. Do not edit the JSON files here; change them in digitalocean/openapi.
"""

import json
import os
import pkgutil
import re
from functools import lru_cache
from typing import Any, Dict, Mapping, Optional

# The agents.json format this module can read.
SUPPORTED_VERSION = 1


def parse(data: bytes) -> Dict[str, Any]:
    """Parses agents.json, rejecting formats this module can't read."""
    rules = json.loads(data)
    if rules.get("version") != SUPPORTED_VERSION:
        raise ValueError(
            f"agents: unsupported agents.json version {rules.get('version')}, "
            f"want {SUPPORTED_VERSION}"
        )
    rules["_name_re"] = re.compile(rules["namePattern"])
    return rules


def _matches(condition: Mapping[str, Any], environ: Mapping[str, str]) -> bool:
    kind = condition.get("type")
    if kind == "anyOf":
        return any(_matches(c, environ) for c in condition.get("conditions", []))
    if kind == "allOf":
        return all(_matches(c, environ) for c in condition.get("conditions", []))
    if kind == "env_set":
        return bool(environ.get(condition.get("name", "")))
    if kind == "env_value":
        name = condition.get("name", "")
        return name in environ and environ[name] == condition.get("value")
    return False


def detect_with(rules: Mapping[str, Any], environ: Mapping[str, str]) -> Optional[str]:
    """Returns the agent described by environ, or None if none matches.

    A valid value in the variable named by aiAgentVar wins over the rule list.
    """
    override = environ.get(rules.get("aiAgentVar") or "")
    if override is not None:
        override = override.strip()
        if rules["_name_re"].search(override):
            return override
    for agent in rules.get("agents", []):
        if _matches(agent.get("match", {}), environ):
            return agent.get("name")
    return None


@lru_cache(maxsize=None)
def _load_rules() -> Dict[str, Any]:
    return parse(pkgutil.get_data(__name__, "agents.json"))


def detect(environ: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """Returns the name of the AI agent driving the process, or None.

    The rules are parsed once; the environment is read on every call.
    Detection must never break the client, so unreadable rules mean no agent.
    """
    try:
        rules = _load_rules()
    except Exception:  # pylint: disable=broad-except
        return None
    return detect_with(rules, os.environ if environ is None else environ)


def user_agent_token() -> Optional[str]:
    """Returns the "Agent/<name>" User-Agent token, or None if no agent."""
    name = detect()
    return f"Agent/{name}" if name else None
