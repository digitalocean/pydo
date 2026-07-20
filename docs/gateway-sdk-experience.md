# Action Gateway — Python SDK Experience

**Audience:** internal alignment on the developer experience of the Action Gateway surface in `pydo`.
**Status:** proposal / preview. Feedback welcome — nothing here is final.

The Action Gateway gives models access to a large catalog of third-party tools plus a sandboxed Python runtime. Usage is **session-first**: create a session on the DigitalOcean API, then call tools over REST on `actions.do-ai.run` with that session.

---

## 1. Setup

```bash
pip install pydo
export DIGITALOCEAN_TOKEN=...
```

```python
from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])

session = client.sessions.create(
    end_user_id="user-123",   # required
    # permissions optional — defaults to allow-all
)
```

`end_user_id` is required. If you omit `permissions`, the SDK creates a default policy of `{"defaultAction": "allow", "rules": []}`. Optional permissions:

```python
session = client.sessions.create(
    end_user_id="user-123",
    permissions={
        "default_action": "ask",
        "rules": [
            {"toolbelt": "read-only@1.2.3", "action": "allow"},
            {"tool": "gmail", "action": "allow"},
        ],
    },
)
```

Session create hits `POST /v2/sessions` on `api.digitalocean.com`. Tool calls go to the gateway host (`https://actions.do-ai.run` by default; override with `gateway_endpoint=` or `PYDO_GATEWAY_ENDPOINT`).

`session.url` is the session-pinned MCP URL for external MCP clients:

```text
https://actions.do-ai.run/mcp/session/<session-uuid>
```

---

## 2. Basic usage (no model involved)

```python
results = session.tools.search("search the web for recent news")
catalog = session.tools.list(include_all=True)

output = session.tools.invoke_one(
    "EXA_SEARCH",
    {"query": "DigitalOcean news", "num_results": 5},
)

envelope = session.tools.invoke([
    {"tool": "EXA_SEARCH", "arguments": {"query": "DigitalOcean news"}},
    {"tool": "HACKERNEWS_GET_TODAY_STORIES", "arguments": {}},
])

result = session.code.execute("print(sum(range(10)))")
```

These map to REST: `POST /tools/search`, `POST /tools/invoke`, `POST /code/execute`, always with `X-Session-Id`.

---

## 3. Using tools with a model

- **`session.tools()`** — provider-formatted tool definitions for `tools=`
- **`session.handle_tool_calls(response)`** — execute the model's tool calls and return ready-to-append messages

### Chat Completions

```python
from pydo.action_gateway import Client

client = Client(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.sessions.create(end_user_id="user-123")

tools = session.tools()
messages = [{"role": "user", "content":
             "Find the latest news about DigitalOcean and summarize it."}]

while True:
    response = client.chat.completions.create(
        model="openai-gpt-4o",
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message
    if not message.get("tool_calls"):
        break

    messages.append(dict(message))
    messages.extend(session.handle_tool_calls(response))

print(message["content"])
```

### Messages API

```python
from pydo.action_gateway import Client, MessagesProvider

client = Client(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=MessagesProvider(),
)
session = client.sessions.create(end_user_id="user-123")

tools = session.tools()
# ... same loop with client.messages.create and session.handle_tool_calls
```

---

## 4. Meta-tools vs. concrete tools

`session.tools()` defaults to the three meta-tools (`action_search`, `action_invoke`, `action_code`). For a fixed surface:

```python
tools = session.tools(include_all=True)
tools = session.tools(names=["EXA_SEARCH"])
tools = session.tools(search="post a message to slack", limit=5)
```

---

## 5. Async

```python
from pydo.action_gateway.aio import Client

async with Client(token=token) as client:
    session = await client.sessions.create(end_user_id="user-123")
    tools = await session.tools()
    response = await client.chat.completions.create(..., tools=tools)
    messages.extend(await session.handle_tool_calls(response))
```

---

## 6. Design notes

- **Session-first.** Bare gateway calls without a session are unsupported.
- **REST for SDK execution.** MCP remains available via `session.url` for external clients.
- **Provider pattern.** Chat Completions / Messages / Responses formatting stays in small provider classes.
- **Same DO token** for session create (public API) and gateway REST (actions host).
