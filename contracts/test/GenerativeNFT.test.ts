import { expect } from "chai";
import { ethers } from "hardhat";
import { GenerativeNFT } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("GenerativeNFT", function () {
  let nft: GenerativeNFT;
  let owner: SignerWithAddress;
  let revealer: SignerWithAddress;
  let minter: SignerWithAddress;
  let other: SignerWithAddress;

  const NAME = "Generative Art";
  const SYMBOL = "GENART";
  const MINT_PRICE = ethers.parseEther("0.01");
  const MAX_SUPPLY = 100;
  const THEME_COUNT = 5;

  beforeEach(async function () {
    [owner, revealer, minter, other] = await ethers.getSigners();

    const factory = await ethers.getContractFactory("GenerativeNFT");
    nft = await factory.deploy(
      NAME,
      SYMBOL,
      MINT_PRICE,
      MAX_SUPPLY,
      THEME_COUNT,
      revealer.address
    );
    await nft.waitForDeployment();
  });

  describe("Deployment", function () {
    it("should set correct initial values", async function () {
      expect(await nft.name()).to.equal(NAME);
      expect(await nft.symbol()).to.equal(SYMBOL);
      expect(await nft.mintPrice()).to.equal(MINT_PRICE);
      expect(await nft.maxSupply()).to.equal(MAX_SUPPLY);
      expect(await nft.themeCount()).to.equal(THEME_COUNT);
      expect(await nft.revealer()).to.equal(revealer.address);
      expect(await nft.owner()).to.equal(owner.address);
    });

    it("should revert with zero theme count", async function () {
      const factory = await ethers.getContractFactory("GenerativeNFT");
      await expect(
        factory.deploy(NAME, SYMBOL, MINT_PRICE, MAX_SUPPLY, 0, revealer.address)
      ).to.be.revertedWithCustomError(nft, "NoThemes");
    });

    it("should revert with zero revealer address", async function () {
      const factory = await ethers.getContractFactory("GenerativeNFT");
      await expect(
        factory.deploy(
          NAME,
          SYMBOL,
          MINT_PRICE,
          MAX_SUPPLY,
          THEME_COUNT,
          ethers.ZeroAddress
        )
      ).to.be.revertedWithCustomError(nft, "ZeroAddress");
    });
  });

  describe("Minting", function () {
    it("should mint and assign token to caller", async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
      expect(await nft.ownerOf(0)).to.equal(minter.address);
      expect(await nft.totalMinted()).to.equal(1);
    });

    it("should store seed and theme index", async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
      const seed = await nft.tokenSeeds(0);
      const themeIndex = await nft.tokenThemeIndex(0);

      expect(seed).to.not.equal(ethers.ZeroHash);
      expect(themeIndex).to.be.lessThan(THEME_COUNT);
    });

    it("should emit SeedCommitted event with correct params", async function () {
      const tx = await nft.connect(minter).mint({ value: MINT_PRICE });
      const receipt = await tx.wait();

      const event = receipt?.logs.find((log) => {
        try {
          return nft.interface.parseLog({ topics: log.topics as string[], data: log.data })?.name === "SeedCommitted";
        } catch {
          return false;
        }
      });

      expect(event).to.not.be.undefined;

      const parsed = nft.interface.parseLog({
        topics: event!.topics as string[],
        data: event!.data,
      });

      expect(parsed?.args.tokenId).to.equal(0);
      expect(parsed?.args.minter).to.equal(minter.address);
      expect(parsed?.args.seed).to.not.equal(ethers.ZeroHash);
      expect(parsed?.args.themeIndex).to.be.lessThan(THEME_COUNT);
    });

    it("should increment token IDs", async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
      await nft.connect(minter).mint({ value: MINT_PRICE });

      expect(await nft.ownerOf(0)).to.equal(minter.address);
      expect(await nft.ownerOf(1)).to.equal(minter.address);
      expect(await nft.totalMinted()).to.equal(2);
    });

    it("should revert on insufficient payment", async function () {
      await expect(
        nft.connect(minter).mint({ value: ethers.parseEther("0.001") })
      ).to.be.revertedWithCustomError(nft, "InsufficientPayment");
    });

    it("should revert when max supply reached", async function () {
      // Deploy with max supply of 2
      const factory = await ethers.getContractFactory("GenerativeNFT");
      const smallNft = await factory.deploy(
        NAME,
        SYMBOL,
        MINT_PRICE,
        2,
        THEME_COUNT,
        revealer.address
      );

      await smallNft.connect(minter).mint({ value: MINT_PRICE });
      await smallNft.connect(minter).mint({ value: MINT_PRICE });

      await expect(
        smallNft.connect(minter).mint({ value: MINT_PRICE })
      ).to.be.revertedWithCustomError(smallNft, "MaxSupplyReached");
    });

    it("should produce different seeds for different minters", async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
      await nft.connect(other).mint({ value: MINT_PRICE });

      const seed0 = await nft.tokenSeeds(0);
      const seed1 = await nft.tokenSeeds(1);

      expect(seed0).to.not.equal(seed1);
    });
  });

  describe("Reveal", function () {
    const IPFS_URI = "ipfs://QmTestMetadataCID123";

    beforeEach(async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
    });

    it("should reveal token with IPFS URI", async function () {
      await nft.connect(revealer).revealToken(0, IPFS_URI);

      expect(await nft.tokenRevealed(0)).to.be.true;
      expect(await nft.tokenIPFSURIs(0)).to.equal(IPFS_URI);
    });

    it("should emit TokenRevealed event", async function () {
      await expect(nft.connect(revealer).revealToken(0, IPFS_URI))
        .to.emit(nft, "TokenRevealed")
        .withArgs(0, IPFS_URI);
    });

    it("should revert if caller is not revealer", async function () {
      await expect(
        nft.connect(other).revealToken(0, IPFS_URI)
      ).to.be.revertedWithCustomError(nft, "OnlyRevealer");
    });

    it("should revert if token already revealed", async function () {
      await nft.connect(revealer).revealToken(0, IPFS_URI);
      await expect(
        nft.connect(revealer).revealToken(0, "ipfs://QmDifferent")
      ).to.be.revertedWithCustomError(nft, "AlreadyRevealed");
    });

    it("should revert for non-existent token", async function () {
      await expect(
        nft.connect(revealer).revealToken(999, IPFS_URI)
      ).to.be.revertedWithCustomError(nft, "TokenDoesNotExist");
    });
  });

  describe("tokenURI", function () {
    beforeEach(async function () {
      await nft.connect(minter).mint({ value: MINT_PRICE });
    });

    it("should return placeholder for unrevealed token", async function () {
      const uri = await nft.tokenURI(0);
      expect(uri).to.contain("data:application/json;base64,");

      // Decode and check
      const json = Buffer.from(
        uri.replace("data:application/json;base64,", ""),
        "base64"
      ).toString();
      const metadata = JSON.parse(json);

      expect(metadata.name).to.equal("Generative Art #0");
      expect(metadata.description).to.contain("Seed:");
      expect(metadata.image).to.contain("data:image/svg+xml;base64,");
      expect(metadata.attributes).to.have.length(3);
      expect(metadata.attributes[0].value).to.equal("Generating");
    });

    it("should return IPFS URI for revealed token", async function () {
      const ipfsURI = "ipfs://QmTestCID";
      await nft.connect(revealer).revealToken(0, ipfsURI);

      expect(await nft.tokenURI(0)).to.equal(ipfsURI);
    });

    it("should revert for non-existent token", async function () {
      await expect(nft.tokenURI(999)).to.be.revertedWithCustomError(
        nft,
        "TokenDoesNotExist"
      );
    });
  });

  describe("Owner functions", function () {
    it("should allow owner to update revealer", async function () {
      await expect(nft.connect(owner).setRevealer(other.address))
        .to.emit(nft, "RevealerUpdated")
        .withArgs(revealer.address, other.address);

      expect(await nft.revealer()).to.equal(other.address);
    });

    it("should revert setting zero address revealer", async function () {
      await expect(
        nft.connect(owner).setRevealer(ethers.ZeroAddress)
      ).to.be.revertedWithCustomError(nft, "ZeroAddress");
    });

    it("should allow owner to update mint price", async function () {
      const newPrice = ethers.parseEther("0.05");
      await nft.connect(owner).setMintPrice(newPrice);
      expect(await nft.mintPrice()).to.equal(newPrice);
    });

    it("should allow owner to update theme count", async function () {
      await nft.connect(owner).setThemeCount(10);
      expect(await nft.themeCount()).to.equal(10);
    });

    it("should revert setting zero theme count", async function () {
      await expect(
        nft.connect(owner).setThemeCount(0)
      ).to.be.revertedWithCustomError(nft, "NoThemes");
    });

    it("should allow owner to withdraw", async function () {
      // Mint a token to put ETH in the contract
      await nft.connect(minter).mint({ value: MINT_PRICE });

      const balanceBefore = await ethers.provider.getBalance(owner.address);
      const tx = await nft.connect(owner).withdraw();
      const receipt = await tx.wait();
      const gasCost = receipt!.gasUsed * receipt!.gasPrice;
      const balanceAfter = await ethers.provider.getBalance(owner.address);

      expect(balanceAfter + gasCost - balanceBefore).to.equal(MINT_PRICE);
    });

    it("should revert non-owner calls", async function () {
      await expect(
        nft.connect(other).setRevealer(other.address)
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");

      await expect(
        nft.connect(other).setMintPrice(0)
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");

      await expect(
        nft.connect(other).withdraw()
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");
    });
  });
});
