# NFT Generative Art with Provable Randomness

AI-generated art where the seed is committed on-chain **before** generation, making the output provably fair and tamper-proof. Buyers can verify the generation was honest by re-running the same seed.

## Live Deployment

| | Details |
|---|---|
| **Chain** | Base Sepolia Testnet (Chain ID: 84532) |
| **Contract** | `0xd6D93BFdd279236dD2815857DEeB68E0A8BE4D9c` |
| **Explorer** | [sepolia.basescan.org](https://sepolia.basescan.org/address/0xd6D93BFdd279236dD2815857DEeB68E0A8BE4D9c) |
| **Mint Price** | 0.0001 ETH |
| **Max Supply** | 1,000 |
| **Themes** | 5 (Cosmic Nebula, Abstract Geometry, Organic Flow, Crystal Formation, Ethereal Landscape) |

## Architecture

```
                                    On-Chain (Base Sepolia)
                                   ┌──────────────────────┐
  User ──► Frontend (Next.js) ──►  │  GenerativeNFT.sol   │
           localhost:3000          │  - mint()             │
                                   │  - SeedCommitted event│
                                   │  - revealToken()      │
                                   └──────────┬───────────┘
                                              │
                                   ┌──────────▼───────────┐
                                   │  Backend (Python)     │
                                   │  localhost:8000       │
                                   │                       │
                                   │  1. Listen for events │
                                   │  2. Build prompt      │
                                   │  3. Run Stable Diff.  │
                                   │  4. Upload to IPFS    │
                                   │  5. Reveal on-chain   │
                                   └──────────┬───────────┘
                                              │
                                   ┌──────────▼───────────┐
                                   │  IPFS (Pinata)        │
                                   │  - Image PNG          │
                                   │  - Metadata JSON      │
                                   └──────────────────────┘
```

### Provable Randomness Flow

1. **User mints** - calls `mint()` on the smart contract
2. **Seed committed on-chain** - contract generates `keccak256(prevrandao, timestamp, sender, tokenId)` and stores it immutably
3. **Event emitted** - `SeedCommitted(tokenId, seed, themeIndex, minter)`
4. **Backend picks up event** - chain listener detects the new mint
5. **Prompt built deterministically** - seed maps to specific colors, textures, shapes, moods via modular arithmetic
6. **Image generated** - Stable Diffusion runs with the exact seed and pinned parameters
7. **Uploaded to IPFS** - image + metadata (including SHA-256 hash) pinned via Pinata
8. **Revealed on-chain** - backend calls `revealToken(tokenId, ipfsURI)`
9. **Verification** - anyone can read the seed from the blockchain, re-run generation, and compare the image hash

## Project Structure

```
nft-generative-art/
├── contracts/                  # Solidity smart contracts (Hardhat)
│   ├── contracts/
│   │   └── GenerativeNFT.sol   # ERC-721 with commit-reveal pattern
│   ├── test/
│   │   └── GenerativeNFT.test.ts  # 25 unit tests
│   ├── scripts/
│   │   └── deploy.ts
│   └── hardhat.config.ts
│
├── backend/                    # Python generation service
│   ├── src/
│   │   ├── main.py             # Entrypoint (listener + API)
│   │   ├── config.py           # Settings from .env
│   │   ├── listener/
│   │   │   └── chain_listener.py   # Polls SeedCommitted events
│   │   ├── generator/
│   │   │   ├── prompt_builder.py   # Deterministic seed-to-prompt
│   │   │   └── stable_diffusion.py # Pinned SD generation
│   │   ├── storage/
│   │   │   └── ipfs_uploader.py    # Pinata IPFS uploads
│   │   ├── reveal/
│   │   │   └── token_revealer.py   # On-chain reveal transactions
│   │   └── api/
│   │       └── verification.py     # FastAPI verification endpoints
│   └── tests/
│       └── test_prompt_builder.py
│
├── frontend/                   # Next.js 15 + TypeScript
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Landing + gallery
│   │   │   ├── mint/page.tsx       # Mint page
│   │   │   ├── my-gallery/page.tsx # User's owned NFTs
│   │   │   ├── token/[tokenId]/page.tsx  # Token detail
│   │   │   └── verify/page.tsx     # Verification tool
│   │   ├── components/
│   │   │   ├── Gallery.tsx         # NFT grid with IPFS images
│   │   │   ├── Header.tsx          # Nav with RainbowKit
│   │   │   ├── Providers.tsx       # Wagmi + RainbowKit providers
│   │   │   ├── SeedDisplay.tsx     # Seed with copy button
│   │   │   └── NFTCard.tsx
│   │   ├── hooks/
│   │   │   ├── useGenerativeNFT.ts # Contract read/write hooks
│   │   │   └── useTokenData.ts     # Full token data + metadata
│   │   └── lib/
│   │       ├── contract.ts         # ABI + address
│   │       ├── wagmi.ts            # Wagmi config
│   │       └── ipfs.ts             # IPFS gateway helpers
│   └── abis/
│       └── GenerativeNFT.json
│
└── shared/
    └── prompts.json            # Theme templates + variation arrays
```

## Tech Stack

| Layer | Technology |
|---|---|
| **Blockchain** | Base Sepolia Testnet |
| **Smart Contract** | Solidity 0.8.27, OpenZeppelin v5, Hardhat v2 |
| **Backend** | Python 3.12, FastAPI, web3.py, diffusers (Stable Diffusion v1.5) |
| **Frontend** | Next.js 15, TypeScript, wagmi v2, viem, RainbowKit v2, Tailwind CSS |
| **Storage** | IPFS via Pinata |
| **AI Model** | Stable Diffusion v1.5 (sd-legacy/stable-diffusion-v1-5) |

## Prerequisites

- **Node.js** >= 22.10 (via nvm)
- **Python** >= 3.10
- **MetaMask** browser extension
- **Base Sepolia testnet ETH** (from faucet)

## Setup & Run

### 1. Smart Contracts

```bash
cd contracts
npm install

# Run tests (25 passing)
npx hardhat test

# Deploy to Base Sepolia (fill in .env first)
cp .env.example .env
# Edit .env with your PRIVATE_KEY
npx hardhat run scripts/deploy.ts --network baseSepolia
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install web3 fastapi uvicorn httpx python-dotenv pydantic pydantic-settings Pillow

# Install ML dependencies (for image generation)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install diffusers transformers accelerate safetensors

# Configure
cp .env.example .env
# Edit .env with:
#   CONTRACT_ADDRESS=0xYourContract
#   BACKEND_PRIVATE_KEY=0xYourKey
#   PINATA_API_KEY=your_key
#   PINATA_SECRET_KEY=your_secret

# Start verification API only
PYTHONPATH=. python3 -m uvicorn src.api.verification:app --host 0.0.0.0 --port 8000

# Or start full backend (listener + API + SD generation)
PYTHONPATH=. python3 src/main.py
```

**Note:** The first run downloads the Stable Diffusion model (~4GB). Generation takes ~90 seconds on CPU.

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps

# Configure
cp .env.local.example .env.local
# Edit .env.local with:
#   NEXT_PUBLIC_CONTRACT_ADDRESS=0xYourContract
#   NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id (or "demo")
#   NEXT_PUBLIC_VERIFICATION_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

Open **http://localhost:3000** in your browser.

### Quick Start (All Services)

```bash
# Terminal 1 - Backend API
cd backend && source .venv/bin/activate
PYTHONPATH=. python3 -m uvicorn src.api.verification:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev

# Terminal 3 - Full backend with SD (optional, for auto-generation)
cd backend && source .venv/bin/activate
PYTHONPATH=. python3 src/main.py
```

## Frontend Pages

| Route | Description |
|---|---|
| `/` | Landing page with hero, "How It Works", and gallery of all minted NFTs |
| `/mint` | Connect wallet, mint NFT, see committed seed and theme |
| `/my-gallery` | View NFTs owned by the connected wallet |
| `/token/[id]` | Token detail with full-size image, metadata, prompt, generation params, SHA-256 hash |
| `/verify` | Verification tool - enter token ID, see on-chain seed, derived prompt, re-generate for hash comparison |

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service status and SD model state |
| `/api/verify/{tokenId}` | GET | Get all generation parameters for a token from on-chain data |
| `/api/regenerate` | POST | Re-generate image from seed + theme for verification (rate limited: 5/hour) |

## Smart Contract

**GenerativeNFT.sol** - ERC-721 with commit-reveal:

| Function | Description |
|---|---|
| `mint()` | Mint NFT, generate and store seed on-chain, emit `SeedCommitted` |
| `revealToken(tokenId, ipfsURI)` | Set IPFS metadata URI (revealer only) |
| `tokenURI(tokenId)` | Returns on-chain SVG placeholder before reveal, IPFS URI after |
| `tokenSeeds(tokenId)` | Read the committed seed (public) |
| `tokenThemeIndex(tokenId)` | Read the assigned theme (public) |
| `tokenRevealed(tokenId)` | Check if artwork has been revealed (public) |
| `setMintPrice(price)` | Update mint price (owner only) |
| `setRevealer(address)` | Update backend revealer wallet (owner only) |
| `withdraw()` | Withdraw contract balance (owner only) |

## Prompt System

Seeds are deterministically mapped to prompts using `shared/prompts.json`:

- **5 themes** with template strings containing `{color}`, `{texture}`, `{shape}`, `{mood}` placeholders
- **Variation arrays** with 10-12 options each for colors, textures, shapes, moods
- Selection uses different 64-bit chunks of the 256-bit seed via modular arithmetic
- Same seed + theme always produces the exact same prompt

## Verification

Anyone can verify a token's generation was honest:

1. Read `tokenSeeds(tokenId)` and `tokenThemeIndex(tokenId)` from the contract
2. Run the prompt builder with those inputs to get the exact prompt
3. Run Stable Diffusion with the same seed, model, steps, guidance, and resolution
4. Compare the output image's SHA-256 hash with the `image_hash_sha256` in the IPFS metadata

The verification page at `/verify` automates steps 1-2 and provides a re-generation button for step 3-4.

## Generation Parameters (Pinned)

| Parameter | Value |
|---|---|
| Model | `sd-legacy/stable-diffusion-v1-5` |
| Scheduler | `EulerDiscreteScheduler` |
| Steps | 50 |
| Guidance Scale | 7.5 |
| Resolution | 512x512 |
| Precision | float32 |
| Seed | `int(on_chain_seed, 16) % 2^32` |

**Determinism note:** Stable Diffusion outputs depend on the exact GPU/CPU, CUDA version, and library versions. The image SHA-256 hash in the metadata serves as the ground truth for verification.

## Testing

```bash
# Smart contract tests (25 passing)
cd contracts && npx hardhat test

# Backend prompt builder tests
cd backend && source .venv/bin/activate
PYTHONPATH=. pytest tests/test_prompt_builder.py -v
```

## License

MIT
