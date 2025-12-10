.PHONY: help setup install start stop restart logs build-catalog test-query clean ps

help:
	@echo "RAG Service - Makefile Commands"
	@echo "================================"
	@echo "make setup          - Setup environment and create directories"
	@echo "make install        - Install dependencies với uv"
	@echo "make start          - Start infrastructure services (PostgreSQL, Neo4j, LiteLLM)"
	@echo "make stop           - Stop infrastructure services"
	@echo "make restart        - Restart infrastructure services"
	@echo "make logs           - View logs"
	@echo "make build-catalog  - Build entity catalog"
	@echo "make test-query     - Test query functionality"
	@echo "make dev-run        - Run MCP server locally"
	@echo "make clean          - Stop and remove all volumes"
	@echo "make ps             - Show service status"

setup:
	@echo "Setting up environment..."
	@cp -n env.example .env 2>/dev/null || copy env.example .env 2>nul || true
	@mkdir -p data logs rag_storage schema_docs 2>/dev/null || mkdir data logs rag_storage schema_docs 2>nul || true
	@echo "✓ Setup complete. Don't forget to:"
	@echo "  1. Edit .env and add OPENAI_API_KEY"
	@echo "  2. Copy SQL files to data/ directory"
	@echo "  3. Run 'make install' to install dependencies"

install:
	@echo "Installing dependencies với uv..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install from https://astral.sh/uv"; exit 1; }
	uv pip install -e .
	@echo "✓ Dependencies installed"

start:
	@echo "Starting infrastructure services..."
	docker-compose up -d
	@echo "✓ Infrastructure services started"
	@echo ""
	@echo "Services running:"
	@echo "  - PostgreSQL/PGVector: localhost:5432 (user: postgres, pass: postgres)"
	@echo "  - Neo4j Browser: http://localhost:7474 (user: neo4j, pass: neo4j_local_dev)"
	@echo "  - Neo4j Bolt: localhost:7687"
	@echo "  - LiteLLM Proxy: http://localhost:4000"
	@echo ""
	@echo "Next steps:"
	@echo "  1. make build-catalog  # Build entity catalog"
	@echo "  2. make dev-run        # Run MCP server"

stop:
	@echo "Stopping infrastructure services..."
	docker-compose down
	@echo "✓ Infrastructure services stopped"

restart:
	@echo "Restarting infrastructure services..."
	docker-compose restart
	@echo "✓ Infrastructure services restarted"

logs:
	docker-compose logs -f

build-catalog:
	@echo "Building entity catalog..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uv run python scripts/build_catalog.py
	@echo "✓ Catalog built"

test-query:
	@echo "Testing queries..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uv run python scripts/test_query.py

dev-run:
	@echo "Running MCP server..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uv run python -m src.main

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	@echo "✓ All infrastructure services and volumes removed"

ps:
	@echo "Infrastructure Services Status:"
	@docker-compose ps

health:
	@echo "Checking infrastructure health..."
	@echo ""
	@echo "PostgreSQL:"
	@docker exec -it rag-postgres pg_isready -U postgres -d postgres 2>/dev/null && echo "✓ Healthy" || echo "✗ Not running"
	@echo ""
	@echo "Neo4j:"
	@curl -s http://localhost:7474 >/dev/null && echo "✓ Healthy" || echo "✗ Not running"
	@echo ""
	@echo "LiteLLM:"
	@curl -s http://localhost:4000/health >/dev/null && echo "✓ Healthy" || echo "✗ Not running"

# Dev helpers
dev-install:
	@echo "Installing with dev dependencies..."
	uv pip install -e ".[dev]"
	@echo "✓ Dev dependencies installed"

dev-format:
	@echo "Formatting code..."
	uv run black src/ scripts/
	uv run isort src/ scripts/
	@echo "✓ Code formatted"

dev-test:
	@echo "Running tests..."
	uv run pytest
