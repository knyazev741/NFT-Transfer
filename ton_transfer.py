#!/usr/bin/env python3
import sys
import os
import re
import asyncio
import aiohttp
import traceback
from dotenv import load_dotenv
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV5R1
from tonutils.nft import NFTStandard
from tonutils.utils import Address, Cell, begin_cell
from tonutils.wallet.data import TransferNFTData
from base64 import b64encode, urlsafe_b64encode
from typing import Optional, List, Dict

# Load environment variables from .env file
load_dotenv()

# Constants from environment variables
TONAPI_KEY = os.getenv("TONAPI_KEY")
TARGET_ADDRESS = os.getenv("TARGET_ADDRESS")

def to_nano(amount):
    """Convert TON to nanoTON"""
    return int(amount * 1e9)

def hex_to_b64(hex_str):
    """Convert hex string to base64"""
    # Remove 0: prefix if present
    if hex_str.startswith("0:"):
        hex_str = hex_str[2:]
    # Convert hex to bytes then to base64
    return b64encode(bytes.fromhex(hex_str)).decode()

def convert_address(address_str: str, bounceable: bool = True) -> str:
    """Convert any TON address format to user-friendly format (EQ/UQ)"""
    try:
        print(f"\nConverting address: {address_str}")
        print(f"Bounceable: {bounceable}")
        
        # If already in user-friendly format, return as is
        if address_str.startswith('EQ') or address_str.startswith('UQ'):
            print("Address is already in user-friendly format")
            return address_str
            
        # Handle raw format (0:hex)
        if address_str.startswith('0:'):
            wc = 0
            hash_part = address_str[2:]  # Remove '0:' prefix
            print(f"Raw address detected, workchain: {wc}, hash: {hash_part}")
        else:
            # Assume it's just hex
            wc = 0
            hash_part = address_str
            print(f"Hex address detected, workchain: {wc}, hash: {hash_part}")
            
        # Create address from workchain and hash
        addr = Address(f"{wc}:{hash_part}")
        print(f"Created Address object: {addr}")
        
        # Convert to user-friendly format with all parameters
        result = addr.to_str(
            is_user_friendly=True,
            is_url_safe=True,
            is_bounceable=bounceable,
            is_test_only=False
        )
        print(f"Converted to user-friendly format: {result}")
        return result
        
    except Exception as e:
        print(f"Error converting address {address_str}: {e}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return address_str

async def get_nft_items(client, address):
    """Get all NFTs owned by an address using TonAPI"""
    addr_str = str(address).replace("Address<", "").replace(">", "")
    url = f"https://tonapi.io/v2/accounts/{addr_str}/nfts"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("nft_items", [])
                else:
                    print(f"Error getting NFTs: {response.status} - {await response.text()}")
                    return []
    except Exception as e:
        print(f"Error getting NFTs: {str(e)}")
        return []

async def transfer_nft(wallet: WalletV5R1, nft_address: str, nft_name: str, target_address: str, retry_count: int = 0) -> bool:
    try:
        print(f"\nPreparing NFT transfer (attempt {retry_count + 1}/3):")
        print(f"NFT address: {nft_address}")
        print(f"NFT name: {nft_name}")

        # Create transfer data using minimal required parameters as per library example
        transfer_data = TransferNFTData(
            destination=target_address,
            nft_address=nft_address
        )

        print("\nSending transfer...")

        # Send as a single-item batch as per library example
        tx_hash = await wallet.batch_nft_transfer(
            data_list=[transfer_data]
        )

        print(f"✅ Successfully sent NFT transfer: {tx_hash}")
        await asyncio.sleep(5)  # Wait between transfers
        return True

    except Exception as e:
        print(f"❌ Error sending NFT transfer: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")

        if "rate limit" in str(e).lower():
            print("\nHit rate limit. Waiting 60 seconds before retrying...")
            await asyncio.sleep(60)
        elif retry_count < 2:
            print(f"Retrying in 3 seconds... (attempt {retry_count + 2}/3)")
            await asyncio.sleep(3)
            return await transfer_nft(wallet, nft_address, nft_name, target_address, retry_count + 1)
        return False

async def send_ton(wallet, amount_ton: float) -> bool:
    """Send TON to the target address"""
    print(f"\n=== SENDING {amount_ton} TON ===")
    
    try:
        # Convert amount to nano
        amount_nano = to_nano(amount_ton)
        print(f"Amount to send: {amount_ton} TON ({amount_nano} nano)")
        
        # Get current balance
        balance = await wallet.balance()
        if balance < amount_nano:
            print(f"❌ Insufficient balance: {balance/1e9:.9f} TON < {amount_ton} TON")
            return False
        
        # Send transfer transaction
        target = Address(TARGET_ADDRESS)
        tx_hash = await wallet.transfer(
            destination=target,
            amount=amount_ton
        )
        
        print("\n✅ TON transfer transaction sent successfully!")
        print(f"Transaction hash: {tx_hash}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error sending TON transfer: {str(e)}")
        return False

async def process_single_seed_phrase(seed_phrase: str) -> None:
    print("\n=== FINDING WALLET WITH BALANCE ===")
    print(f"Seed phrase contains {len(seed_phrase.split())} words.")
    print(f"Seed phrase (first 3 words): {' '.join(seed_phrase.split()[:3])}...")

    # Initialize TonAPI client
    print("Initializing TonAPI client...")
    client = TonapiClient(api_key=TONAPI_KEY, is_testnet=False)

    try:
        # Create V5 wallet from seed phrase
        print("Creating V5 wallet from mnemonic...")
        wallet, pub, priv, _ = WalletV5R1.from_mnemonic(client, seed_phrase.split())
        addr_str = str(wallet.address)
        print(f"Generated address: {addr_str}")

        while True:
            # Check balance
            print("\nChecking balance...")
            balance = await wallet.balance()
            print(f"Balance: {balance/1e9:.9f} TON")

            # Get NFTs
            print("Checking for NFTs...")
            nfts = await get_nft_items(client, addr_str)
            nft_count = len(nfts)
            print(f"Found {nft_count} NFTs")

            if nft_count == 0:
                print("\nNo NFTs remaining. Sending all TON to target address...")
                # Leave 0.1 TON for fees
                amount_to_send = (balance / 1e9) - 0.1
                if amount_to_send > 0:
                    success = await send_ton(wallet, amount_to_send)
                    if success:
                        print("✅ Successfully sent remaining TON")
                    else:
                        print("❌ Failed to send remaining TON")
                else:
                    print("Insufficient balance to send TON (need to leave 0.1 TON for fees)")
                break

            print(f"\n=== TRANSFER SUMMARY ===")
            print(f"From: {addr_str}")
            print(f"To: {TARGET_ADDRESS}")
            print(f"Current balance: {balance / 1e9} TON")

            # Transfer NFTs one by one
            print("\n=== TRANSFERRING NFTs ===")
            success_count = 0
            failed_nfts = []

            for i, nft in enumerate(nfts, 1):
                print(f"\n=== TRANSFERRING NFT {i}/{nft_count} ===")
                print(f"NFT: {nft.get('metadata', {}).get('name', f'NFT #{i}')}")
                print(f"Address: {nft.get('address', '')}")

                success = await transfer_nft(
                    wallet=wallet,
                    nft_address=nft.get('address', ''),
                    nft_name=nft.get('metadata', {}).get('name', f'NFT #{i}'),
                    target_address=TARGET_ADDRESS
                )
                
                if success:
                    success_count += 1
                else:
                    failed_nfts.append(nft)

            # Print summary
            print("\n=== NFT TRANSFER SUMMARY ===")
            print(f"Successfully transferred: {success_count}/{nft_count} NFTs")
            print(f"Failed transfers: {len(failed_nfts)}")

            # Wait a bit before checking again
            print("\nWaiting 10 seconds before checking for remaining NFTs...")
            await asyncio.sleep(10)

    except Exception as e:
        print(f"Error processing wallet: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")

def get_seed_phrases():
    """Extract all seed phrases from .env file"""
    seed_phrases = []
    seed_pattern = re.compile(r'^SEED_\d+$')
    
    for key, value in os.environ.items():
        if seed_pattern.match(key) and value.strip():
            seed_phrases.append((key, value.strip()))
    
    # Sort by seed number
    seed_phrases.sort(key=lambda x: int(x[0].split('_')[1]))
    return seed_phrases

async def main():
    print("=== TON NFT SCANNER AND TRANSFER ===")
    
    # Get all seed phrases from .env
    seed_phrases = get_seed_phrases()
    
    if not seed_phrases:
        print("No seed phrases found in .env file.")
        print("Please add seed phrases with format SEED_1, SEED_2, etc.")
        return
    
    print(f"Found {len(seed_phrases)} seed phrase(s) in .env file.")
    
    # Process each seed phrase sequentially
    for seed_idx, (seed_key, seed_phrase) in enumerate(seed_phrases):
        print(f"\n====== PROCESSING {seed_key} ({seed_idx+1}/{len(seed_phrases)}) ======")
        await process_single_seed_phrase(seed_phrase)
    
    print("\n===== ALL SEED PHRASES PROCESSED =====")
    print(f"Processed {len(seed_phrases)} seed phrases.")

if __name__ == "__main__":
    # Install required packages
    import subprocess
    
    # Check if required packages are installed, if not install them
    required_packages = ["tonutils", "python-dotenv"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"Installing required package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Run the main function
    asyncio.run(main()) 