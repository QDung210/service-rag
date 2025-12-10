"""RAG Service using LightRAG with PGVector and Neo4j."""

from lightrag import LightRAG, QueryParam
from lightrag.kg.neo4j_impl import Neo4JStorage
from lightrag.kg.postgres_impl import PGVectorStorage

from src.core.config import settings
from src.core.logging import logger
from src.services.litellm_service import litellm_complete, litellm_embed


class RAGService:
    """RAG Service wrapper for LightRAG."""
    
    def __init__(self):
        """Initialize RAG service."""
        self.rag: LightRAG | None = None
    
    async def initialize(self) -> None:
        """Initialize LightRAG with PGVector and Neo4j."""
        logger.info("Initializing RAG Service...")
        
        # Create LightRAG instance
        # LightRAG will read config from .env file (loaded by pydantic-settings)
        self.rag = LightRAG(
            working_dir=settings.WORKING_DIR,
            embedding_func=litellm_embed,
            llm_model_func=litellm_complete,
            llm_model_name=settings.LLM_MODEL,
            
            # Use PGVector for vector storage
            vector_storage="PGVectorStorage",
            
            # Use Neo4j for graph storage
            graph_storage="Neo4JStorage",
        )
        
        # Initialize storages
        await self.rag.initialize_storages()
        
        logger.info("✓ RAG Service initialized successfully")
        logger.info(f"  - Working directory: {settings.WORKING_DIR}")
        logger.info(f"  - Vector storage: PGVector ({settings.POSTGRES_HOST})")
        logger.info(f"  - Graph storage: Neo4j ({settings.NEO4J_URI})")
        logger.info(f"  - LLM: {settings.LLM_MODEL} (via LiteLLM)")
        logger.info(f"  - Embedding: {settings.EMBEDDING_MODEL}")
    
    async def finalize(self) -> None:
        """Finalize RAG service."""
        if self.rag:
            await self.rag.finalize_storages()
            logger.info("RAG Service finalized")
    
    async def query(
        self,
        query: str,
        mode: str = "global",
        top_k: int = 10
    ) -> dict:
        """
        Query the RAG system.
        
        Args:
            query: The search query
            mode: Query mode (local, global, hybrid, naive)
            top_k: Number of results to return
            
        Returns:
            Dictionary with query results
        """
        if not self.rag:
            raise RuntimeError("RAG Service not initialized")
        
        logger.info(f"Querying RAG: '{query}' (mode={mode}, top_k={top_k})")
        
        try:
            # Query the vector database for entities
            entity_vdb = self.rag.entities_vdb
            results = await entity_vdb.query(query, top_k=top_k)
            
            # Format results as chunks
            chunks = {}
            chunk_idx = 1
            
            for result in results:
                entity_name = result.get('entity_name', 'N/A')
                content = result.get('content', '')
                
                # Parse entity type and name
                if ':' in entity_name:
                    entity_type, name = entity_name.split(':', 1)
                else:
                    entity_type, name = 'Unknown', entity_name
                
                # Build hierarchy based on entity type
                if entity_type == 'Column':
                    # Column format: "database.table.column"
                    parts = name.split('.')
                    if len(parts) >= 3:
                        db_name, table_name, col_name = parts[0], parts[1], '.'.join(parts[2:])
                        
                        # Add Database
                        db_key = f"Database:{db_name}"
                        chunks[f"chunk{chunk_idx}"] = {
                            "Entity": db_key,
                            "Content": f"Database: {db_name}"
                        }
                        chunk_idx += 1
                        
                        # Add Table
                        table_key = f"Table:{db_name}.{table_name}"
                        chunks[f"chunk{chunk_idx}"] = {
                            "Entity": table_key,
                            "Content": f"Table: {table_name} in database {db_name}"
                        }
                        chunk_idx += 1
                        
                        # Add Column (the matched entity)
                        chunks[f"chunk{chunk_idx}"] = {
                            "Entity": entity_name,
                            "Content": content
                        }
                        chunk_idx += 1
                
                elif entity_type == 'Table':
                    # Table format: "database.table"
                    parts = name.split('.')
                    if len(parts) >= 2:
                        db_name = parts[0]
                        
                        # Add Database
                        db_key = f"Database:{db_name}"
                        chunks[f"chunk{chunk_idx}"] = {
                            "Entity": db_key,
                            "Content": f"Database: {db_name}"
                        }
                        chunk_idx += 1
                    
                    # Add Table (the matched entity)
                    chunks[f"chunk{chunk_idx}"] = {
                        "Entity": entity_name,
                        "Content": content
                    }
                    chunk_idx += 1
                
                else:
                    # For other types, just return the entity
                    chunks[f"chunk{chunk_idx}"] = {
                        "Entity": entity_name,
                        "Content": content
                    }
                    chunk_idx += 1
            
            logger.info(f"Query completed: {len(chunks)} chunks returned")
            
            return {
                "success": True,
                "query": query,
                "mode": mode,
                "total_chunks": len(chunks),
                "chunks": chunks
            }
        
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "mode": mode,
                "total_chunks": 0,
                "chunks": {}
            }
    
    async def insert(self, text: str) -> None:
        """
        Insert text into RAG system.
        
        Args:
            text: Text to insert
        """
        if not self.rag:
            raise RuntimeError("RAG Service not initialized")
        
        await self.rag.ainsert(text)
        logger.info(f"Inserted text of length {len(text)}")
    
    def get_rag(self) -> LightRAG:
        """Get the underlying LightRAG instance."""
        if not self.rag:
            raise RuntimeError("RAG Service not initialized")
        return self.rag

