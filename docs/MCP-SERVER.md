# MemoBrain MCP Server

MCP (Model Context Protocol) server providing executive memory capabilities for AI agents.

## Overview

The MemoBrain MCP Server enables Claude Code and other MCP-compatible clients to maintain persistent memory across agent sessions, track knowledge evolution, and facilitate handoffs between specialized agents.

## Installation

```bash
cd memobrain
source .venv/bin/activate

# Install dependencies
uv pip install "mcp[cli]" python-dotenv anthropic
```

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Required
ZAI_API_KEY=your_api_key_here
ZAI_BASE_URL=https://api.z.ai/api/anthropic
ZAI_MODEL=GLM-4.5-Air
```

### Claude Code Integration

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "memobrain": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/memobrain",
      "env": {
        "PYTHONPATH": "/path/to/memobrain"
      }
    }
  }
}
```

Or use the provided `mcp-config.json`:

```bash
# Copy to Claude Code settings
cat mcp-config.json
```

## Running the Server

### Stdio Transport (for Claude Code)

```bash
cd memobrain
PYTHONPATH=. python -m src.mcp_server
```

### HTTP Transport (for debugging)

```bash
PYTHONPATH=. python -m src.mcp_server --transport http --port 8080
```

---

## Tools Reference

### `memory_init`

Initialize a new memory session for a task.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| task | string | Yes | Description of the task/goal |
| agent | string | No | Agent name (default: "default") |
| session_id | string | No | Custom session ID |

**Returns:** Session info with `session_id`, `nodes`, `status`

**Example:**
```
memory_init("Implement user authentication for Epic-42", agent="architect")
```

---

### `memory_store`

Store knowledge or reasoning episode in memory.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| content | string | Yes | The content to store |
| kind | string | No | Node type: evidence, subtask, decision, insight |
| tags | array | No | Tags for categorization |
| participant | string | No | Who is storing (defaults to session agent) |
| session_id | string | No | Target session |

**Returns:** Node info with `node_id`, `kind`, `tags`

**Example:**
```
memory_store(
  "Decided to use JWT for authentication because of stateless scaling",
  kind="decision",
  tags=["auth", "architecture"]
)
```

---

### `memory_recall`

Optimize memory and retrieve compressed context.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | No | Target session |

**Returns:** Optimized messages and statistics

**Example:**
```
memory_recall()
```

---

### `memory_query`

Query specific knowledge from memory.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| tag | string | No | Filter by tag |
| kind | string | No | Filter by node kind |
| participant | string | No | Filter by participant |
| include_history | boolean | No | Include superseded versions |
| session_id | string | No | Target session |

**Returns:** Matching knowledge nodes

**Example:**
```
memory_query(tag="architecture", kind="decision")
```

---

### `memory_handoff`

Create a handoff summary for transitioning to another agent.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| target_agent | string | Yes | Target agent name |
| focus_tags | array | No | Tags to prioritize |
| include_task | boolean | No | Include original task |
| session_id | string | No | Source session |

**Returns:** Handoff context with prioritized knowledge

**Example:**
```
memory_handoff("dev", focus_tags=["architecture", "api-design"])
```

---

### `memory_save`

Persist memory session to file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | string | No | Custom filename |
| session_id | string | No | Target session |

**Returns:** Save path and status

**Example:**
```
memory_save("epic-42-auth.json")
```

---

### `memory_load`

Load memory session from file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | string | Yes | File to load |
| session_id | string | No | Session ID to use |
| agent | string | No | Agent name |

**Returns:** Loaded session info

**Example:**
```
memory_load("epic-42-auth.json", agent="dev")
```

---

### `memory_status`

Get current memory status and statistics.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | No | Target session or "all" |

**Returns:** Memory statistics

**Example:**
```
memory_status("all")  # Overview of all sessions
memory_status()       # Active session details
```

---

### `memory_switch`

Switch active session.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | Session to activate |

**Returns:** New active session info

**Example:**
```
memory_switch("architect_20240115")
```

---

## BMad Integration Patterns

### Pattern 1: Single Agent Session

```
PM starts Epic planning:

1. memory_init("Epic-42: User Authentication", agent="pm")
2. memory_store("Requirements: OAuth2, JWT, RBAC", kind="evidence", tags=["requirements"])
3. memory_store("Decided: 3 stories for MVP", kind="decision", tags=["planning"])
4. memory_save("epic-42-planning.json")
```

### Pattern 2: Agent Handoff (PM → Architect)

```
PM completes, hands off to Architect:

1. memory_handoff("architect", focus_tags=["requirements", "constraints"])

Architect continues:

2. memory_load("epic-42-planning.json", agent="architect")
3. memory_store("Architecture: NestJS + Passport.js", kind="decision", tags=["architecture"])
4. memory_handoff("dev", focus_tags=["architecture", "api-design"])
```

### Pattern 3: Multi-Session Collaboration

```
Multiple agents work in parallel:

Agent 1 (Backend):
  memory_init("Implement Auth API", agent="dev-backend", session_id="auth-api")
  memory_store("Endpoint: POST /auth/login", tags=["api", "auth"])

Agent 2 (Frontend):
  memory_init("Implement Login UI", agent="dev-frontend", session_id="auth-ui")
  memory_store("Component: LoginForm with validation", tags=["ui", "auth"])

Coordinator queries both:
  memory_switch("auth-api")
  memory_query(tag="api")
  memory_switch("auth-ui")
  memory_query(tag="ui")
```

### Pattern 4: Knowledge Evolution Tracking

```
Track decision changes over time:

1. memory_store("DB: PostgreSQL", kind="decision", tags=["database"])
   # Later, decision changes...
2. memory_store("DB: Changed to MongoDB for flexibility", kind="decision", tags=["database"])
3. memory_query(tag="database", include_history=True)
   # Returns both decisions with timestamps
```

### Pattern 5: Context Optimization

```
Before complex reasoning:

1. memory_recall()  # Compress and optimize memory
2. # Claude now has optimized context with summaries
```

---

## Storage

Memory files are stored in `_bmad-output/memory/` by default.

Structure:
```
_bmad-output/
└── memory/
    ├── pm_20240115_120000.json
    ├── architect_20240115_130000.json
    ├── epic-42-auth.json
    └── ...
```

---

## Troubleshooting

### Server not starting

1. Check Python path: `PYTHONPATH=. python -m src.mcp_server`
2. Verify dependencies: `uv pip install "mcp[cli]"`
3. Check .env file exists with valid API key

### Memory not persisting

1. Check storage path permissions
2. Verify `memory_save()` called before session ends
3. Server auto-saves on shutdown

### API errors

1. Check ZAI_API_KEY is set correctly
2. Verify ZAI_BASE_URL is `https://api.z.ai/api/anthropic`
3. Check model name (GLM-4.5-Air or GLM-4.7)
