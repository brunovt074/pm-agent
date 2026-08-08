# PM Agent — Design Spec

**Date:** 2026-08-08
**Status:** Draft
**Goal:** Bidirectional sync agent between ClickUp and local git projects, exposed as an MCP server.

---

## 1. Overview

PM Agent is a Python MCP server (FastMCP) that bridges ClickUp and local git repositories. It provides bidirectional task synchronization, automatic status updates via webhooks, and manual MCP tools for operations like creating ClickUp tasks from spec documents, generating status reports, and linking branches to tasks.

**Key decisions:**

- Python 3.12 + FastMCP, hexagonal architecture (same foundation as cv-pal)
- Single server, project-aware via `.pm-agent.yaml` per repo
- Hybrid automation: webhooks for critical events (PR merged → task complete), MCP tools for manual operations
- Combined mapping: branch ↔ task + conventional commits + task ID references in commit messages

### Supported Projects

| Project | Stack |
|---------|-------|
| cv-pal | Python / Typer / MCP |
| therapy | Python FastAPI + Next.js monorepo |
| customer-fi | Kotlin / Ktor / Compose Multiplatform |
| edu-site | Next.js / React |
| cv-pal-public | Python (mirror of cv-pal) |

---

## 2. Architecture

```
pm-agent/
├── server/
│   ├── domain/            # Pure models, no dependencies
│   │   ├── project.py     # Project, MappingsConfig
│   │   ├── task.py        # Task, CommitRef
│   │   ├── sync_rule.py   # SyncRule
│   │   └── sync_event.py  # SyncEvent
│   ├── application/       # Use cases (orchestration)
│   │   ├── sync_project.py
│   │   ├── create_tasks_from_spec.py
│   │   ├── generate_status_report.py
│   │   └── handle_webhook.py
│   ├── infrastructure/    # External adapters
│   │   ├── clickup_adapter.py    # ClickUp API v2
│   │   ├── git_adapter.py        # git CLI wrappers
│   │   └── webhook_listener.py   # FastAPI endpoint
│   └── interfaces/        # Entry points
│       ├── mcp_tools.py          # FastMCP tool definitions
│       └── webhook_routes.py     # HTTP webhook handlers
├── pyproject.toml
├── .env.example
└── .pm-agent.yaml.example
```

**Layer rules:**
- Domain never imports infrastructure
- Application depends on domain ports (protocols)
- Infrastructure implements domain ports
- Interfaces wire everything together

---

## 3. Project Configuration

Each project declares its ClickUp mapping via `.pm-agent.yaml` at the repo root. The agent auto-detects it from the working directory.

```yaml
project:
  name: therapy
  clickup_workspace_id: "90123456"
  git_root: "."

mappings:
  lists:
    - clickup_list_id: "123"
      clickup_list_name: "Backlog"
      convention: "feature,fix"
    - clickup_list_id: "124"
      clickup_list_name: "Bugs"
      convention: "fix,hotfix"

  statuses:
    "in progress":
      branch_state: "active"
      action: "create_branch"
    "in review":
      branch_state: "pr_open"
      action: "create_pr"
    "complete":
      branch_state: "merged"
      action: "none"

  commit_patterns:
    task_id: "CU-[a-z0-9]+"
    conventional: ["feat", "fix", "chore", "docs", "refactor", "test"]

  branch_pattern: "{type}/{task_id}-{slug}"

webhooks:
  github_secret: "${GITHUB_WEBHOOK_SECRET}"
  clickup_secret: "${CLICKUP_WEBHOOK_SECRET}"
```

---

## 4. MCP Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `sync_project` | `direction: "full" \| "clickup_to_git" \| "git_to_clickup"` | Full or directional sync |
| `link_branch` | `task_id: str, branch_name: str` | Link a git branch to a ClickUp task |
| `create_tasks_from_spec` | `spec_path: str, clickup_list_id: str` | Parse spec doc → Create task hierarchy in ClickUp |
| `status_report` | `format: "text" \| "json"` | Consolidated report: tasks, branches, PRs, recent commits |
| `move_task` | `task_id: str, new_status: str` | Move ClickUp task to a new status |
| `comment_on_task` | `task_id: str, comment: str` | Add a comment to a ClickUp task |
| `configure_project` | interactive | Conversational setup of `.pm-agent.yaml` |
| `listen_status` | `action: "start" \| "stop" \| "status"` | Manage the webhook listener |
| `create_branch_from_task` | `task_id: str` | Create a git branch following the configured pattern |

---

## 5. Sync Rules — Bidirectional Mapping

### 5.1 ClickUp → Git

| ClickUp Event | Git Action |
|---------------|------------|
| Task moved to "In Progress" | Create branch `{type}/{task_id}-{slug}` if none exists |
| Task moved to "Complete" | If PR open, comment reminder to merge |
| Task created | Log event, no automatic branch creation |

### 5.2 Git → ClickUp

| Git Event | ClickUp Action |
|-----------|---------------|
| Branch created matching pattern | Find task, move to "In Progress", comment with branch name |
| PR opened referencing task ID | Move to "In Review", comment with PR link |
| PR merged | Move to "Complete", comment with merge SHA |
| Commit with task ID reference | Comment on task with commit message |
| Conventional commit with task ID | Comment + update task metadata |

### 5.3 Task ID Detection Order

1. Branch name: parse `{type}/{task_id}-{slug}`
2. Commit message: regex match `CU-[a-z0-9]+`
3. PR title/body: regex match
4. Manual link via `link_branch` tool

---

## 6. Webhook Listener

The agent optionally runs an HTTP server (`--serve` mode) to receive webhooks.

**Endpoints:**

- `POST /webhooks/github` — push, pull_request, create events
- `POST /webhooks/clickup` — taskUpdated, taskCreated, taskCommentPosted

**Security:** HMAC signature verification using secrets from `.pm-agent.yaml`.

**Startup:**
```
pm-agent serve --port 9090
```

Without `--serve`, the agent runs as a pure MCP server (stdio) and all sync is manual via tools.

---

## 7. Data Flow

```
OpenCode / Claude Code
       │
       │ MCP tools (stdio)
       ▼
┌──────────────┐
│  PM Agent    │
│              │
│  ┌────────┐  │   HTTP       ┌──────────┐
│  │ClickUp │──┼──────────────► ClickUp  │
│  │Adapter │  │              │ API v2   │
│  └────────┘  │              └──────────┘
│              │
│  ┌────────┐  │   subprocess  ┌──────────┐
│  │ Git    │──┼──────────────► git CLI  │
│  │Adapter │  │              └──────────┘
│  └────────┘  │
│              │
│  ┌────────┐  │   HTTP (in)   ┌──────────┐
│  │Webhook │◄─┼───────────────│ GitHub   │
│  │Listener│  │   webhooks    │ ClickUp  │
│  └────────┘  │              └──────────┘
└──────────────┘
```

---

## 8. Dependencies

```
python = "^3.12"
fastmcp = "^2.0"
httpx = "^0.27"         # ClickUp API calls
pydantic = "^2.0"
pyyaml = "^6.0"         # .pm-agent.yaml parsing
uvicorn = "^0.30"       # webhook listener (optional)
starlette = "^0.38"     # webhook routes
python-dotenv = "^1.0"  # env variable loading
```

---

## 9. Environment Variables

```
CLICKUP_API_TOKEN=           # ClickUp personal API token
GITHUB_TOKEN=                # GitHub personal access token (for PR comments)
GITHUB_WEBHOOK_SECRET=       # HMAC secret for GitHub webhooks
CLICKUP_WEBHOOK_SECRET=      # HMAC secret for ClickUp webhooks
PM_AGENT_PORT=9090           # Webhook listener port (default: 9090)
```

---

## 10. Out of Scope (v1)

- Multi-user ClickUp workspaces
- Jira / Linear / Trello adapters
- Time tracking sync
- Automated changelog generation
- Slack/Discord notifications
- Scheduled/poll-based sync (cron)
