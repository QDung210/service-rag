"""Script to build entity catalog from SQL files."""
import traceback
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.rag_service import RAGService
from src.core.logging import logger


async def main():
    """Main function to build catalog."""
    logger.info("Building Entity Catalog")
    # Initialize RAG service
    rag_service = RAGService()
    await rag_service.initialize()
    try:
        # Build entity catalog
        result = await rag_service.build_catalog()
        logger.info("Entity Catalog Built Successfully!")
        logger.info(f"Result: {result}")
        logger.info("Catalog build process completed. Exiting...")
        
        # Exit successfully after completion
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Error building catalog: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup
        await rag_service.finalize()
        logger.info("RAG service finalized. Process terminated.")


if __name__ == "__main__":
    TIMEOUT_SECONDS = 600
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except SystemExit as e:
        raise
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

