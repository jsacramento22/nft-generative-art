"""Listens for SeedCommitted events and orchestrates the generation pipeline."""

import asyncio
import logging

from web3 import Web3
from web3.contract import Contract

from src.config import load_contract_abi, settings
from src.generator.prompt_builder import PromptBuilder
from src.generator.stable_diffusion import StableDiffusionGenerator
from src.reveal.token_revealer import TokenRevealer
from src.storage.ipfs_uploader import IPFSUploader

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds


class ChainListener:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        abi = load_contract_abi()
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.contract_address),
            abi=abi,
        )

        self.prompt_builder = PromptBuilder()
        self.sd_generator = StableDiffusionGenerator()
        self.ipfs_uploader = IPFSUploader()
        self.revealer = TokenRevealer()

        self._last_block = 0
        self._processing: set[int] = set()
        self._model_loaded = False

    async def _ensure_model(self) -> None:
        """Load SD model in executor so it doesn't block the event loop."""
        if self._model_loaded:
            return
        logger.info("Loading SD model in background...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sd_generator.load_model)
        self._model_loaded = True
        logger.info("SD model ready")

    async def start(self) -> None:
        """Start listening for events. Loads model, then polls."""
        logger.info("Starting chain listener...")

        # Load SD model without blocking
        await self._ensure_model()

        # Also scan for any unrevealed tokens already on-chain
        await self._catch_up_unrevealed()

        # Start from current block
        self._last_block = self.w3.eth.block_number
        logger.info(f"Listening from block {self._last_block}")

        while True:
            try:
                await self._poll_events()
            except Exception as e:
                logger.error(f"Polling error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

    async def _catch_up_unrevealed(self) -> None:
        """Process any tokens that were minted but never revealed."""
        try:
            total = self.contract.functions.totalMinted().call()
            logger.info(f"Checking {total} existing tokens for unrevealed...")
            for token_id in range(total):
                if token_id in self._processing:
                    continue
                if self.contract.functions.tokenRevealed(token_id).call():
                    continue
                logger.info(f"Found unrevealed token {token_id}, processing...")
                self._processing.add(token_id)
                await self._process_token(token_id)
        except Exception as e:
            logger.error(f"Catch-up error: {e}")

    async def _poll_events(self) -> None:
        """Poll for new SeedCommitted events."""
        current_block = self.w3.eth.block_number

        if current_block <= self._last_block:
            return

        # RPC limits block range; cap at 90 blocks per query
        from_block = self._last_block + 1
        to_block = min(current_block, from_block + 90)

        events = self.contract.events.SeedCommitted.get_logs(
            from_block=from_block,
            to_block=to_block,
        )

        for event in events:
            token_id = event["args"]["tokenId"]

            # Skip if already processing or already revealed
            if token_id in self._processing:
                continue
            if self.contract.functions.tokenRevealed(token_id).call():
                continue

            self._processing.add(token_id)
            # Process in background task so polling continues
            asyncio.create_task(self._process_token(token_id))

        self._last_block = to_block

    async def _process_token(self, token_id: int) -> None:
        """Process a token through the full generation pipeline."""
        try:
            seed_bytes = self.contract.functions.tokenSeeds(token_id).call()
            seed = "0x" + seed_bytes.hex()
            theme_index = self.contract.functions.tokenThemeIndex(token_id).call()

            logger.info(f"Token {token_id}: seed={seed[:18]}... theme={theme_index}")

            # 1. Build prompt
            prompt = self.prompt_builder.build(seed, theme_index)
            sd_seed = self.prompt_builder.get_sd_seed(seed)
            theme_name = self.prompt_builder.get_theme_name(theme_index)
            logger.info(f"Token {token_id} prompt: {prompt[:80]}...")

            # 2. Generate image (CPU-bound, run in executor)
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(
                None, self.sd_generator.generate, prompt, sd_seed
            )
            image_bytes = StableDiffusionGenerator.image_to_bytes(image)
            logger.info(f"Token {token_id} generated ({len(image_bytes)} bytes)")

            # 3. Upload to IPFS
            ipfs_uri = await self.ipfs_uploader.upload_full(
                token_id=token_id,
                image_bytes=image_bytes,
                seed_hex=seed,
                theme_name=theme_name,
                theme_index=theme_index,
                prompt=prompt,
            )
            logger.info(f"Token {token_id} uploaded: {ipfs_uri}")

            # 4. Reveal on-chain
            tx_hash = await loop.run_in_executor(
                None, self.revealer.reveal, token_id, ipfs_uri
            )
            logger.info(f"Token {token_id} REVEALED! TX: {tx_hash}")

        except Exception as e:
            logger.error(f"Failed to process token {token_id}: {e}", exc_info=True)
        finally:
            self._processing.discard(token_id)
