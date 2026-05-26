# pkg-knowledge-mcp

> A [FastMCP v3](https://gofastmcp.com) server that gives Claude Code **live, up-to-date knowledge** about any Python or JavaScript package — fetched directly from PyPI, npm, and GitHub at call time.

Claude Code's training data has a cutoff. When asked to use a library like LangChain it defaults to patterns from training — which may be 1–2 major versions old. This MCP server fixes that by injecting the **current** documentation, changelog, and API reference directly into Claude's context.

---

## Tools

| Tool | What it does |
|---|---|
| `get_docs` | Fetch the latest README / docs for any package. **Start here.** |
| `get_changelog` | Show what changed between two versions. Use for migration tasks. |
| `get_api_ref` | Look up a specific class or function signature. |
| `search_docs` | Keyword search across a package's full docs folder. |

### `get_docs`

```
get_docs(package, ecosystem="python", version=None, section=None)
```

Fetches the README from GitHub. Pass `section=` to extract a specific heading (e.g. `"installation"`, `"quickstart"`, `"agents"`). Checks bundled **skills** first before hitting the network.

### `get_changelog`

```
get_changelog(package, ecosystem="python", from_version=None, to_version=None)
```

Fetches `CHANGELOG.md` from GitHub, falls back to the GitHub Releases API. Filters to the version range you specify.

### `get_api_ref`

```
get_api_ref(package, symbol, ecosystem="python", version=None)
```

Searches the `docs/` directory of the GitHub repo for the symbol name and extracts the matching section. Falls back to the official docs site.

### `search_docs`

```
search_docs(package, query, ecosystem="python", version=None, max_results=5)
```

Walks the `docs/` directory on GitHub, scores each section by keyword overlap, returns the top matches.

---

## Skills

**Skills** are curated `.md` files that live in `skills/`. They contain exactly what Claude Code needs to know about a package: current import paths, breaking changes, idioms, gotchas. Skills are checked **before** any live fetch — they're faster and more focused than a raw README.

### Bundled starter skills

| File | Covers |
|---|---|
| `skills/langchain.md` | 0.3.x import paths, LCEL, removed APIs, RAG, tool calling |
| `skills/fastmcp.md` | v3 decorators, tool vs resource vs prompt, CLI usage |
| `skills/pydantic-v2.md` | v1->v2 migration, validators, ConfigDict, TypeAdapter |

These are committed to the repo and ship with the server.

### Adding your own skill

1. Create `skills/custom/your-package.md`
2. No code changes needed — the loader picks it up automatically
3. Custom skills take priority over bundled ones (same name = override)

```markdown
---
package: your-package
version_tested: 1.2.x
ecosystem: python
source: https://docs.your-package.com
updated: 2025-05-26
---

# Your Package — What Claude Code Needs to Know

## Import Paths
...
```

> **What gets committed?**
> - `skills/*.md` — **yes**, committed. These are the bundled starters.
> - `skills/custom/` — **gitignored**. Add private or personal skills here without polluting the repo.

---

## MCP Resources

| Resource URI | Returns |
|---|---|
| `skill://{package}` | The skill file for a package, or a hint to use `get_docs()` |
| `skill://index` | List of all available skills |

---

## Installation

### Option 1 — Claude Code (recommended, no Docker)

```bash
# Clone the repo
git clone https://github.com/your-username/pkg-knowledge-mcp
cd pkg-knowledge-mcp

cp .env.example .env
# Add your GITHUB_TOKEN to .env (optional but recommended)

# Install into Claude Code (reads fastmcp.json for deps)
fastmcp install claude-code main.py
```

Or without cloning:

```bash
claude mcp add pkg-knowledge -- uv run --with fastmcp --with httpx \
  --with beautifulsoup4 --with markdownify --with python-dotenv \
  --with packaging fastmcp run main.py
```

### Option 2 — Docker Compose

```bash
git clone https://github.com/your-username/pkg-knowledge-mcp
cd pkg-knowledge-mcp

cp .env.example .env
# Edit .env — add GITHUB_TOKEN if you have one

docker compose up -d
```

The server starts on `http://localhost:8000` using SSE transport. Add it to Claude Code:

```bash
claude mcp add pkg-knowledge --transport sse http://localhost:8000/sse
```

To add custom skills without rebuilding:

```bash
# Drop .md files into skills/custom/ — they're volume-mounted at runtime
cp my-skill.md skills/custom/my-package.md
```

### Option 3 — Run locally with uv

```bash
git clone https://github.com/your-username/pkg-knowledge-mcp
cd pkg-knowledge-mcp

cp .env.example .env
uv sync

fastmcp run main.py          # STDIO transport (for Claude Code)
fastmcp dev main.py          # dev mode — opens MCP Inspector in browser
```

---

## Configuration

Copy `.env.example` to `.env`:

```bash
# Raises GitHub API rate limit from 60 -> 5000 req/hr (strongly recommended)
# Create at https://github.com/settings/tokens — no scopes needed for public repos
GITHUB_TOKEN=ghp_...

# Max tokens returned per tool call (~4 chars per token)
DEFAULT_MAX_TOKENS=4000

# httpx request timeout in seconds
REQUEST_TIMEOUT=15
```

---

## Development

```bash
uv sync

# Unit tests only (no network required)
uv run pytest tests/ -v -m "not integration"

# Integration tests (live network)
uv run pytest tests/ -v -m integration

# All tests
uv run pytest tests/ -v

# Dev server with MCP Inspector UI
fastmcp dev main.py
```

### Project layout

```
pkg-knowledge-mcp/
├── main.py                        # FastMCP entrypoint
├── fastmcp.json                   # FastMCP project config
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── skills/                        # curated .md knowledge files
│   ├── langchain.md               #   committed — ships with server
│   ├── fastmcp.md
│   ├── pydantic-v2.md
│   └── custom/                    #   gitignored — your private skills here
└── src/pkg_knowledge/
    ├── resolvers/                 # PyPI + npm -> version + github_repo
    ├── fetchers/                  # GitHub raw + docs site scraper
    ├── processors/                # section extraction, truncation, changelog filter
    ├── skills/                    # loader.py — get_skill() + list_skills()
    └── tools/                     # get_docs, get_changelog, get_api_ref, search_docs
```

---

## How it works

```
Claude Code calls get_docs("langchain")
       │
       ▼
1. Check skills/langchain.md ──exists──▶ return skill (fast, no network)
       │
     not found
       │
       ▼
2. PyPI API -> resolved version + github_repo
       │
       ▼
3. GitHub raw -> README.md
       │
     404 / not found
       │
       ▼
4. Scrape official docs site (fallback)
       │
       ▼
5. extract_section() + truncate_to_tokens() -> return markdown
```
