#!/usr/bin/env python3
import requests
import hashlib
from tonsdk.crypto import mnemonic_to_wallet_key
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import Address

# Constants
API_KEY = "82c720448bf7ae5de2339efffe7779f81b6b1ee91f22bb65176efa8dfecdd7a8"
SEED_PHRASE = "check bean high swamp myth bag genre brush timber peasant stone live saddle famous wedding repair hammer dad rely sudden differ little win bike"

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

def main():
    print("=== CHECKING BALANCES FOR ALL POSSIBLE WALLET CONFIGURATIONS ===\n")
    
    # Split the seed phrase
    mnemonics = SEED_PHRASE.split()
    print(f"Seed phrase contains {len(mnemonics)} words.")
    print(f"Seed phrase (first 3 words): {' '.join(mnemonics[:3])}...\n")
    
    try:
        # Convert mnemonic to keypair
        keypair = mnemonic_to_wallet_key(mnemonics)
        public_key = keypair[0]
        private_key = keypair[1]
        
        print(f"Public key from seed: {public_key.hex()}")
        
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
        
        print("\n=== GENERATING ADDRESSES AND CHECKING BALANCES ===")
        addresses_with_balance = []
        
        # Generate addresses for V3 wallets (no wallet_id)
        for workchain in workchains:
            for version, version_name in wallet_versions:
                if version_name.startswith("v3"):
                    try:
                        # Generate mnemonics and wallet
                        mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                            mnemonics=mnemonics,
                            version=version,
                            workchain=workchain
                        )
                        addr = wallet.address.to_string(True, True, True)
                        desc = f"{version_name} (wc={workchain})"
                        
                        # Check balance
                        balance = check_balance(addr)
                        if balance > 0:
                            print(f"✅ {desc}: {addr}")
                            print(f"   Balance: {balance/1e9:.9f} TON")
                            addresses_with_balance.append((desc, addr, balance))
                        else:
                            print(f"{desc}: {addr}")
                    except Exception as e:
                        print(f"Error with {version_name} (wc={workchain}): {str(e)}")
        
        # Generate addresses for V4 wallets (with wallet_id)
        for workchain in workchains:
            for version, version_name in wallet_versions:
                if version_name.startswith("v4"):
                    for wallet_id in wallet_ids:
                        try:
                            # Generate mnemonics and wallet
                            mnemo, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                                mnemonics=mnemonics,
                                version=version,
                                workchain=workchain,
                                wallet_id=wallet_id
                            )
                            addr = wallet.address.to_string(True, True, True)
                            desc = f"{version_name} (wc={workchain}, id={wallet_id})"
                            
                            # Check balance
                            balance = check_balance(addr)
                            if balance > 0:
                                print(f"✅ {desc}: {addr}")
                                print(f"   Balance: {balance/1e9:.9f} TON")
                                addresses_with_balance.append((desc, addr, balance))
                            else:
                                print(f"{desc}: {addr}")
                        except Exception as e:
                            print(f"Error with {version_name} (wc={workchain}, id={wallet_id}): {str(e)}")
        
        # Print summary
        print("\n=== SUMMARY ===")
        if addresses_with_balance:
            print(f"Found {len(addresses_with_balance)} address(es) with balance:")
            for desc, addr, balance in addresses_with_balance:
                print(f"- {desc}: {addr}")
                print(f"  Balance: {balance/1e9:.9f} TON")
        else:
            print("No addresses with balance found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 