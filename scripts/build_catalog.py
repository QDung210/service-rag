"""Script to build entity catalog from SQL files."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.rag_service import RAGService
from src.ingest.entities_catalog import build_entity_catalog
from src.core.logging import logger


async def main():
    """Main function to build catalog."""
    logger.info("=" * 80)
    logger.info("Building Entity Catalog")
    logger.info("=" * 80)
    
    # Initialize RAG service
    rag_service = RAGService()
    await rag_service.initialize()
    
    try:
        # Build entity catalog
        rag = rag_service.get_rag()
        stats = await build_entity_catalog(rag)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Entity Catalog Built Successfully!")
        logger.info("=" * 80)
        logger.info(f"Statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error building catalog: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup
        await rag_service.finalize()


if __name__ == "__main__":
    asyncio.run(main())

