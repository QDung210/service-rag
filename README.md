# RAG Service - Database Schema Query System

Hệ thống RAG cho việc truy vấn schema database sử dụng LightRAG, PGVector, Neo4j và LiteLLM.

## 📁 Cấu Trúc Folder

```
service_rag/
├── docker-compose.yml              # Cấu hình Docker cho infrastructure (PostgreSQL, Neo4j, LiteLLM)
├── litellm_config.yaml            # Cấu hình models cho LiteLLM proxy
├── pyproject.toml                 # Python project config và dependencies (dùng với uv)
├── env.example                    # File mẫu environment variables (copy thành .env)
├── Makefile                       # Các lệnh tiện ích (make start, make build-catalog, etc.)
├── .python-version                # Python version cho uv
├── .gitignore                     # Git ignore file
│
├── src/                           # Source code chính
│   ├── main.py                    # FastMCP server - entry point chính
│   │
│   ├── core/                      # Core modules
│   │   ├── config.py              # Settings và environment configuration
│   │   └── logging.py             # Logging setup với structlog
│   │
│   ├── models/                    # Data models
│   │   └── schema.py              # Table, Column, ForeignKey models
│   │
│   ├── parsers/                   # SQL parsers
│   │   └── sql_parser.py          # MySQL và PostgreSQL schema parsers
│   │
│   ├── services/                  # Business logic services
│   │   ├── rag_service.py         # LightRAG wrapper service
│   │   └── litellm_service.py     # LiteLLM integration
│   │
│   └── ingest/                    # Data ingestion (logic xử lý)
│       └── entities_catalog.py    # Logic tạo entities & relationships từ SQL schemas
│                                   # (Module này được gọi bởi build_catalog.py)
│
├── scripts/                       # Utility scripts (scripts để chạy)
│   ├── build_catalog.py          # ⭐ Script chính để build entity catalog (CHẠY FILE NÀY)
│   └── test_query.py             # Script để test queries
│
├── data/                          # SQL schema files (copy 2 file SQL vào đây)
│   ├── vd.sql                    # MySQL schema
│   └── sqlfile.sql               # PostgreSQL schema
│
├── rag_storage/                   # LightRAG working directory (tự động tạo)
└── schema_docs/                   # Generated markdown docs (tự động tạo)
```

## 🚀 Các Bước Chạy Project

### Bước 1: Cài đặt uv

```bash
pip install uv
# Verify installation
uv --version
```

### Bước 2: Setup Environment

```bash
# 1. Copy file env example
copy env.example .env

# 2. Edit file .env và config các keys
```

**Quan trọng - Config các keys trong `.env`:**

1. **OPENAI_API_KEY** (REQUIRED): 
   - Lấy từ https://platform.openai.com/api-keys
   - Thay `your_openai_api_key_here` bằng key thật

2. **LITELLM_KEY** (Tự tạo):
   - Đây là master key BẠN TỰ ĐỊNH NGHĨA để bảo vệ LiteLLM proxy
   - Development: Dùng `sk-1234` (đã set sẵn)
   - Production: Đổi thành key phức tạp (ví dụ: `sk-prod-abc123xyz789`)
   - **Phải khớp** với `LITELLM_MASTER_KEY` trong `docker-compose.yml`

3. **Database credentials**: Đã set sẵn cho local development

### Bước 3: Install Dependencies

```bash
# Install dependencies với uv
uv sync
```

### Bước 4: Start Infrastructure Services

```bash
# Start PostgreSQL, Neo4j, và LiteLLM với Docker
docker-compose up -d

# Check logs
docker-compose logs -f

# Đợi đến khi tất cả services healthy
docker-compose ps
```

**Services infrastructure:**
- PostgreSQL/PGVector: `localhost:5432`
- Neo4j Browser: `http://localhost:7474` (neo4j/neo4j_local_dev)
- Neo4j Bolt: `localhost:7687`
- LiteLLM Proxy: `http://localhost:4000`

### Bước 5: Build Entity Catalog

```bash
# Chạy script với uv
uv run python scripts/build_catalog.py
```

**Quá trình này sẽ:**
1. Parse 2 SQL files (MySQL và PostgreSQL) bằng parsers
2. Tạo 2 database nodes riêng biệt
3. Tạo entities: Database, Table, Column, Owner, Tag
4. Tạo relationships: HAS_TABLE, HAS_COLUMN, REFERENCES, TAGGED, OWNED_BY
5. Lưu vectors vào PGVector
6. Lưu graph vào Neo4j

**Flow xử lý:**
```
scripts/build_catalog.py (script chạy)
    ↓
src/ingest/entities_catalog.py (logic xử lý)
    ↓
src/parsers/sql_parser.py (parse SQL)
    ↓
src/services/rag_service.py (lưu vào LightRAG)
    ↓
PostgreSQL (vectors) + Neo4j (graph)
```

⏱️ **Thời gian**: ~5-10 phút tùy kích thước SQL files

### Bước 6: Test Query

```bash
# Test với uv
uv run python scripts/test_query.py
```

### Bước 7: Run MCP Server

```bash
# Run service với uv
uv run python -m src.main
```

Service sẽ chạy như một MCP server, sẵn sàng nhận requests từ Claude Desktop.


## 📊 Verify Setup

### Check PostgreSQL/PGVector
```bash
# Check connection
docker exec -it rag-postgres psql -U postgres -d postgres

# Check entities table (sau khi build catalog)
docker exec -it rag-postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM lightrag_vdb_entity;"
```

### Check Neo4j
- Mở http://localhost:7474
- Login: `neo4j` / `neo4j_local_dev`
- Chạy query: `MATCH (n) RETURN count(n)`

### Check LiteLLM
```bash
curl http://localhost:4000/health
```

## 🔍 Example Queries 
Sau khi setup xong và kết nối với Claude Desktop:

```
"Tìm thông tin liên quan đến số điện thoại"
"Các bảng có cột email"
"Foreign key relationships từ bảng accommodation"
"Tất cả columns có kiểu timestamp"
"Cấu trúc của bảng users"
"Tìm các bảng trong MySQL database"
```


## 🏗️ Tech Stack

- **uv**: Fast Python package installer (thay thế pip)
- **LightRAG**: RAG framework
- **PGVector**: Vector storage (PostgreSQL extension, run trong Docker)
- **Neo4j**: Graph storage (run trong Docker)
- **LiteLLM**: LLM proxy/gateway (run trong Docker) - hỗ trợ nhiều providers
- **OpenAI API**: LLM và embeddings (gpt-4o-mini, text-embedding-3-small)
- **FastMCP**: MCP server (run local)

