# mcp-registry

A small, end-to-end walkthrough of the **MLflow MCP Server Registry**: build MCP servers with
[FastMCP](https://github.com/jlowin/fastmcp), call them with a FastMCP client, then register them
in MLflow so they are discoverable — with versions, access endpoints, and auto-discovered tools.

The repo has three moving parts:

| Part | Path | What it does |
| --- | --- | --- |
| MCP servers | `src/` | Two FastMCP servers — a toy greeting server and a real PostgreSQL explorer |
| MCP clients | `clients/` | Thin FastMCP clients that invoke tools over streamable HTTP |
| Registry utility | `mlflow_mcp_registry_util.py` | Registers servers with MLflow, refreshes their tools, lists access endpoints |

---

## Requirements

- Python **≥ 3.13**
- An MLflow tracking server (v3.15+) running locally — the registry APIs are server-side
- PostgreSQL, if you want to exercise the PostgreSQL server
- [`uv`](https://docs.astral.sh/uv/) (the repo ships a `uv.lock`)

Dependencies (`pyproject.toml`): `fastmcp>=3.4.7`, `mlflow>=3.15.1`, `psycopg2` + `psycopg2-binary`,
`python-dotenv`.

```bash
uv sync
```

---

## Configuration

The PostgreSQL server reads its connection settings from a `.env` file in the repo root
(loaded via `python-dotenv`). `.env` is gitignored — create your own:

```bash
PGHOST=localhost
PGPORT=5432
PGUSER=root
PGPASSWORD=root
PGSSLMODE=prefer
PGADMINDB=postgres
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `PGHOST` | `localhost` | Server host |
| `PGPORT` | `5432` | Server port |
| `PGUSER` | `root` | Login role |
| `PGPASSWORD` | `root` | Password |
| `PGSSLMODE` | `prefer` | libpq SSL mode |
| `PGADMINDB` | `postgres` | Database used for server-wide queries (`ListDatabases`) |

`src/simple_server.py` needs no configuration.

---

## 1. Start an MLflow tracking server

`mlflow_mcp_registry_util.py` points at `http://127.0.0.1:5000`. The repo already contains a
`mlflow.db` (gitignored) from a SQLite-backed run:

```bash
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

If your server lives elsewhere, edit the `mlflow.set_tracking_uri(...)` call at the top of
`mlflow_mcp_registry_util.py`.

---

## 2. Run an MCP server

Both servers bind **port 8000** over streamable HTTP (`http://localhost:8000/mcp`), so run one at a
time — or change the port in the `mcp.run(...)` call.

**Simple greeting server** — two tools, `Greeting` and `Sendoff`:

```bash
uv run python src/simple_server.py
```

**PostgreSQL explorer** — read-only introspection of a live PostgreSQL server:

```bash
uv run python src/postgresql_mcp.py
```

Or via the FastMCP CLI:

```bash
uv run fastmcp run src/postgresql_mcp.py --transport http --port 8000
```

### PostgreSQL tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `ListDatabases` | — | Non-template databases with owner and pretty-printed size |
| `ListSchemas` | `database` | User-defined schemas (system schemas and temp schemas excluded) |
| `ListTables` | `database`, `schema` | Tables and views in the schema, with `table_type` |
| `ListTableColumns` | `database`, `schema`, `table` | Column name, type, nullability, default — in ordinal order |
| `ListTableRelations` | `database`, `schema`, `table` | Foreign keys split into `outgoing` (this table → others) and `incoming` (others → this table) |
| `ListSchemaRelations` | `database`, `schema` | Flat edge list `from_table.from_column → to_table.to_column` for the whole schema — an ERD in list form |

Every tool goes through `_query()`, which opens a fresh connection to the named database, runs a
single parameterised `SELECT` through a `RealDictCursor`, and closes the connection. Nothing writes.

---

## 3. Call a server from a client

With a server running on port 8000:

```bash
uv run python clients/postgres_server_client.py   # calls ListDatabases, prints each database name
uv run python clients/simple_server_client.py     # calls the greeting tool with "Ford"
```

`clients/postgres_server_client.py` unwraps the FastMCP result: each item in `result.content` carries
a JSON `text` payload, which it parses and reads `database` from.

> **Note:** `clients/simple_server_client.py` calls `client.call_tool("greet", ...)`, but the tool in
> `src/simple_server.py` is registered under the name `Greeting` (`greet` is only the Python function
> name). Use `"Greeting"` for the call to resolve.

---

## 4. Register servers with MLflow

`mlflow_mcp_registry_util.py` holds four coroutines, each demonstrating one registry API:

### `register_postgresql_mcp_server()`

Registers a **remote** server — one that is already running and reachable over HTTP:

```python
mlflow.genai.register_mcp_server(
    server_json={
        "name": "io.github.pavanjava/postgresql-server",
        "version": "0.1.0",
        "description": "PostgreSQL FastMCP server exposing DB tools",
        "remotes": [{"url": "http://localhost:8000/mcp", "type": "streamable-http"}],
    },
    status="active",
    source="local dev server via fastmcp",
    create_access_endpoints_from_remotes=True,
)
```

`create_access_endpoints_from_remotes=True` turns each entry in `remotes` into an MLflow **access
endpoint**, so consumers can resolve a connection URL from the registry instead of hardcoding it.

### `register_qdrant_mcp_server()`

Registers a **packaged** server instead — no running process required. The entry describes how to
launch it (`uvx mcp-server-qdrant` over stdio) and declares its environment variables, including
which are required and which are secret (`QDRANT_API_KEY`).

### `discover_tools()`

Calls `refresh_mcp_server_version_tools(...)`. MLflow connects to the registered server version,
enumerates its tools, and persists them on the version — after which `server_version.tools` lists the
discovered tool names. This requires the server to actually be reachable.

### `list_endpoints()`

Calls `search_mcp_access_endpoints(server_name=...)` and prints each endpoint's URL, transport type,
and the server version it resolves to.

### Running it

The `__main__` block runs one coroutine at a time; the rest are commented out. Uncomment the one you
want:

```python
if __name__ == "__main__":
    # asyncio.run(register_postgresql_mcp_server())
    asyncio.run(register_qdrant_mcp_server())
    # asyncio.run(discover_tools())
    # asyncio.run(list_endpoints())
```

```bash
uv run python mlflow_mcp_registry_util.py
```

Registered servers then show up under the **MCP Servers** section of the MLflow UI at
`http://127.0.0.1:5000`.

---

## Suggested end-to-end path

1. Start MLflow on port 5000.
2. Start the PostgreSQL MCP server on port 8000.
3. Verify it answers: `uv run python clients/postgres_server_client.py`.
4. Register it: uncomment `register_postgresql_mcp_server()` and run the util.
5. Discover its tools: switch to `discover_tools()` and run again — the six tools above should print.
6. Inspect its access endpoint: switch to `list_endpoints()`.
7. Browse the result in the MLflow UI.

---

## Repository layout

```
.
├── src/
│   ├── simple_server.py        # FastMCP "My MCP Server" — Greeting + Sendoff tools
│   └── postgresql_mcp.py       # FastMCP "PostgreSQL Explorer" — 6 read-only introspection tools
├── clients/
│   ├── simple_server_client.py     # calls a tool on the greeting server
│   └── postgres_server_client.py   # calls ListDatabases and prints database names
├── mlflow_mcp_registry_util.py # MLflow MCP registry: register / refresh tools / list endpoints
├── pyproject.toml
└── uv.lock
```

`mlflow.db`, `.env`, `.venv`, and `.idea` are gitignored.
