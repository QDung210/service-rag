"""Script to test query functionality."""

import asyncio
import json
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
            "tìm thông tin liên quan đến số điện thoại"
        ]
        
        for query in test_queries:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Query: {query}")
            logger.info('=' * 60)
            
            result = await rag_service.query(query=query, top_k=5)
            
            # Print full result as JSON
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await rag_service.finalize()


if __name__ == "__main__":
    asyncio.run(main())

