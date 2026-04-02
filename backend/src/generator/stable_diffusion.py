"""Deterministic Stable Diffusion image generation with pinned configuration."""

import hashlib
import io
import logging

import torch
from diffusers import EulerDiscreteScheduler, StableDiffusionPipeline
from PIL import Image

from src.config import settings

logger = logging.getLogger(__name__)


class StableDiffusionGenerator:
    def __init__(self):
        self.pipe: StableDiffusionPipeline | None = None

    def load_model(self) -> None:
        """Load the Stable Diffusion model with pinned configuration."""
        logger.info(f"Loading SD model: {settings.sd_model}")

        scheduler = EulerDiscreteScheduler.from_pretrained(
            settings.sd_model, subfolder="scheduler"
        )

        self.pipe = StableDiffusionPipeline.from_pretrained(
            settings.sd_model,
            scheduler=scheduler,
            torch_dtype=torch.float32,  # float32 for determinism
            safety_checker=None,
            requires_safety_checker=False,
        )

        # Use GPU if available, otherwise CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = self.pipe.to(device)

        logger.info(f"Model loaded on {device}")

    def generate(self, prompt: str, sd_seed: int) -> Image.Image:
        """Generate an image deterministically from a prompt and seed.

        Args:
            prompt: The fully-formed text prompt.
            sd_seed: Integer seed for the torch generator.

        Returns:
            PIL Image object.
        """
        if self.pipe is None:
            self.load_model()

        generator = torch.Generator(device=self.pipe.device).manual_seed(sd_seed)

        result = self.pipe(
            prompt=prompt,
            num_inference_steps=settings.sd_steps,
            guidance_scale=settings.sd_guidance,
            width=settings.sd_width,
            height=settings.sd_height,
            generator=generator,
        )

        image = result.images[0]
        logger.info(f"Generated image for seed {sd_seed}, hash: {self.image_hash(image)}")
        return image

    @staticmethod
    def image_hash(image: Image.Image) -> str:
        """Compute SHA-256 hash of image bytes (PNG format)."""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return hashlib.sha256(buf.getvalue()).hexdigest()

    @staticmethod
    def image_to_bytes(image: Image.Image) -> bytes:
        """Convert PIL Image to PNG bytes."""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
