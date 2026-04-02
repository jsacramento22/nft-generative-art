import json
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Polygon RPC
    rpc_url: str = "https://rpc-amoy.polygon.technology"

    # Contract
    contract_address: str = ""
    backend_private_key: str = ""

    # Pinata IPFS
    pinata_api_key: str = ""
    pinata_secret_key: str = ""

    # Stable Diffusion
    sd_model: str = "stabilityai/stable-diffusion-2-1"
    sd_steps: int = 50
    sd_guidance: float = 7.5
    sd_width: int = 512
    sd_height: int = 512

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Paths
    prompts_path: str = str(
        Path(__file__).parent.parent.parent / "shared" / "prompts.json"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def load_contract_abi() -> list:
    abi_path = (
        Path(__file__).parent.parent.parent
        / "contracts"
        / "artifacts"
        / "contracts"
        / "GenerativeNFT.sol"
        / "GenerativeNFT.json"
    )
    with open(abi_path) as f:
        artifact = json.load(f)
    return artifact["abi"]
