"""FastAPI verification endpoints for provable randomness."""

import asyncio
import logging
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3

from src.config import load_contract_abi, settings
from src.generator.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NFT Generative Art - Verification API",
    description="Verify that NFT art generation was honest and deterministic.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting: max 5 regenerations per IP per hour
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 5
RATE_WINDOW = 3600  # 1 hour

prompt_builder = PromptBuilder()
sd_generator = None  # Lazy loaded


def get_sd_generator():
    global sd_generator
    if sd_generator is None:
        try:
            from src.generator.stable_diffusion import StableDiffusionGenerator
            sd_generator = StableDiffusionGenerator()
            sd_generator.load_model()
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Stable Diffusion not available. Install torch and diffusers.",
            )
    return sd_generator


def get_contract():
    w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
    abi = load_contract_abi()
    return w3.eth.contract(
        address=Web3.to_checksum_address(settings.contract_address),
        abi=abi,
    )


class VerifyResponse(BaseModel):
    token_id: int
    seed: str
    theme_index: int
    theme_name: str
    prompt: str
    sd_seed: int
    sd_model: str
    sd_steps: int
    sd_guidance: float
    sd_width: int
    sd_height: int
    revealed: bool
    ipfs_uri: str | None


class RegenerateRequest(BaseModel):
    seed: str
    theme_index: int


class RegenerateResponse(BaseModel):
    prompt: str
    sd_seed: int
    image_hash_sha256: str


@app.get("/api/verify/{token_id}", response_model=VerifyResponse)
async def verify_token(token_id: int):
    """Get all generation parameters for a token so anyone can verify."""
    try:
        contract = get_contract()

        seed_bytes = contract.functions.tokenSeeds(token_id).call()
        seed_hex = "0x" + seed_bytes.hex()
        theme_index = contract.functions.tokenThemeIndex(token_id).call()
        revealed = contract.functions.tokenRevealed(token_id).call()

        ipfs_uri = None
        if revealed:
            ipfs_uri = contract.functions.tokenIPFSURIs(token_id).call()

        prompt = prompt_builder.build(seed_hex, theme_index)
        sd_seed = prompt_builder.get_sd_seed(seed_hex)
        theme_name = prompt_builder.get_theme_name(theme_index)

        return VerifyResponse(
            token_id=token_id,
            seed=seed_hex,
            theme_index=theme_index,
            theme_name=theme_name,
            prompt=prompt,
            sd_seed=sd_seed,
            sd_model=settings.sd_model,
            sd_steps=settings.sd_steps,
            sd_guidance=settings.sd_guidance,
            sd_width=settings.sd_width,
            sd_height=settings.sd_height,
            revealed=revealed,
            ipfs_uri=ipfs_uri,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Token not found: {e}")


@app.post("/api/regenerate", response_model=RegenerateResponse)
async def regenerate(request: RegenerateRequest):
    """Re-generate image from seed and theme for verification. Rate limited."""
    # Simple IP-based rate limiting would need request info;
    # for now just use a global counter
    now = time.time()
    key = "global"
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_WINDOW]
    if len(_rate_limits[key]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 5 regenerations per hour.",
        )
    _rate_limits[key].append(now)

    prompt = prompt_builder.build(request.seed, request.theme_index)
    sd_seed = prompt_builder.get_sd_seed(request.seed)

    gen = get_sd_generator()
    loop = asyncio.get_event_loop()
    image = await loop.run_in_executor(None, gen.generate, prompt, sd_seed)
    from src.generator.stable_diffusion import StableDiffusionGenerator
    image_hash = StableDiffusionGenerator.image_hash(image)

    return RegenerateResponse(
        prompt=prompt,
        sd_seed=sd_seed,
        image_hash_sha256=image_hash,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "sd_model_loaded": sd_generator is not None}
