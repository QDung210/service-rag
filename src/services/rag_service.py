"""RAG Service using LightRAG with PGVector and Neo4j."""

import json
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
        self._neo4j_driver = None  # Cache Neo4j driver
    
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
        # Close Neo4j driver if cached
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            self._neo4j_driver = None
    
    async def _get_neo4j_description(self, entity_name: str) -> str:
        """
        Get entity description from Neo4j.
        
        Args:
            entity_name: Entity ID to query
            
        Returns:
            Description string, empty if not found
        """
        if not entity_name:
            return ''
        
        try:
            # Try to access Neo4j driver
            driver = None
            
            # Method 1: Try _graph_storage (private attribute)
            if hasattr(self.rag, '_graph_storage'):
                graph_storage_obj = self.rag._graph_storage
                if hasattr(graph_storage_obj, 'driver'):
                    driver = graph_storage_obj.driver
                elif hasattr(graph_storage_obj, '_driver'):
                    driver = graph_storage_obj._driver
            
            # Method 2: Try accessing through _storages dict
            if not driver and hasattr(self.rag, '_storages'):
                storages = self.rag._storages
                if 'graph' in storages:
                    graph_storage_obj = storages['graph']
                    if hasattr(graph_storage_obj, 'driver'):
                        driver = graph_storage_obj.driver
                    elif hasattr(graph_storage_obj, '_driver'):
                        driver = graph_storage_obj._driver
            
            # Method 3: Use cached driver or create new one
            if not driver:
                if self._neo4j_driver:
                    driver = self._neo4j_driver
                else:
                    try:
                        from neo4j import AsyncGraphDatabase
                        driver = AsyncGraphDatabase.driver(
                            settings.NEO4J_URI,
                            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
                        )
                        self._neo4j_driver = driver  # Cache it
                    except Exception:
                        return ''
            
            if driver:
                async with driver.session() as session:
                    cypher_query = """
                    MATCH (n {entity_id: $entity_id})
                    RETURN n.description as description
                    LIMIT 1
                    """
                    result = await session.run(cypher_query, entity_id=entity_name)
                    record = await result.single()
                    
                    if record:
                        description = record.get('description', '') or ''
                        return description
        except Exception:
            pass
        
        return ''
    
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
                
                # Debug: log result keys to understand structure
                if chunk_idx == 1:
                    logger.info(f"Sample result keys: {list(result.keys())}")
                    logger.info(f"Sample result structure: {json.dumps({k: str(v)[:100] for k, v in result.items()}, indent=2, ensure_ascii=False)}")
                
                # Try to get content from various possible keys
                content = result.get('content') or result.get('description') or ''
                
                # Try entity_data if available
                if not content:
                    entity_data = result.get('entity_data')
                    if isinstance(entity_data, dict):
                        content = entity_data.get('description') or entity_data.get('content') or ''
                
                # Always try to get full description from graph storage (Neo4j)
                # because entity_vdb.query() may not return full description
                # Query for all entity types (Column, Table, Database) to get rich descriptions
                if entity_name:
                    try:
                        logger.info(f"Attempting to query Neo4j for entity: {entity_name}")
                        
                        # Try to access Neo4j driver from LightRAG's internal storage
                        driver = None
                        
                        # Method 1: Try _graph_storage (private attribute)
                        if hasattr(self.rag, '_graph_storage'):
                            graph_storage_obj = self.rag._graph_storage
                            if hasattr(graph_storage_obj, 'driver'):
                                driver = graph_storage_obj.driver
                            elif hasattr(graph_storage_obj, '_driver'):
                                driver = graph_storage_obj._driver
                        
                        # Method 2: Try accessing through _storages dict
                        if not driver and hasattr(self.rag, '_storages'):
                            storages = self.rag._storages
                            if 'graph' in storages:
                                graph_storage_obj = storages['graph']
                                if hasattr(graph_storage_obj, 'driver'):
                                    driver = graph_storage_obj.driver
                                elif hasattr(graph_storage_obj, '_driver'):
                                    driver = graph_storage_obj._driver
                        
                        # Method 3: Use cached driver or create new one
                        if not driver:
                            if self._neo4j_driver:
                                driver = self._neo4j_driver
                            else:
                                try:
                                    from neo4j import AsyncGraphDatabase
                                    driver = AsyncGraphDatabase.driver(
                                        settings.NEO4J_URI,
                                        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
                                    )
                                    self._neo4j_driver = driver  # Cache it
                                    logger.info("Created new Neo4j driver from config")
                                except Exception as driver_error:
                                    logger.debug(f"Could not create Neo4j driver: {driver_error}")
                        
                        if driver:
                            logger.info(f"Found Neo4j driver, querying...")
                            async with driver.session() as session:
                                # Query entity node by entity_id
                                cypher_query = """
                                MATCH (n {entity_id: $entity_id})
                                RETURN n.description as description, n.entity_data as entity_data
                                LIMIT 1
                                """
                                result = await session.run(cypher_query, entity_id=entity_name)
                                record = await result.single()
                                
                                if not record:
                                    logger.info(f"No node found in Neo4j for entity_id: {entity_name}")
                                else:
                                    logger.info(f"Found node in Neo4j for {entity_name}")
                                
                                if record:
                                    # Get description directly from record
                                    graph_description = record.get('description', '') or ''
                                    
                                    # Also try entity_data if description is empty
                                    if not graph_description:
                                        entity_data_str = record.get('entity_data', '')
                                        if entity_data_str:
                                            try:
                                                if isinstance(entity_data_str, str):
                                                    entity_data = json.loads(entity_data_str)
                                                else:
                                                    entity_data = entity_data_str
                                                if isinstance(entity_data, dict):
                                                    graph_description = entity_data.get('description', '') or entity_data.get('content', '')
                                            except Exception as parse_error:
                                                logger.debug(f"Error parsing entity_data: {parse_error}")
                                    
                                    if graph_description:
                                        # Always use Neo4j description if available (it's more complete)
                                        content = graph_description
                                        logger.info(f"✓ Found description for {entity_name}: {len(content)} chars")
                                    else:
                                        logger.info(f"✗ No description found in Neo4j for {entity_name}")
                        else:
                            logger.info(f"✗ No Neo4j driver found. graph_storage attributes: {dir(graph_storage)}")
                    except Exception as e:
                        logger.info(f"✗ Error querying Neo4j for {entity_name}: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        # Try alternative method if available
                        try:
                            if hasattr(self.rag.graph_storage, 'get_entity'):
                                entity_info = await self.rag.graph_storage.get_entity(entity_name)
                                if entity_info:
                                    if isinstance(entity_info, dict):
                                        graph_desc = entity_info.get('description') or entity_info.get('content') or ''
                                        if graph_desc:
                                            content = graph_desc
                        except:
                            pass
                
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

