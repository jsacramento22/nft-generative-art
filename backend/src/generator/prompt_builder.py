"""Deterministic prompt builder: maps on-chain seed + themeIndex to a specific prompt."""

import json
from pathlib import Path

from src.config import settings


class PromptBuilder:
    def __init__(self, prompts_path: str | None = None):
        path = Path(prompts_path or settings.prompts_path)
        with open(path) as f:
            data = json.load(f)

        self.themes = data["themes"]
        self.variations = data["variations"]

    def build(self, seed_hex: str, theme_index: int) -> str:
        """Build a deterministic prompt from seed and theme index.

        Args:
            seed_hex: The on-chain seed as a hex string (0x-prefixed, 32 bytes).
            theme_index: The theme index assigned on-chain.

        Returns:
            A fully-formed prompt string, deterministic for the given inputs.
        """
        seed_int = int(seed_hex, 16)

        theme = self.themes[theme_index]
        template = theme["template"]

        # Deterministic variation selection using different byte ranges of the seed
        color = self._pick(self.variations["colors"], seed_int, offset=0)
        texture = self._pick(self.variations["textures"], seed_int, offset=1)
        shape = self._pick(self.variations["shapes"], seed_int, offset=2)
        mood = self._pick(self.variations["moods"], seed_int, offset=3)

        prompt = template.format(
            color=color,
            texture=texture,
            shape=shape,
            mood=mood,
        )

        return prompt

    def get_sd_seed(self, seed_hex: str) -> int:
        """Convert on-chain bytes32 seed to a Stable Diffusion integer seed.

        Uses modulo to fit within PyTorch's seed range.
        """
        return int(seed_hex, 16) % (2**32)

    def get_theme_name(self, theme_index: int) -> str:
        return self.themes[theme_index]["name"]

    @staticmethod
    def _pick(options: list, seed_int: int, offset: int) -> str:
        """Pick an option deterministically based on different seed byte ranges."""
        # Use different 8-byte chunks of the 32-byte seed for each parameter
        shifted = seed_int >> (offset * 64)
        index = shifted % len(options)
        return options[index]
