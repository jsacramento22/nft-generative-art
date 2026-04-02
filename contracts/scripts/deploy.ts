import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", ethers.formatEther(balance), "MATIC");

  const NAME = "Generative Art";
  const SYMBOL = "GENART";
  const MINT_PRICE = ethers.parseEther("0.01");
  const MAX_SUPPLY = 1000;
  const THEME_COUNT = 5;

  // Use deployer as revealer initially — update to backend wallet after deploy
  const REVEALER = deployer.address;

  console.log("\nDeploying GenerativeNFT...");
  const factory = await ethers.getContractFactory("GenerativeNFT");
  const nft = await factory.deploy(
    NAME,
    SYMBOL,
    MINT_PRICE,
    MAX_SUPPLY,
    THEME_COUNT,
    REVEALER
  );

  await nft.waitForDeployment();
  const address = await nft.getAddress();

  console.log("GenerativeNFT deployed to:", address);
  console.log("\nDeployment params:");
  console.log("  Name:", NAME);
  console.log("  Symbol:", SYMBOL);
  console.log("  Mint Price:", ethers.formatEther(MINT_PRICE), "MATIC");
  console.log("  Max Supply:", MAX_SUPPLY);
  console.log("  Theme Count:", THEME_COUNT);
  console.log("  Revealer:", REVEALER);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
