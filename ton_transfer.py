#!/usr/bin/env python3
import sys
import requests
import base64
import os
from dotenv import load_dotenv
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.contract.token import nft
from tonsdk.utils import Address
import time

# Load environment variables from .env file
load_dotenv()

# Constants from environment variables
API_KEY = os.getenv("API_KEY")
TONAPI_KEY = os.getenv("TONAPI_KEY")
TARGET_ADDRESS = os.getenv("TARGET_ADDRESS")

def to_nano(amount):
    """Convert TON to nanoTON"""
    return int(amount * 1e9)

def check_balance(address):
    """Check balance of an address using TonCenter API"""
    wallet_info_url = f"https://toncenter.com/api/v2/getAddressBalance?address={address}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.get(wallet_info_url, headers=headers)
        if response.status_code == 200:
            balance = int(response.json().get("result", "0"))
            return balance
        return 0
    except Exception:
        return 0

def get_seqno(address):
    """Get the current seqno of an address using TonCenter API"""
    get_method_url = f"https://toncenter.com/api/v2/runGetMethod"
    headers = {"X-API-Key": API_KEY}
    payload = {
        "address": address,
        "method": "seqno",
        "stack": []
    }
    
    try:
        response = requests.post(get_method_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json().get("result", {})
            if result.get("exit_code") == 0 and "stack" in result:
                # Parse the stack (first element)
                seqno = int(result["stack"][0][1], 16)
                return seqno
        return 0  # Default to 0 if can't get seqno (new wallet or error)
    except Exception as e:
        print(f"Error getting seqno: {str(e)}")
        return 0

def get_nfts_from_address(address):
    """Get all NFTs owned by an address using TonAPI"""
    nft_url = f"https://tonapi.io/v2/accounts/{address}/nfts?limit=1000"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        # Try the newer API authentication format
        response = requests.get(nft_url, headers=headers)
        if response.status_code == 401:
            # If that fails, try without the Bearer prefix
            headers = {"X-API-Key": TONAPI_KEY}
            response = requests.get(nft_url, headers=headers)
            
        # Or try with just the api_key parameter
        if response.status_code == 401:
            nft_url = f"https://tonapi.io/v2/accounts/{address}/nfts?limit=1000&api_key={TONAPI_KEY}"
            response = requests.get(nft_url)
            
        # Try toncenter API as fallback
        if response.status_code != 200:
            print(f"Trying alternative API endpoint...")
            nft_url = f"https://toncenter.com/api/v2/getAccountNftData?address={address}"
            headers = {"X-API-Key": API_KEY}
            response = requests.get(nft_url, headers=headers)
            
        if response.status_code == 200:
            data = response.json()
            # Handle different API response formats
            if "nft_items" in data:
                nft_items = data.get("nft_items", [])
            elif "result" in data:
                nft_items = data.get("result", {}).get("items", [])
            else:
                nft_items = []
            return nft_items
        else:
            print(f"Error retrieving NFTs: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error retrieving NFTs: {str(e)}")
        return []

def find_wallet_with_balance(seed_phrase):
    """Find wallet address with balance from the given seed phrase"""
    print("\n=== FINDING WALLET WITH BALANCE ===")
    
    # Split the seed phrase
    mnemonics = seed_phrase.split()
    print(f"Seed phrase contains {len(mnemonics)} words.")
    print(f"Seed phrase (first 3 words): {' '.join(mnemonics[:3])}...")
    
    try:
        # Convert mnemonic to keypair
        keypair = mnemonic_to_wallet_key(mnemonics)
        public_key = keypair[0].hex()
        print(f"Public key from seed: {public_key}")
        
        # Try different wallet versions
        wallet_versions = [
            (WalletVersionEnum.v3r1, "v3r1"),
            (WalletVersionEnum.v3r2, "v3r2"),
            (WalletVersionEnum.v4r1, "v4r1"),
            (WalletVersionEnum.v4r2, "v4r2")
        ]
        
        # Try workchains 0 and -1
        workchains = [0, -1]
        
        # Common subwallet IDs to try
        wallet_ids = [0, 1, 698983191, 4085333890]
        
        wallets_with_balance = []
        
        # Check V3 wallets (no wallet_id)
        for workchain in workchains:
            for version, version_name in wallet_versions:
                if version_name.startswith("v3"):
                    try:
                        mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                            mnemonics=mnemonics,
                            version=version,
                            workchain=workchain
                        )
                        addr = wallet.address.to_string(True, True, True)
                        
                        # Check balance
                        balance = check_balance(addr)
                        if balance > 0:
                            print(f"✅ Found wallet with balance: {version_name} (wc={workchain})")
                            print(f"  Address: {addr}")
                            print(f"  Balance: {balance/1e9:.9f} TON")
                            wallets_with_balance.append({
                                'version': version,
                                'workchain': workchain,
                                'wallet_id': None,
                                'address': addr,
                                'balance': balance,
                                'desc': f"{version_name} (wc={workchain})"
                            })
                    except Exception as e:
                        pass
        
        # Check V4 wallets (with wallet_id)
        for workchain in workchains:
            for version, version_name in wallet_versions:
                if version_name.startswith("v4"):
                    for wallet_id in wallet_ids:
                        try:
                            mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                                mnemonics=mnemonics,
                                version=version,
                                workchain=workchain,
                                wallet_id=wallet_id
                            )
                            addr = wallet.address.to_string(True, True, True)
                            
                            # Check balance
                            balance = check_balance(addr)
                            if balance > 0:
                                print(f"✅ Found wallet with balance: {version_name} (wc={workchain}, id={wallet_id})")
                                print(f"  Address: {addr}")
                                print(f"  Balance: {balance/1e9:.9f} TON")
                                wallets_with_balance.append({
                                    'version': version,
                                    'workchain': workchain,
                                    'wallet_id': wallet_id,
                                    'address': addr,
                                    'balance': balance,
                                    'desc': f"{version_name} (wc={workchain}, id={wallet_id})"
                                })
                        except Exception as e:
                            pass
        
        if wallets_with_balance:
            # Return the wallet with the highest balance
            return sorted(wallets_with_balance, key=lambda x: x['balance'], reverse=True)[0]
        else:
            print("❌ No wallet with balance found for this seed phrase.")
            return None
            
    except Exception as e:
        print(f"Error processing seed phrase: {str(e)}")
        return None

def transfer_nft(wallet_config, seed_phrase, nft_address, nft_name=""):
    """Transfer an NFT to the target address"""
    print(f"\n=== TRANSFERRING NFT: {nft_name} ===")
    
    try:
        # Unpack wallet configuration
        version = wallet_config['version']
        workchain = wallet_config['workchain']
        wallet_id = wallet_config['wallet_id']
        address = wallet_config['address']
        desc = wallet_config['desc']
        balance = wallet_config['balance']
        
        # Check if the wallet has enough balance for gas
        if balance < to_nano(0.05):
            print(f"❌ Insufficient balance for gas: {balance/1e9:.9f} TON < 0.05 TON")
            return False
        
        # Get mnemonics from the seed phrase
        mnemonics = seed_phrase.split()
        
        # Initialize wallet with the correct version and parameters
        _, _, _, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=version,
            workchain=workchain,
            wallet_id=wallet_id
        )
        
        # Verify the wallet address matches what we found
        generated_address = wallet.address.to_string(True, True, True)
        if generated_address != address:
            print(f"❌ ERROR: Generated address {generated_address} doesn't match expected address {address}")
            return False
        
        # Get current seqno
        seqno = get_seqno(address)
        print(f"Current seqno: {seqno}")
        
        # Create NFT transfer body - standard TON NFT transfer message with opcode 0x5fcc3d14
        nft_contract = nft.NFTItem()
        target_addr = Address(TARGET_ADDRESS)
        owner_addr = Address(address)  # Current owner (for response_destination)
        
        # Create the transfer body with parameters:
        # - new_owner: TARGET_ADDRESS
        # - response_destination: wallet address (to receive notifications)
        # - custom_payload: None (no additional data)
        transfer_body = nft_contract.create_transfer_body(
            new_owner_address=target_addr
        )
        
        # Amount to attach to the NFT transfer (standard is ~0.05 TON)
        amount_nano = to_nano(0.05)
        
        # Create transfer message from wallet to NFT contract
        message = wallet.create_transfer_message(
            to_addr=nft_address,  # NFT smart contract address
            amount=amount_nano,   # 0.05 TON for transfer
            seqno=seqno,
            payload=transfer_body,
            send_mode=3           # Standard send mode
        )
        
        # Sign and serialize the message
        signed_message = message["message"].to_boc(False)
        boc_b64 = base64.b64encode(signed_message).decode('utf-8')
        
        # Send the transaction using TonCenter API
        send_tx_url = "https://toncenter.com/api/v2/sendBoc"
        headers = {"X-API-Key": API_KEY}
        payload = {"boc": boc_b64}
        
        print(f"Sending NFT transfer transaction...")
        print(f"From: {address} ({desc})")
        print(f"NFT: {nft_address} ({nft_name})")
        print(f"To: {TARGET_ADDRESS}")
        
        response = requests.post(send_tx_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok") == True:
                print(f"\n✅ NFT transfer transaction sent successfully!")
                return True
            else:
                print(f"\n❌ Failed to send NFT transfer: {result}")
                return False
        else:
            print(f"\n❌ Failed to send NFT transfer: {response.text}")
            return False
    except Exception as e:
        print(f"\n❌ Error sending NFT transfer: {str(e)}")
        return False

def main():
    print("=== TON NFT SCANNER AND TRANSFER ===")
    
    # Check if seed phrase is provided as command-line argument
    if len(sys.argv) < 2:
        print("Usage: python ton_transfer.py \"SEED PHRASE\"")
        return
    
    # Get seed phrase from command-line argument and strip quotes if present
    seed_phrase = sys.argv[1].strip('"\'')
    
    # Find wallet with balance
    wallet = find_wallet_with_balance(seed_phrase)
    
    if wallet:
        # Process until wallet is empty of NFTs and TON
        while True:
            # Get NFTs from the found wallet address
            wallet_address = wallet['address']
            print(f"\n=== RETRIEVING NFTs FROM {wallet_address} ===")
            nft_items = get_nfts_from_address(wallet_address)
            
            # Update wallet balance
            current_balance = check_balance(wallet_address)
            wallet['balance'] = current_balance
            
            if not nft_items:
                print(f"No NFTs found on address {wallet_address}")
                
                # Send remaining TON balance if sufficient
                if current_balance > to_nano(0.05):  # Ensure there's enough for gas
                    print(f"\n=== TRANSFERRING REMAINING TON ===")
                    print(f"Current balance: {current_balance/1e9:.9f} TON")
                    print(f"Target: {TARGET_ADDRESS}")
                    
                    # Reserve a small amount for gas
                    transfer_amount = current_balance - to_nano(0.01)
                    success = send_ton(wallet, seed_phrase, transfer_amount/1e9)
                    
                    if success:
                        print(f"\n✅ TON transfer completed successfully!")
                    else:
                        print(f"\n❌ TON transfer failed.")
                else:
                    print(f"Insufficient TON balance for transfer: {current_balance/1e9:.9f} TON")
                
                # Check if wallet is now empty
                remaining_balance = check_balance(wallet_address)
                if remaining_balance < to_nano(0.01) and not nft_items:
                    print(f"\n✅ Wallet emptying completed!")
                    print(f"Final balance: {remaining_balance/1e9:.9f} TON")
                    print(f"All NFTs and TON have been transferred to {TARGET_ADDRESS}")
                    break
                elif remaining_balance < to_nano(0.05):
                    print(f"\n✅ Wallet has minimal balance left: {remaining_balance/1e9:.9f} TON")
                    print(f"All NFTs have been transferred to {TARGET_ADDRESS}")
                    break
                else:
                    # Wait and retry if there's still a significant balance
                    print(f"Waiting for transactions to complete...")
                    time.sleep(5)
                    continue
            
            print(f"Found {len(nft_items)} NFTs on {wallet_address}")
            
            # Display all NFTs
            print("\n=== NFT LIST ===")
            for idx, nft in enumerate(nft_items):
                nft_address = nft.get("address", "")
                nft_name = nft.get("metadata", {}).get("name", f"NFT #{idx+1}")
                collection_name = nft.get("collection", {}).get("name", "Unknown Collection")
                
                print(f"NFT {idx+1}/{len(nft_items)}: {nft_name} ({collection_name})")
                print(f"  Address: {nft_address}")
                
                # If available, print more details
                if "metadata" in nft:
                    metadata = nft["metadata"]
                    if "description" in metadata:
                        print(f"  Description: {metadata['description']}")
                    if "attributes" in metadata:
                        print(f"  Attributes: {metadata['attributes']}")
                    if "image" in metadata:
                        print(f"  Image URL: {metadata['image']}")
                
                print("")  # Empty line for better readability
            
            # Transfer each NFT one by one
            success_count = 0
            for idx, nft in enumerate(nft_items):
                nft_address = nft.get("address", "")
                nft_name = nft.get("metadata", {}).get("name", f"NFT #{idx+1}")
                collection_name = nft.get("collection", {}).get("name", "Unknown Collection")
                full_name = f"{nft_name} ({collection_name})"
                
                print(f"\n=== TRANSFERRING NFT {idx+1}/{len(nft_items)} ===")
                print(f"Selected NFT: {full_name}")
                print(f"Address: {nft_address}")
                print(f"Target: {TARGET_ADDRESS}")
                
                # Transfer the NFT
                success = transfer_nft(wallet, seed_phrase, nft_address, full_name)
                if success:
                    print(f"\n✅ NFT transfer initiated successfully!")
                    success_count += 1
                else:
                    print(f"\n❌ NFT transfer failed.")
                    
                # Wait a bit between transfers to avoid rate limits and allow blockchain to process
                time.sleep(2)
                
                # Update wallet details after each transfer
                current_balance = check_balance(wallet_address)
                wallet['balance'] = current_balance
                
                # If balance is getting low, stop and wait for next round
                if current_balance < to_nano(0.05):
                    print(f"\n⚠️ Balance too low ({current_balance/1e9:.9f} TON), stopping transfers")
                    break
            
            print(f"\n=== TRANSFER SUMMARY ===")
            print(f"Successfully initiated transfer of {success_count}/{len(nft_items)} NFTs")
            print(f"From: {wallet_address} ({wallet['desc']})")
            print(f"To: {TARGET_ADDRESS}")
            print(f"Remaining balance: {current_balance/1e9:.9f} TON")
            
            # If we've transferred all NFTs in this batch, wait a bit to let blockchain settle
            if success_count == len(nft_items):
                print(f"Waiting for transactions to complete...")
                time.sleep(10)
            
    else:
        print("\n❌ No wallet with balance found. Cannot retrieve NFTs.")

def send_ton(wallet_config, seed_phrase, amount_ton):
    """Send TON to the target address"""
    print(f"\n=== SENDING {amount_ton} TON ===")
    
    try:
        # Unpack wallet configuration
        version = wallet_config['version']
        workchain = wallet_config['workchain']
        wallet_id = wallet_config['wallet_id']
        address = wallet_config['address']
        desc = wallet_config['desc']
        balance = wallet_config['balance']
        
        # Convert amount to nano
        amount_nano = to_nano(amount_ton)
        print(f"Amount to send: {amount_ton} TON ({amount_nano} nano)")
        
        if balance < amount_nano:
            print(f"❌ Insufficient balance: {balance/1e9:.9f} TON < {amount_ton} TON")
            return False
        
        # Get mnemonics from the seed phrase
        mnemonics = seed_phrase.split()
        
        # Initialize wallet with the correct version and parameters
        _, _, _, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=version,
            workchain=workchain,
            wallet_id=wallet_id
        )
        
        # Verify the wallet address matches what we found
        generated_address = wallet.address.to_string(True, True, True)
        if generated_address != address:
            print(f"❌ ERROR: Generated address {generated_address} doesn't match expected address {address}")
            return False
        
        # Get current seqno
        seqno = get_seqno(address)
        print(f"Current seqno: {seqno}")
        
        # Create transfer message
        message = wallet.create_transfer_message(
            to_addr=TARGET_ADDRESS,
            amount=amount_nano,
            seqno=seqno,
            payload="",  # Optional comment
            send_mode=3  # Default send mode
        )
        
        # Sign and send the transaction
        signed_message = message["message"].to_boc(False)
        
        # Send the transaction using TonCenter API
        send_tx_url = "https://toncenter.com/api/v2/sendBoc"
        headers = {"X-API-Key": API_KEY}
        
        # Convert BOC to base64
        boc_b64 = base64.b64encode(signed_message).decode('utf-8')
        payload = {"boc": boc_b64}
        
        print(f"Sending TON transfer transaction...")
        print(f"From: {address} ({desc})")
        print(f"To: {TARGET_ADDRESS}")
        print(f"Amount: {amount_ton} TON")
        
        response = requests.post(send_tx_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok") == True:
                print("\n✅ TON transfer transaction sent successfully!")
                return True
            else:
                print(f"\n❌ Failed to send TON transfer: {result}")
                return False
        else:
            print(f"\n❌ Failed to send TON transfer: {response.text}")
            return False
    except Exception as e:
        print(f"\n❌ Error sending TON transfer: {str(e)}")
        return False

if __name__ == "__main__":
    # Install required packages
    import subprocess
    
    # Check if required packages are installed, if not install them
    required_packages = ["tonsdk", "python-dotenv"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"Installing required package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Run the main function
    main() 