"""Tests for deterministic prompt building."""

from pathlib import Path

import pytest

from src.generator.prompt_builder import PromptBuilder

PROMPTS_PATH = str(Path(__file__).parent.parent.parent / "shared" / "prompts.json")


@pytest.fixture
def builder():
    return PromptBuilder(prompts_path=PROMPTS_PATH)


SEED_A = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
SEED_B = "0x1111111111111111111111111111111111111111111111111111111111111111"


class TestPromptBuilder:
    def test_determinism(self, builder: PromptBuilder):
        """Same seed + theme should always produce the same prompt."""
        prompt1 = builder.build(SEED_A, 0)
        prompt2 = builder.build(SEED_A, 0)
        assert prompt1 == prompt2

    def test_different_seeds_different_prompts(self, builder: PromptBuilder):
        """Different seeds should produce different prompts."""
        prompt_a = builder.build(SEED_A, 0)
        prompt_b = builder.build(SEED_B, 0)
        assert prompt_a != prompt_b

    def test_different_themes_different_prompts(self, builder: PromptBuilder):
        """Different theme indices should produce different base prompts."""
        prompt_0 = builder.build(SEED_A, 0)
        prompt_1 = builder.build(SEED_A, 1)
        assert prompt_0 != prompt_1

    def test_prompt_contains_theme_keywords(self, builder: PromptBuilder):
        """Prompt should contain keywords from the selected theme."""
        # Theme 0 is "Cosmic Nebula"
        prompt = builder.build(SEED_A, 0)
        assert "nebula" in prompt.lower() or "cosmic" in prompt.lower()

    def test_sd_seed_determinism(self, builder: PromptBuilder):
        """SD seed should be deterministic."""
        seed1 = builder.get_sd_seed(SEED_A)
        seed2 = builder.get_sd_seed(SEED_A)
        assert seed1 == seed2

    def test_sd_seed_within_range(self, builder: PromptBuilder):
        """SD seed should fit within uint32 range."""
        sd_seed = builder.get_sd_seed(SEED_A)
        assert 0 <= sd_seed < 2**32

    def test_get_theme_name(self, builder: PromptBuilder):
        assert builder.get_theme_name(0) == "Cosmic Nebula"
        assert builder.get_theme_name(1) == "Abstract Geometry"

    def test_all_themes_produce_valid_prompts(self, builder: PromptBuilder):
        """Every theme index should produce a non-empty prompt."""
        for i in range(5):
            prompt = builder.build(SEED_A, i)
            assert len(prompt) > 20
            assert "{" not in prompt  # No unresolved template vars
