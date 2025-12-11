# RAG Service - Database Schema Query System

RAG system for querying database schemas using LightRAG, PGVector, Neo4j, and LiteLLM.

## 📁 Folder Structure

```
service_rag/
├── docker-compose.yml              # Docker configuration for infrastructure (PostgreSQL, Neo4j, LiteLLM)
├── litellm_config.yaml            # Model configuration for LiteLLM proxy
├── pyproject.toml                 # Python project config and dependencies (used with uv)
├── env.example                    # Environment variables template (copy to .env)
├── .python-version                # Python version for uv
├── .gitignore                     # Git ignore file
│
├── src/                           # Main source code
│   ├── main.py                    # FastMCP server - main entry point
│   │
│   ├── core/                      # Core modules
│   │   ├── config.py              # Settings and environment configuration
│   │   └── logging.py             # Logging setup with structlog
│   │
│   ├── models/                    # Data models
│   │   └── schema.py              # Table, Column, ForeignKey models
│   │
│   ├── services/                  # Business logic services
│   │   ├── rag_service.py         # LightRAG wrapper service (includes build_catalog method)
│   │   └── litellm_service.py     # LiteLLM integration
│   │
│   └── utils/                     # Utility modules
│       ├── sql_parser.py          # MySQL and PostgreSQL schema parsers
│       └── entities_catalog.py    # Logic for creating entities & relationships from SQL schemas
│
├── scripts/                       # Utility scripts
│   ├── build_catalog.py           # Script wrapper to build entity catalog (calls RAGService.build_catalog)
│   └── test_query.py              # Script to test queries
│
├── data/                          # SQL schema files (copy 2 SQL files here)
│   ├── vd.sql                    # MySQL schema
│   └── sqlfile.sql               # PostgreSQL schema
│
├── rag_storage/                   # LightRAG working directory (auto-created)
└── schema_docs/                   # Generated markdown docs (auto-created)
```

## 🚀 Project Setup Steps

### Step 1: Install uv

```bash
pip install uv
```

### Step 2: Setup Environment

```bash
# 1. Copy the example env file
copy env.example .env

# 2. Edit the .env file and configure the keys
```

**Important - Configure keys in `.env`:**

1. **OPENAI_API_KEY** (REQUIRED): 
   - Get from https://platform.openai.com/api-keys
   - Replace `your_openai_api_key_here` with your actual key

2. **LITELLM_KEY** (Self-generated):
   - This is a master key YOU DEFINE to protect the LiteLLM proxy
   - Development: Use `sk-1234` (already set)
   - Production: Change to a complex key (e.g., `sk-prod-abc123xyz789`)
   - **Must match** `LITELLM_MASTER_KEY` in `docker-compose.yml`

3. **Database credentials**: Already set for local development

### Step 3: Install Dependencies

```bash
# Install dependencies with uv
uv sync
```

### Step 4: Start Infrastructure Services

```bash
# Start PostgreSQL, Neo4j, and LiteLLM with Docker
docker-compose up -d
```

**Infrastructure services:**
- PostgreSQL/PGVector: `localhost:5432`
- Neo4j Browser: `http://localhost:7474` (neo4j/neo4j_local_dev)
- Neo4j Bolt: `localhost:7687`
- LiteLLM Proxy: `http://localhost:4000`

### Step 5: Build Entity Catalog

```bash
# Run script with uv
uv run python scripts/build_catalog.py
```

**This process will:**
1. Parse 2 SQL files (MySQL and PostgreSQL) using parsers
2. Create 2 separate database nodes
3. Create entities: Database, Table, Column, Owner, Tag
4. Create relationships: HAS_TABLE, HAS_COLUMN, REFERENCES, TAGGED, OWNED_BY
5. Save vectors to PGVector
6. Save graph to Neo4j

**Processing flow:**
```
scripts/build_catalog.py (script wrapper)
    ↓
RAGService.build_catalog() (in src/services/rag_service.py)
    ↓
build_entity_catalog() (in src/utils/entities_catalog.py)
    ↓
sql_parser.py (parse SQL)
    ↓
LightRAG (save to storage)
    ↓
PostgreSQL (vectors) + Neo4j (graph)
```

⏱️ **Duration**: ~5-10 minutes depending on SQL file size

### Step 6: Test Query

```bash
# Test with uv
uv run python scripts/test_query.py
```

### Step 7: Run MCP Server

```bash
# Run service with uv
uv run python -m src.main
```

## 🔍 Example Queries 
```
"Find information related to phone numbers"
"Tables with email columns"
"Foreign key relationships from accommodation table"
"All columns with timestamp type"
"Structure of users table"
"Find tables in MySQL database"
```


## 🏗️ Tech Stack

- **uv**: Fast Python package installer (replaces pip)
- **LightRAG**: RAG framework
- **PGVector**: Vector storage (PostgreSQL extension, runs in Docker)
- **Neo4j**: Graph storage (runs in Docker)
- **LiteLLM**: LLM proxy/gateway (runs in Docker) - supports multiple providers
- **OpenAI API**: LLM and embeddings (gpt-4o-mini, text-embedding-3-small)
- **FastMCP**: MCP server (runs locally)