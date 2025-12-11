"""Utility for formatting query results into hierarchical chunks."""

from typing import Callable, Any
from src.core.logging import logger


async def format_chunks_hierarchical(
    results: list,
    get_neo4j_description: Callable[[str], Any]
) -> dict:
    """
    Format query results into hierarchical chunks: Database → Table → Column
    
    Args:
        results: List of query results from entity_vdb.query()
        get_neo4j_description: Async function to get entity description from Neo4j
        
    Returns:
        Dictionary with 'chunks' and 'total_chunks'
    """
    chunks = {}
    chunk_idx = 1
    seen_databases = set()
    seen_tables = set()
    
    for result in results:
        entity_name = result.get('entity_name', 'N/A')
        
        # Get description from Neo4j
        content = await get_neo4j_description(entity_name)
        
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
                db_name, table_name = parts[0], parts[1]
                
                # Add Database (only once per database)
                db_key = f"Database:{db_name}"
                if db_key not in seen_databases:
                    db_content = await get_neo4j_description(db_key) or f"Database: {db_name}"
                    chunks[f"chunk{chunk_idx}"] = {"Entity": db_key, "Content": db_content}
                    chunk_idx += 1
                    seen_databases.add(db_key)
                
                # Add Table (only once per table)
                table_key = f"Table:{db_name}.{table_name}"
                if table_key not in seen_tables:
                    table_content = await get_neo4j_description(table_key) or f"Table: {table_name} in database {db_name}"
                    chunks[f"chunk{chunk_idx}"] = {"Entity": table_key, "Content": table_content}
                    chunk_idx += 1
                    seen_tables.add(table_key)
                
                # Add Column
                chunks[f"chunk{chunk_idx}"] = {"Entity": entity_name, "Content": content or entity_name}
                chunk_idx += 1
        
        elif entity_type == 'Table':
            # Table format: "database.table"
            parts = name.split('.')
            if len(parts) >= 2:
                db_name = parts[0]
                
                # Add Database (only once per database)
                db_key = f"Database:{db_name}"
                if db_key not in seen_databases:
                    db_content = await get_neo4j_description(db_key) or f"Database: {db_name}"
                    chunks[f"chunk{chunk_idx}"] = {"Entity": db_key, "Content": db_content}
                    chunk_idx += 1
                    seen_databases.add(db_key)
                
                # Add Table
                chunks[f"chunk{chunk_idx}"] = {"Entity": entity_name, "Content": content or entity_name}
                chunk_idx += 1
        
        else:
            # For other types (Database, etc.)
            if not content:
                content = await get_neo4j_description(entity_name) or entity_name
            
            chunks[f"chunk{chunk_idx}"] = {"Entity": entity_name, "Content": content}
            chunk_idx += 1
    
    logger.debug(f"Formatted {len(chunks)} chunks from {len(results)} results")
    
    return {
        "total_chunks": len(chunks),
        "chunks": chunks
    }

