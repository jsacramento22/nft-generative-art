"""Calls contract.revealToken() to set the IPFS URI on-chain."""

import logging
import time

from web3 import Web3
from web3.contract import Contract

from src.config import load_contract_abi, settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class TokenRevealer:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.account = self.w3.eth.account.from_key(settings.backend_private_key)
        abi = load_contract_abi()
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.contract_address),
            abi=abi,
        )

    def reveal(self, token_id: int, ipfs_uri: str) -> str:
        """Submit revealToken transaction and return the tx hash."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                nonce = self.w3.eth.get_transaction_count(self.account.address)

                gas_price = self.w3.eth.gas_price
                tx = self.contract.functions.revealToken(
                    token_id, ipfs_uri
                ).build_transaction(
                    {
                        "from": self.account.address,
                        "nonce": nonce,
                        "gas": 120_000,
                        "gasPrice": gas_price,
                    }
                )

                signed = self.w3.eth.account.sign_transaction(
                    tx, self.account.key
                )
                tx_hash = self.w3.eth.send_raw_transaction(
                    signed.raw_transaction
                )
                receipt = self.w3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=120
                )

                if receipt["status"] == 1:
                    logger.info(
                        f"Token {token_id} revealed. TX: {tx_hash.hex()}"
                    )
                    return tx_hash.hex()
                else:
                    logger.error(
                        f"Reveal tx reverted for token {token_id}: {tx_hash.hex()}"
                    )
                    raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")

            except Exception as e:
                logger.warning(
                    f"Reveal attempt {attempt}/{MAX_RETRIES} failed for token {token_id}: {e}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise
