"""Agent detection tests

testcases.json is shared with godo and dots, so every client reports the same
agent for the same environment.
"""

import json
import pkgutil

import pytest

from pydo import Client, _agents
from pydo.aio import Client as AsyncClient

# pylint: disable=missing-function-docstring,protected-access

RULES = _agents.parse(pkgutil.get_data("pydo._agents", "agents.json"))
TESTCASES = json.loads(pkgutil.get_data("pydo._agents", "testcases.json"))
SUPPORTED_TYPES = {"anyOf", "allOf", "env_set", "env_value"}


def _check_condition(condition):
    assert condition["type"] in SUPPORTED_TYPES, condition
    for sub in condition.get("conditions", []):
        _check_condition(sub)


def test_embedded_rules():
    assert RULES["aiAgentVar"] == "AI_AGENT"
    assert RULES["agents"]

    names = [agent["name"] for agent in RULES["agents"]]
    assert len(names) == len(set(names))
    for agent in RULES["agents"]:
        assert agent["match"]["type"] in {"anyOf", "allOf"}, agent["name"]
        _check_condition(agent["match"])


@pytest.mark.parametrize("case", TESTCASES, ids=[c["name"] for c in TESTCASES])
def test_shared_testcases(case):
    assert _agents.detect_with(RULES, case["env"]) == case["expected"]


def test_condition_combinators():
    env = {"A": "1", "B": "x"}

    def env_set(name):
        return {"type": "env_set", "name": name}

    def all_of(*conditions):
        return {"type": "allOf", "conditions": list(conditions)}

    def any_of(*conditions):
        return {"type": "anyOf", "conditions": list(conditions)}

    matches = _agents._matches
    assert matches(
        all_of(env_set("A"), {"type": "env_value", "name": "B", "value": "x"}), env
    )
    assert not matches(all_of(env_set("A"), env_set("C")), env)
    assert matches(any_of(env_set("C"), env_set("A")), env)
    assert not matches(any_of(), env)
    assert not matches({"type": "file_exists", "name": "/"}, env)
    assert not matches({"type": "env_value", "name": "C"}, env)


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b'{"namePattern": ".*"}',
        b'{"version": 2, "namePattern": ".*"}',
        b'{"version": 1, "namePattern": "("}',
    ],
    ids=["not json", "missing version", "unsupported version", "invalid namePattern"],
)
def test_parse_invalid(data):
    with pytest.raises(Exception):
        _agents.parse(data)


def test_detect_reads_env_on_each_call(monkeypatch):
    monkeypatch.setenv("AI_AGENT", "first-agent")
    assert _agents.detect() == "first-agent"

    monkeypatch.setenv("AI_AGENT", "second-agent")
    assert _agents.detect() == "second-agent"


@pytest.mark.parametrize("client_class", [Client, AsyncClient])
def test_user_agent_includes_agent(monkeypatch, client_class):
    monkeypatch.setenv("AI_AGENT", "test-agent")
    client = client_class("")
    assert client._config.user_agent_policy.user_agent.endswith(" Agent/test-agent")
