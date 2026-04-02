"""Main entrypoint: starts the chain listener and verification API concurrently."""

import asyncio
import logging

import uvicorn

from src.api.verification import app
from src.config import settings
from src.listener.chain_listener import ChainListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_api():
    """Run the FastAPI verification server."""
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Start both the chain listener and the API server."""
    logger.info("Starting NFT Generative Art Backend")

    listener = ChainListener()

    await asyncio.gather(
        listener.start(),
        run_api(),
    )


if __name__ == "__main__":
    asyncio.run(main())
