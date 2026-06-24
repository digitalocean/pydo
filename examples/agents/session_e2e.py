"""End-to-end hosted-agents demo: create -> attach -> destroy.

This single script walks the whole lifecycle the way an end user would:

  1. create   — provision a session from an agents.yaml manifest (the spec
                defines the runtime adapter, sandbox, env, etc.)
  2. attach   — open the SSE event stream, send a prompt, and consume the
                events as they arrive: render the agent's reply token-by-token,
                surface tool calls, auto-approve HITL prompts, and capture the
                assembled answer for programmatic use.
  3. destroy  — tear the session down.

stdout = the agent's streamed reply.   stderr = the play-by-play / status.

Required env:
  DIGITALOCEAN_TOKEN
  PYDO_AGENTS_ENDPOINT   stage2: https://api.s2r1.internal.digitalocean.com
  AGENT_SPEC             path to the agent spec YAML (agents.yaml manifest)

Optional env:
  PROMPT                 message to send (default: a short demo prompt)
  RUN_TIMEOUT_SECONDS    how long to wait for the run to finish (default: 120)

Example:
  export DIGITALOCEAN_TOKEN=dop_v1_...
  export PYDO_AGENTS_ENDPOINT=https://api.s2r1.internal.digitalocean.com
  export AGENT_SPEC=/path/to/codex-agent-spec.yaml
  python examples/agents/session_e2e.py
"""

import os
import sys
import threading
import time

from pydo import Client
from pydo.agents import HITLOutcome, ResolutionSource


def log(msg=""):
    """Status line -> stderr (keeps stdout clean for the agent's reply)."""
    print(msg, file=sys.stderr, flush=True)


def main():
    token = os.environ["DIGITALOCEAN_TOKEN"]
    endpoint = os.environ.get("PYDO_AGENTS_ENDPOINT")
    spec_path = os.environ.get("AGENT_SPEC", "agent-spec.yaml")
    prompt = os.environ.get("PROMPT", "In one short sentence, what is DigitalOcean?")
    run_timeout = float(os.environ.get("RUN_TIMEOUT_SECONDS", "120"))

    with open(spec_path, "r", encoding="utf-8") as fh:
        manifest = fh.read()

    client = Client(token=token, agents_endpoint=endpoint)
    log("endpoint: " + client.agents.base_url)

    # --- 1. create -------------------------------------------------------
    session = client.agents.sessions.create_from_manifest(manifest)
    session_id = session.session.session_id
    log("[created] %s  (%s)" % (session_id, session.session.status))

    finished = threading.Event()
    reply_chunks = []

    # --- 2a. attach: consume the SSE event feed in the background --------
    def consume_events():
        try:
            with client.agents.sessions.stream(session_id) as events:
                for ev in events:
                    etype = getattr(ev, "type", None)
                    data = ev.get("data") or {}

                    if etype == "run.started":
                        log("\n[run started]")
                    elif etype == "run.token_delta":
                        text = data.get("text", "")
                        reply_chunks.append(text)
                        print(text, end="", flush=True)  # live reply -> stdout
                    elif etype == "run.tool_call_started":
                        log("\n[tool] %s ..." % data.get("name", "?"))
                    elif etype == "run.tool_call_completed":
                        log("[tool done] %s" % data.get("summary", "ok"))
                    elif etype == "run.human_input_requested":
                        # A HITL approval gates the run; auto-approve for the demo.
                        req_id = data.get("hitl_id") or data.get("request_id")
                        log("\n[HITL] auto-approving %s" % req_id)
                        client.agents.sessions.resolve_hitl(
                            session_id,
                            req_id,
                            outcome=HITLOutcome.APPROVE,
                            source=ResolutionSource.OUT_OF_BAND,
                        )
                    elif etype == "run.completed":
                        log(
                            "\n[run completed] tokens in=%s out=%s cost=$%.4f"
                            % (
                                data.get("total_tokens_in"),
                                data.get("total_tokens_out"),
                                (data.get("run_cost_micros") or 0) / 1_000_000,
                            )
                        )
                        finished.set()
                        return
                    elif etype == "run.failed":
                        log(
                            "\n[run failed] %s (code %s)"
                            % (data.get("message"), data.get("code"))
                        )
                        finished.set()
                        return
                    else:
                        log("\n[event] %s" % etype)
        except Exception as exc:  # noqa: BLE001 - surface any stream error and unblock
            log("\n[stream error] %r" % exc)
            finished.set()

    streamer = threading.Thread(target=consume_events, daemon=True)
    streamer.start()
    time.sleep(1)  # let the stream attach before submitting input

    # --- 2b. attach: send the prompt ------------------------------------
    log("\n>>> " + prompt + "\n")
    run = client.agents.sessions.send_input(session_id, text=prompt)
    log("[queued run] %s" % run.get("run_id"))

    # --- 2c. wait for the run to finish (driven by the SSE feed) --------
    if not finished.wait(timeout=run_timeout):
        log("\n[timeout] no completion within %ss" % run_timeout)

    # --- use the streamed data ------------------------------------------
    reply = "".join(reply_chunks).strip()
    log("\n[captured reply: %d chars / %d words]" % (len(reply), len(reply.split())))

    # --- 3. destroy ------------------------------------------------------
    try:
        client.agents.sessions.destroy(session_id)
        log("[destroyed] %s" % session_id)
    except Exception as exc:  # noqa: BLE001
        log("[destroy failed] %r" % exc)

    return 0 if reply else 1


if __name__ == "__main__":
    raise SystemExit(main())
