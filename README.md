# TON NFT Transfer Tool

A Python script that allows scanning TON wallets for NFTs and transferring them to a specified address.

## Features

- Find wallet address from a seed phrase
- Retrieve all NFTs from a TON wallet
- Display detailed NFT information (name, description, attributes, images)
- Transfer NFTs to a specified address
- Support for different wallet types (v3r1, v3r2, v4r1, v4r2)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/knyazev741/NFT-Transfer.git
cd NFT-Transfer
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example` with your API keys and target address:
```bash
cp .env.example .env
```

4. Edit the `.env` file and fill in your API keys:
- `API_KEY`: Your TonCenter API key
- `TONAPI_KEY`: Your TonAPI key
- `TARGET_ADDRESS`: The wallet address to transfer NFTs to

## Usage

Run the script with a TON wallet seed phrase:

```bash
python ton_transfer.py "your seed phrase here"
```

The script will:
1. Find the wallet address associated with the seed phrase
2. Retrieve and display all NFTs in the wallet
3. Transfer the first NFT to the target address specified in the `.env` file

## Requirements

- Python 3.6+
- tonsdk
- python-dotenv
- requests

## License

MIT 