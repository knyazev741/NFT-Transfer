#!/usr/bin/env python3
import requests
import base64
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.crypto import mnemonic_to_wallet_key

# Constants
API_KEY = "82c720448bf7ae5de2339efffe7779f81b6b1ee91f22bb65176efa8dfecdd7a8"
SEED_PHRASE = "check bean high swamp myth bag genre brush timber peasant stone live saddle famous wedding repair hammer dad rely sudden differ little win bike"
TARGET_ADDRESS = "UQDcym0-0e5Uqhhx6hSisfCo6SsPClIUojVAkFi0A2YFGPGv"

# Transaction parameters
AMOUNT_TON = 0.1  # Fixed amount to send

# Wallet configuration (as found by check_balance.py)
WALLET_VERSION = WalletVersionEnum.v4r2
WORKCHAIN = 0
SUBWALLET_ID = 698983191

def to_nano(amount):
    """Convert TON to nanoTON"""
    return int(amount * 1e9)

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
        
        # Default to 0 if can't get seqno (new wallet or error)
        return 0
    except Exception as e:
        print(f"Error getting seqno: {str(e)}")
        return 0

def main():
    print("=== TON TRANSACTION SENDER ===\n")
    
    # Use fixed amount
    amount = AMOUNT_TON
    amount_nano = to_nano(amount)
    print(f"Amount to send: {amount} TON ({amount_nano} nano)")
    
    # Create wallet from seed phrase
    mnemonics = SEED_PHRASE.split()
    
    # Initialize wallet with the correct version and parameters
    mnemo, public_key, private_key, wallet = Wallets.from_mnemonics(
        mnemonics=mnemonics,
        version=WALLET_VERSION,
        workchain=WORKCHAIN,
        wallet_id=SUBWALLET_ID
    )
    
    # Get wallet address
    wallet_address = wallet.address.to_string(True, True, True)
    print(f"\nWallet address: {wallet_address}")
    
    # Check wallet balance
    wallet_info_url = f"https://toncenter.com/api/v2/getAddressBalance?address={wallet_address}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = requests.get(wallet_info_url, headers=headers)
        if response.status_code == 200:
            balance = int(response.json().get("result", "0"))
            print(f"Balance: {balance/1e9:.9f} TON")
            
            if balance < amount_nano:
                print("⚠️ Insufficient balance!")
                return
    except Exception as e:
        print(f"Error checking balance: {str(e)}")
        return
    
    # Get current seqno
    seqno = get_seqno(wallet_address)
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
    
    # Convert BOC to base64 - this fixes the encoding issue
    boc_b64 = base64.b64encode(signed_message).decode('utf-8')
    payload = {"boc": boc_b64}
    
    try:
        response = requests.post(send_tx_url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get("ok") == True:
                print("\n✅ Transaction sent successfully!")
                print(f"From: {wallet_address}")
                print(f"To: {TARGET_ADDRESS}")
                print(f"Amount: {amount} TON")
            else:
                print(f"\n❌ Failed to send transaction: {result}")
        else:
            print(f"\n❌ Failed to send transaction: {response.text}")
    except Exception as e:
        print(f"\n❌ Error sending transaction: {str(e)}")

if __name__ == "__main__":
    # Install required packages
    import subprocess
    import sys
    
    # Check if required packages are installed, if not install them
    required_packages = ["tonsdk"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"Installing required package: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Run the main function
    main() 