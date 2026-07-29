# Action Gateway — Python SDK Experience

**Audience:** internal alignment on the developer experience of the Action Gateway surface in `pydo`.
**Status:** proposal / preview. Feedback welcome — nothing here is final.

The Action Gateway gives models access to a large catalog of third-party tools plus a sandboxed Python runtime. Usage is **session-first**: create a session on the DigitalOcean API, then call tools through the returned MCP URL.

---

## 1. Setup

```bash
pip install pydo
export DIGITALOCEAN_TOKEN=...
```

```python
from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])

session = client.session.create(
    actor_id="user-123",   # required
    # permissions optional — defaults to ask
)
```

`actor_id` is required. If you omit `permissions`, the SDK creates a default policy of `{"defaultAction": "ask"}`. Optional permissions:

```python
session = client.session.create(
    actor_id="user-123",
    permissions={
        "default_action": "ask",
        "rules": [
            {"tool": "toolbelt:read-only@1", "action": "allow"},
            {"tool": "gmail", "action": "allow"},
        ],
    },
)
```

Session create hits `POST /v2/action-gateway/sessions` on `api.digitalocean.com` with `name`, `policy`, and `actor_id`. It can also send `tools` (omitted means all, an empty list means none) and opaque `config`, including `preloadTools`. Tool calls use the `mcpUrl` returned by the API. The same actor is sent as `X-Actor-Id` on gateway requests.

```python
session = client.session.create(
    actor_id="user-123",
    tools=["exa_web_search@v1"],
    config={"preloadTools": ["exa_web_search@v1"]},
    permissions={
        "default_action": "ask",
        "rules": [{"tool": "exa_web_search", "action": "allow"}],
    },
)
```

`session.url` is the session-pinned MCP URL for external MCP clients:

```text
https://actions.do-ai.run/mcp/session/<session-uuid>
```

---

## 2. Basic usage (no model involved)

```python
results = session.tools.search("search the web for recent news")
session_tools = session.tools.list(include_all=True)

output = session.tools.invoke_one(
    "exa_web_search",
    {"query": "DigitalOcean news", "max_results": 5},
)

envelope = session.tools.invoke([
    {"tool": "exa_web_search", "arguments": {"query": "DigitalOcean news"}},
    {"tool": "exa_web_fetch", "arguments": {"url": "https://www.digitalocean.com"}},
])

result = session.code.execute("print(sum(range(10)))")
```

These calls use JSON-RPC over the `mcpUrl` returned by session creation, with `X-Session-Id` and `X-Actor-Id`.

For policies that require approval, approve a pending invocation by ID:

```python
session.approve(approval_id)
```

See `examples/gateway/approval_flow.py` for a complete request, approval, and retry flow.

---

## 3. Using tools with a model

- **`session.tools()`** — provider-formatted tool definitions for `tools=`
- **`session.handle_tool_calls(response)`** — execute the model's tool calls and return ready-to-append messages

### Chat Completions

```python
from pydo.action_gateway import ActionGatewayClient

client = ActionGatewayClient(token=os.environ["DIGITALOCEAN_TOKEN"])
session = client.session.create(actor_id="user-123")

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
from pydo.action_gateway import ActionGatewayClient, MessagesProvider

client = ActionGatewayClient(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=MessagesProvider(),
)
session = client.session.create(actor_id="user-123")

tools = session.tools()
# ... same loop with client.messages.create and session.handle_tool_calls
```

---

## 4. Meta-tools vs. concrete tools

`session.tools()` defaults to the three meta-tools (`action_search`, `action_invoke`, `action_code`). With `config.preloadTools`, request every tool exposed on this session MCP endpoint or select by name:

```python
tools = session.tools(include_all=True)
tools = session.tools(names=["exa_web_search"])
tools = session.tools(search="post a message to slack", limit=5)
```

---

## 5. Toolbelts and policies

Create a versioned toolbelt from provider-qualified tool names:

```python
toolbelt = client.create_toolbelt(
    name="search-toolbelt",
    tools=["exa_web_search", "exa_web_fetch"],
)
print(toolbelt.ref)  # search-toolbelt@1
```

Toolbelts are public DigitalOcean API resources, so the base CRUD surface is
generated from the public OpenAPI specification under `client.toolbelts`:

```python
client.toolbelts.list(status="active")
client.toolbelts.get("search-toolbelt", version="1")
client.toolbelts.add_tools("search-toolbelt", {"tools": ["jira_create_issue"]})
client.toolbelts.delete_tools("search-toolbelt", {"tools": ["exa_web_fetch"]})
client.toolbelts.delete("search-toolbelt")
```

`client.create_toolbelt(...)` is the Action Gateway convenience wrapper around
the generated `client.toolbelts.create(body=...)` operation.

Pin that version in a session policy:

```python
session = client.session.create(
    actor_id="user-123",
    permissions={
        "default_action": "ask",
        "rules": [
            {"tool": f"toolbelt:{toolbelt.ref}", "action": "allow"},
        ],
    },
)
```

Toolbelt creation maps to `POST /v2/toolbelts`. The response exposes both `toolbelt.reference` and the shorter `toolbelt.ref` alias.

---

## 6. Responses API

```python
from pydo.action_gateway import ActionGatewayClient, ResponsesProvider

client = ActionGatewayClient(
    token=os.environ["DIGITALOCEAN_TOKEN"],
    gateway_provider=ResponsesProvider(),
)
session = client.session.create(actor_id="user-123")
response = client.responses.create(
    model="openai-gpt-4o",
    input="What DigitalOcean Droplet sizes are available in NYC3?",
    tools=session.tools(),
)
tool_outputs = session.handle_tool_calls(response)
```

The Responses API can also connect to `session.url` directly when its MCP tool
surface supports remote MCP servers. Gateway policy approval remains separate
from model-provider approval: use `session.approve(approval_id)` or
`session.deny(approval_id)`, then retry the tool call.

---

## 7. Async

```python
from pydo.action_gateway.aio import ActionGatewayClient

async with ActionGatewayClient(token=token) as client:
    session = await client.session.create(actor_id="user-123")
    tools = await session.tools()
    response = await client.chat.completions.create(..., tools=tools)
    messages.extend(await session.handle_tool_calls(response))
```

---

## 8. Design notes

- **Session-first.** Bare gateway calls without a session are unsupported.
- **MCP for SDK execution.** `session.url` is the same returned MCP endpoint used by the SDK.
- **Provider pattern.** Chat Completions / Messages / Responses formatting stays in small provider classes.
- **Same DO token** for session create and the returned MCP endpoint.
