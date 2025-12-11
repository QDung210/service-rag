"""Main MCP server application."""
import sys
import asyncio
from pathlib import Path
from fastmcp import FastMCP
from src.core.config import settings
from src.core.logging import logger
from src.services.rag_service import RAGService
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Create FastMCP server
mcp = FastMCP("RAG Query Server")

# Global RAG service
_rag_service: RAGService | None = None


async def initialize_service():
    """Initialize RAG service."""
    global _rag_service
    
    logger.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
    )
    
    # Initialize RAG service
    _rag_service = RAGService()
    await _rag_service.initialize()
    
    logger.info("[READY] - Application is ready to serve requests")


async def finalize_service():
    """Finalize RAG service."""
    global _rag_service
    
    logger.info("application_shutting_down")
    if _rag_service:
        await _rag_service.finalize()
        _rag_service = None
    logger.info("application_shutdown_complete")


@mcp.tool()
async def query_chunks(query: str,mode: str = "global",top_k: int = 10) -> dict:
    """
    Query the knowledge graph and return relevant chunks with full hierarchy.
    
    Args:
        query: The search query
        mode: Query mode (local, global, hybrid, naive)
        top_k: Number of chunks to return
        
    Returns:
        Dictionary with chunks including full path from Database to Column
    """
    logger.info(f"query_chunks called: query='{query}', mode={mode}, top_k={top_k}")
    
    if not _rag_service:
        return {
            "success": False,
            "error": "RAG Service not initialized",
            "query": query,
            "mode": mode,
            "total_chunks": 0,
            "chunks": {}
        }
    
    try:
        result = await _rag_service.query(query=query, mode=mode, top_k=top_k)
        return result
    
    except Exception as e:
        logger.error(f"Error in query_chunks: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "mode": mode,
            "total_chunks": 0,
            "chunks": {}
        }


@mcp.tool()
async def build_catalog() -> dict:
    """
    Build entity catalog from SQL files.
    This should be called after initial setup or when schema changes.
    
    Returns:
        Dictionary with success status and statistics
    """
    logger.info("build_catalog called")
    
    if not _rag_service:
        return {
            "success": False,
            "error": "RAG Service not initialized"
        }
    
    try:
        result = await _rag_service.build_catalog()
        return result
    
    except Exception as e:
        logger.error(f"Error building catalog: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns:
        Dictionary with health status
    """
    logger.info("health_check called")
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {
            "rag_service": "healthy" if _rag_service else "not_initialized",
            "postgres": "healthy",
            "neo4j": "healthy",
            "litellm": "healthy",
        }
    }


if __name__ == "__main__":
    logger.debug("initialized settings", settings=settings)
    asyncio.run(initialize_service())
    mcp.run()

