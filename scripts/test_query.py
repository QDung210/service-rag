"""Script to test query functionality."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.rag_service import RAGService
from src.core.logging import logger


async def main():
    """Main function to test queries."""
    logger.info("Testing RAG Service Query")
    
    # Initialize RAG service
    rag_service = RAGService()
    await rag_service.initialize()
    
    try:
        # Test queries
        test_queries = [
            "tìm thông tin liên quan đến số điện thoại",
            "các bảng có cột email",
            "foreign key relationships",
            "tables in mysql_application_db",
            "columns with timestamp type"
        ]
        
        for query in test_queries:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Query: {query}")
            logger.info('=' * 60)
            
            result = await rag_service.query(query=query, top_k=5)
            
            if result["success"]:
                logger.info(f"Total chunks: {result['total_chunks']}")
                for chunk_key, chunk_data in result["chunks"].items():
                    logger.info(f"\n{chunk_key}:")
                    logger.info(f"  Entity: {chunk_data['Entity']}")
                    content_preview = chunk_data['Content'][:200]
                    logger.info(f"  Content: {content_preview}...")
            else:
                logger.error(f"Query failed: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await rag_service.finalize()


if __name__ == "__main__":
    asyncio.run(main())

