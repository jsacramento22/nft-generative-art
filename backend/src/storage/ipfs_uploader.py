"""Upload images and metadata to IPFS via Pinata."""

import hashlib
import json
import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

PINATA_PIN_FILE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"


class IPFSUploader:
    def __init__(self):
        self.headers = {
            "pinata_api_key": settings.pinata_api_key,
            "pinata_secret_api_key": settings.pinata_secret_key,
        }

    async def upload_image(self, image_bytes: bytes, filename: str) -> str:
        """Upload image bytes to Pinata and return the IPFS CID."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                PINATA_PIN_FILE_URL,
                headers=self.headers,
                files={"file": (filename, image_bytes, "image/png")},
                data={
                    "pinataMetadata": json.dumps({"name": filename}),
                },
            )
            response.raise_for_status()
            cid = response.json()["IpfsHash"]
            logger.info(f"Image pinned: ipfs://{cid}")
            return cid

    async def upload_metadata(
        self,
        token_id: int,
        image_cid: str,
        seed_hex: str,
        theme_name: str,
        theme_index: int,
        prompt: str,
        image_hash: str,
    ) -> str:
        """Upload ERC-721 metadata JSON to Pinata and return the IPFS CID."""
        metadata = {
            "name": f"Generative Art #{token_id}",
            "description": (
                f"AI-generated art with provable randomness. "
                f"Seed: {seed_hex}"
            ),
            "image": f"ipfs://{image_cid}",
            "attributes": [
                {"trait_type": "Theme", "value": theme_name},
                {"trait_type": "Theme Index", "value": str(theme_index)},
                {"trait_type": "Seed", "value": seed_hex},
                {"trait_type": "Prompt", "value": prompt},
            ],
            "properties": {
                "seed": seed_hex,
                "themeIndex": theme_index,
                "prompt": prompt,
                "sd_model": settings.sd_model,
                "sd_steps": settings.sd_steps,
                "sd_guidance": settings.sd_guidance,
                "sd_width": settings.sd_width,
                "sd_height": settings.sd_height,
                "image_hash_sha256": image_hash,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PINATA_PIN_JSON_URL,
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "pinataContent": metadata,
                    "pinataMetadata": {
                        "name": f"generative-art-{token_id}-metadata.json"
                    },
                },
            )
            response.raise_for_status()
            cid = response.json()["IpfsHash"]
            logger.info(f"Metadata pinned: ipfs://{cid}")
            return cid

    async def upload_full(
        self,
        token_id: int,
        image_bytes: bytes,
        seed_hex: str,
        theme_name: str,
        theme_index: int,
        prompt: str,
    ) -> str:
        """Upload image and metadata, return the metadata IPFS URI."""
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        image_cid = await self.upload_image(
            image_bytes, f"generative-art-{token_id}.png"
        )

        metadata_cid = await self.upload_metadata(
            token_id=token_id,
            image_cid=image_cid,
            seed_hex=seed_hex,
            theme_name=theme_name,
            theme_index=theme_index,
            prompt=prompt,
            image_hash=image_hash,
        )

        return f"ipfs://{metadata_cid}"
