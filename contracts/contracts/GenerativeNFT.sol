// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Base64.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract GenerativeNFT is ERC721, Ownable, ReentrancyGuard {
    using Strings for uint256;
    using Strings for bytes32;

    // --- State ---
    uint256 public mintPrice;
    uint256 public maxSupply;
    uint8 public themeCount;
    address public revealer;
    uint256 private _nextTokenId;

    mapping(uint256 => bytes32) public tokenSeeds;
    mapping(uint256 => uint8) public tokenThemeIndex;
    mapping(uint256 => bool) public tokenRevealed;
    mapping(uint256 => string) public tokenIPFSURIs;

    // --- Events ---
    event SeedCommitted(
        uint256 indexed tokenId,
        bytes32 seed,
        uint8 themeIndex,
        address indexed minter
    );
    event TokenRevealed(uint256 indexed tokenId, string ipfsURI);
    event RevealerUpdated(address indexed oldRevealer, address indexed newRevealer);

    // --- Errors ---
    error InsufficientPayment();
    error MaxSupplyReached();
    error OnlyRevealer();
    error AlreadyRevealed();
    error TokenDoesNotExist();
    error NoThemes();
    error ZeroAddress();
    error WithdrawFailed();

    // --- Modifiers ---
    modifier onlyRevealer() {
        if (msg.sender != revealer) revert OnlyRevealer();
        _;
    }

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 mintPrice_,
        uint256 maxSupply_,
        uint8 themeCount_,
        address revealer_
    ) ERC721(name_, symbol_) Ownable(msg.sender) {
        if (themeCount_ == 0) revert NoThemes();
        if (revealer_ == address(0)) revert ZeroAddress();

        mintPrice = mintPrice_;
        maxSupply = maxSupply_;
        themeCount = themeCount_;
        revealer = revealer_;
    }

    function mint() external payable nonReentrant returns (uint256) {
        if (msg.value < mintPrice) revert InsufficientPayment();
        if (_nextTokenId >= maxSupply) revert MaxSupplyReached();

        uint256 tokenId = _nextTokenId++;

        bytes32 seed = keccak256(
            abi.encodePacked(
                block.prevrandao,
                block.timestamp,
                msg.sender,
                tokenId
            )
        );

        uint8 themeIndex = uint8(uint256(seed) % themeCount);

        tokenSeeds[tokenId] = seed;
        tokenThemeIndex[tokenId] = themeIndex;

        _safeMint(msg.sender, tokenId);

        emit SeedCommitted(tokenId, seed, themeIndex, msg.sender);

        return tokenId;
    }

    function revealToken(
        uint256 tokenId,
        string calldata ipfsURI
    ) external onlyRevealer {
        if (_ownerOf(tokenId) == address(0)) revert TokenDoesNotExist();
        if (tokenRevealed[tokenId]) revert AlreadyRevealed();

        tokenIPFSURIs[tokenId] = ipfsURI;
        tokenRevealed[tokenId] = true;

        emit TokenRevealed(tokenId, ipfsURI);
    }

    function tokenURI(
        uint256 tokenId
    ) public view override returns (string memory) {
        if (_ownerOf(tokenId) == address(0)) revert TokenDoesNotExist();

        if (tokenRevealed[tokenId]) {
            return tokenIPFSURIs[tokenId];
        }

        // Return on-chain placeholder for unrevealed tokens
        bytes32 seed = tokenSeeds[tokenId];
        string memory json = string(
            abi.encodePacked(
                '{"name":"Generative Art #',
                tokenId.toString(),
                '","description":"Art is being generated. Seed: ',
                _toHexString(seed),
                '","image":"data:image/svg+xml;base64,',
                Base64.encode(_placeholderSVG(tokenId, seed)),
                '","attributes":[{"trait_type":"Status","value":"Generating"},{"trait_type":"Seed","value":"',
                _toHexString(seed),
                '"},{"trait_type":"Theme Index","value":"',
                uint256(tokenThemeIndex[tokenId]).toString(),
                '"}]}'
            )
        );

        return string(
            abi.encodePacked(
                "data:application/json;base64,",
                Base64.encode(bytes(json))
            )
        );
    }

    // --- Owner functions ---

    function setRevealer(address newRevealer) external onlyOwner {
        if (newRevealer == address(0)) revert ZeroAddress();
        address old = revealer;
        revealer = newRevealer;
        emit RevealerUpdated(old, newRevealer);
    }

    function setMintPrice(uint256 newPrice) external onlyOwner {
        mintPrice = newPrice;
    }

    function setThemeCount(uint8 newCount) external onlyOwner {
        if (newCount == 0) revert NoThemes();
        themeCount = newCount;
    }

    function withdraw() external onlyOwner {
        (bool success, ) = payable(owner()).call{value: address(this).balance}(
            ""
        );
        if (!success) revert WithdrawFailed();
    }

    // --- View helpers ---

    function totalMinted() external view returns (uint256) {
        return _nextTokenId;
    }

    // --- Internal helpers ---

    function _placeholderSVG(
        uint256 tokenId,
        bytes32 seed
    ) internal pure returns (bytes memory) {
        // Generate a simple SVG with the seed-derived color
        uint8 r = uint8(uint256(seed) >> 16);
        uint8 g = uint8(uint256(seed) >> 8);
        uint8 b = uint8(uint256(seed));

        return
            abi.encodePacked(
                '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512">',
                '<rect width="512" height="512" fill="rgb(',
                uint256(r).toString(),
                ",",
                uint256(g).toString(),
                ",",
                uint256(b).toString(),
                ')"/>',
                '<text x="256" y="230" font-family="monospace" font-size="20" fill="white" text-anchor="middle">Generating...</text>',
                '<text x="256" y="270" font-family="monospace" font-size="14" fill="white" text-anchor="middle">#',
                tokenId.toString(),
                "</text>",
                "</svg>"
            );
    }

    function _toHexString(bytes32 value) internal pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(66);
        str[0] = "0";
        str[1] = "x";
        for (uint256 i = 0; i < 32; i++) {
            str[2 + i * 2] = alphabet[uint8(value[i] >> 4)];
            str[3 + i * 2] = alphabet[uint8(value[i] & 0x0f)];
        }
        return string(str);
    }
}
