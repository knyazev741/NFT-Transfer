# TON NFT Transfer Tool

A Python script that allows scanning TON wallets for NFTs and transferring them to a specified address.

## Features

- Find wallet address from a seed phrase
- Retrieve all NFTs from a TON wallet
- Display detailed NFT information (name, description, attributes, images)
- Transfer NFTs to a specified address
- Support for different wallet types (v3r1, v3r2, v4r1, v4r2)
- Process multiple seed phrases sequentially

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
- `SEED_1`, `SEED_2`, etc.: Your seed phrases (for batch processing)

## Usage

### Method 1: Process a single wallet using command-line argument

Run the script with a TON wallet seed phrase:

```bash
python ton_transfer.py "your seed phrase here"
```

### Method 2: Process multiple wallets using .env file

1. Add multiple seed phrases to your .env file in the format:
```
SEED_1=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
SEED_2=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
SEED_3=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12
```

2. Run the script without arguments to process all seed phrases:
```bash
python ton_transfer.py
```

The script will process each seed phrase sequentially and:
1. Find the wallet address associated with each seed phrase
2. Retrieve and display all NFTs in the wallet
3. Transfer all NFTs to the target address specified in the `.env` file
4. Transfer remaining TON balance after all NFTs are processed

## Requirements

- Python 3.6+
- tonsdk
- python-dotenv
- requests

## License

MIT 