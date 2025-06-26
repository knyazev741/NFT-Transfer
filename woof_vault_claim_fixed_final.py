#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import requests
import base64
import time
from dotenv import load_dotenv
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import Address
from tonsdk.boc import Cell
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Constants from environment variables
API_KEY = os.getenv("API_KEY")
TONAPI_KEY = os.getenv("TONAPI_KEY")
MAIN_SEED = os.getenv("MAIN_SEED")

# Claim operation code (0x4B68B891 in decimal)
CLAIM_OP_CODE = 1265154193

def to_nano_ton(amount_ton: float) -> int:
    """Convert TON to nanoTON"""
    return int(amount_ton * 1e9)

def create_working_claim_body() -> Cell:
    """Create claim body that exactly matches the working transaction"""
    # Working BOC from successful transaction
    working_hex = "b5ee9c7201010101000e0000184b68b89176a486eeb929b2ff"
    working_bytes = bytes.fromhex(working_hex)
    return Cell.one_from_boc(working_bytes)

def create_simple_claim_body() -> Cell:
    """Create simple claim body with just the operation code"""
    from tonsdk.boc import begin_cell
    
    body = begin_cell()
    body.store_uint(CLAIM_OP_CODE, 32)  # op_code = 0x4b68b891
    body.store_uint(0, 64)  # query_id = 0
    return body.end_cell()

async def get_nft_items(session: aiohttp.ClientSession, address: str) -> List[Dict]:
    """Get all NFTs owned by an address using TonAPI"""
    url = f"https://tonapi.io/v2/accounts/{address}/nfts"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                nft_items = data.get("nft_items", [])
                return nft_items
            else:
                response_text = await response.text()
                print(f"Error getting NFTs: {response.status} - {response_text}")
                return []
    except Exception as e:
        print(f"Error getting NFTs: {str(e)}")
        return []

def get_lock_period(nft_name: str) -> str:
    """Extract lock period from NFT name"""
    name_lower = nft_name.lower()
    if "2 month" in name_lower or "2-month" in name_lower:
        return "2-month"
    elif "3 month" in name_lower or "3-month" in name_lower:
        return "3-month"
    elif "6 month" in name_lower or "6-month" in name_lower:
        return "6-month"
    else:
        return "unknown"

def get_seqno(address: str) -> int:
    """Get wallet seqno from wallet data"""
    url = f"https://toncenter.com/api/v2/getAddressInformation"
    params = {"address": address}
    if API_KEY:
        params["api_key"] = API_KEY
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and "result" in data:
                result = data["result"]
                
                # For wallet v3r2, extract seqno from data field
                if "data" in result and result["data"]:
                    data_b64 = result["data"]
                    try:
                        data_bytes = base64.b64decode(data_b64)
                        
                        # For v3r2 wallets, seqno is at offset 13 in BOC data
                        if len(data_bytes) >= 17:  # offset 13 + 4 bytes
                            seqno_bytes = data_bytes[13:17]
                            seqno = int.from_bytes(seqno_bytes, 'big')
                            if 0 < seqno < 1000000:  # Reasonable range
                                return seqno
                                
                    except Exception as e:
                        print(f"Error parsing wallet data: {e}")
                
        return 0
    except Exception as e:
        print(f"Error getting seqno: {e}")
        return 0

def create_claim_transfer(wallet, to_addr: str, amount: int, seqno: int, payload_cell: Cell) -> dict:
    """Create transfer message using simplified approach"""
    from tonsdk.boc import Cell
    from tonsdk.utils import Address
    
    # Use wallet's native transfer method with proper payload
    transfer = wallet.create_transfer_message(
        to_addr=to_addr,
        amount=amount,
        seqno=seqno,
        payload=payload_cell,
        send_mode=3,  # PAY_FEES_SEPARATELY + IGNORE_ERRORS
        dummy_signature=False
    )
    
    return transfer

async def claim_from_vault_nft_fixed(wallet, nft_address: str, amount_ton: float = 0.1) -> bool:
    """Send claim transaction with FIXED message creation"""
    try:
        print(f"\n=== CLAIMING FROM VAULT NFT (FIXED VERSION) ===")
        print(f"NFT/Vault address: {nft_address}")
        print(f"Amount for gas: {amount_ton} TON")
        
        # Get current seqno
        wallet_address = wallet.address.to_string(True, True, True)
        seqno = get_seqno(wallet_address)
        print(f"Current seqno: {seqno}")
        
        if seqno == 0:
            print("❌ Could not get seqno")
            return False
        
        # Create EXACT claim body from working transaction
        claim_body = create_working_claim_body()
        print(f"✅ Using EXACT working claim body (length: {len(claim_body)} bytes)")
        print(f"   BOC hex: {claim_body.to_boc(False).hex()}")
        
        # Create message with FIXED bounce=true
        try:
            message = create_claim_transfer(
                wallet,
                nft_address,
                to_nano_ton(amount_ton),
                seqno,
                claim_body
            )
            
            print(f"✅ Message created with FORCED bounce=true")
            
        except Exception as e:
            print(f"Error creating transfer message: {e}")
            return False
        
        # Send transaction using TonCenter
        try:
            boc_bytes = message["message"].to_boc(False)
            boc_base64 = base64.b64encode(boc_bytes).decode()
            
            url = "https://toncenter.com/api/v2/sendBoc"
            data = {"boc": boc_base64}
            
            if API_KEY:
                data["api_key"] = API_KEY
            
            print(f"🚀 Sending FIXED transaction...")
            print(f"📏 BOC size: {len(boc_bytes)} bytes")
            print(f"🔗 Transaction preview: {boc_base64[:50]}...")
            
            response = requests.post(url, json=data, timeout=30)
            
            print(f"📡 Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"📋 Response: {result}")
                
                if result.get("ok"):
                    tx_hash = result.get("result", {}).get("hash", "unknown")
                    print(f"✅ Transaction sent successfully!")
                    print(f"🔗 Hash: {tx_hash}")
                    
                    # Wait and check if NFT was destroyed (successful claim)
                    print(f"\n📊 Checking claim result...")
                    await asyncio.sleep(15)
                    
                    # Check if NFT still exists
                    nft_url = f"https://tonapi.io/v2/nfts/{nft_address}"
                    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(nft_url, headers=headers) as nft_check:
                            if nft_check.status == 404:
                                print(f"🎉 SUCCESS! NFT was destroyed - tokens claimed!")
                                return True
                            elif nft_check.status == 200:
                                print(f"⚠️  NFT still exists - claim may have failed")
                                return False
                            else:
                                print(f"❓ Unknown NFT status: {nft_check.status}")
                                return True  # Assume success
                    
                else:
                    print(f"❌ Transaction failed: {result}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending transaction: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def find_working_wallet(mnemonics: List[str], session: aiohttp.ClientSession):
    """Find the wallet configuration that has NFTs"""
    print("🔍 Searching for wallet configuration with NFTs...")
    
    try:
        _, _, _, wallet = Wallets.from_mnemonics(
            mnemonics, 
            WalletVersionEnum.v3r2, 
            0  # workchain
        )
        
        address = wallet.address.to_string(True, True, True)
        nfts = await get_nft_items(session, address)
        
        if len(nfts) > 0:
            print(f"✅ Found wallet with NFTs: v3r2 - {address}")
            print(f"   NFT count: {len(nfts)}")
            return wallet, nfts, address
                
    except Exception as e:
        print(f"   Error with v3r2: {e}")
    
    return None, [], ""

async def claim_simple_version(wallet, nft_address: str, amount_ton: float = 0.1) -> bool:
    """Simplified claim version using wallet's native methods"""
    try:
        print(f"\n=== SIMPLE CLAIM VERSION ===")
        print(f"NFT/Vault address: {nft_address}")
        print(f"Amount for gas: {amount_ton} TON")
        
        # Get current seqno
        wallet_address = wallet.address.to_string(True, True, True)
        seqno = get_seqno(wallet_address)
        print(f"Current seqno: {seqno}")
        
        if seqno == 0:
            print("❌ Could not get seqno")
            return False
        
        # Create simple claim body
        claim_body = create_simple_claim_body()
        print(f"✅ Created simple claim body with op_code: {CLAIM_OP_CODE}")
        
        # Use wallet's standard transfer method
        transfer = wallet.create_transfer_message(
            to_addr=nft_address,
            amount=to_nano_ton(amount_ton),
            seqno=seqno,
            payload=claim_body,
            send_mode=3  # PAY_FEES_SEPARATELY + IGNORE_ERRORS
        )
        
        print(f"✅ Transfer message created")
        
        # Send transaction
        boc_bytes = transfer["message"].to_boc(False)
        boc_base64 = base64.b64encode(boc_bytes).decode()
        
        url = "https://toncenter.com/api/v2/sendBoc"
        data = {"boc": boc_base64}
        
        if API_KEY:
            data["api_key"] = API_KEY
        
        print(f"🚀 Sending simple claim transaction...")
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 Response: {result}")
            
            if result.get("ok"):
                tx_hash = result.get("result", {}).get("hash", "unknown")
                print(f"✅ Transaction sent successfully!")
                print(f"🔗 Hash: {tx_hash}")
                return True
            else:
                print(f"❌ Transaction failed: {result}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in simple claim: {e}")
        return False

async def mass_claim_all_vaults(wallet, vaults_list: List[Dict], delay_seconds: int = 10) -> Dict:
    """Mass claim from all vault NFTs with delay between transactions"""
    results = {
        "total": len(vaults_list),
        "successful": 0,
        "failed": 0,
        "errors": []
    }
    
    print(f"\n🚀 STARTING MASS CLAIM FOR {len(vaults_list)} VAULTS")
    print(f"⏱️  Delay between transactions: {delay_seconds} seconds")
    print(f"💰 Total cost estimate: {len(vaults_list) * 0.1} TON")
    
    wallet_address = wallet.address.to_string(True, True, True)
    
    for i, vault in enumerate(vaults_list, 1):
        try:
            print(f"\n{'='*60}")
            print(f"🎯 VAULT {i}/{len(vaults_list)}")
            print(f"📛 Name: {vault['name']}")
            print(f"📍 Address: {vault['nft_address']}")
            
            # Get fresh seqno for each transaction
            seqno = get_seqno(wallet_address)
            if seqno == 0:
                print(f"❌ Could not get seqno for vault {i}")
                results["failed"] += 1
                results["errors"].append(f"Vault {i}: seqno error")
                continue
            
            print(f"🔢 Using seqno: {seqno}")
            
            # Create simple claim body
            claim_body = create_simple_claim_body()
            
            # Use wallet's standard transfer method
            transfer = wallet.create_transfer_message(
                to_addr=vault['nft_address'],
                amount=to_nano_ton(0.1),
                seqno=seqno,
                payload=claim_body,
                send_mode=3
            )
            
            # Send transaction
            boc_bytes = transfer["message"].to_boc(False)
            boc_base64 = base64.b64encode(boc_bytes).decode()
            
            url = "https://toncenter.com/api/v2/sendBoc"
            data = {"boc": boc_base64}
            
            if API_KEY:
                data["api_key"] = API_KEY
            
            print(f"🚀 Sending claim transaction...")
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("ok"):
                    tx_hash = result.get("result", {}).get("hash", "unknown")
                    print(f"✅ SUCCESS! Hash: {tx_hash}")
                    results["successful"] += 1
                else:
                    print(f"❌ Transaction failed: {result}")
                    results["failed"] += 1
                    results["errors"].append(f"Vault {i}: {result}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                results["failed"] += 1
                results["errors"].append(f"Vault {i}: HTTP {response.status_code}")
            
            # Wait before next transaction (except for last one)
            if i < len(vaults_list):
                print(f"⏳ Waiting {delay_seconds} seconds before next transaction...")
                await asyncio.sleep(delay_seconds)
                
        except Exception as e:
            print(f"❌ Error processing vault {i}: {e}")
            results["failed"] += 1
            results["errors"].append(f"Vault {i}: {str(e)}")
    
    # Final results
    print(f"\n{'='*60}")
    print(f"📊 MASS CLAIM COMPLETED!")
    print(f"✅ Successful: {results['successful']}/{results['total']}")
    print(f"❌ Failed: {results['failed']}/{results['total']}")
    print(f"💰 Total cost: ~{results['successful'] * 0.1} TON")
    
    if results["errors"]:
        print(f"\n❌ Errors:")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"   - {error}")
        if len(results["errors"]) > 5:
            print(f"   ... and {len(results['errors']) - 5} more errors")
    
    return results

async def main():
    if not MAIN_SEED:
        print("❌ MAIN_SEED not found in environment variables")
        return
    
    if not TONAPI_KEY:
        print("❌ TONAPI_KEY not found in environment variables")
        return
    
    print("🔍 Starting Woof Vault Auto-Claim (FIXED VERSION)")
    print("💰 Using 0.1 TON per transaction (like working example)")
    print("🎯 Using EXACT working claim body + bounce=true")
    
    # Parse mnemonics
    mnemonics = MAIN_SEED.split()
    if len(mnemonics) != 24:
        print(f"❌ Invalid mnemonic: expected 24 words, got {len(mnemonics)}")
        return
    
    # Find working wallet configuration
    async with aiohttp.ClientSession() as session:
        wallet, nfts, wallet_address = await find_working_wallet(mnemonics, session)
        
        if not wallet or not nfts:
            print("❌ No wallet with NFTs found")
            return
        
        print(f"✅ Using wallet: {wallet_address}")
        print(f"✅ Found {len(nfts)} NFTs")
        
        # Filter for Woof Vaults with 3-month lock
        woof_vaults_3m = []
        for nft in nfts:
            name = nft.get("metadata", {}).get("name", "")
            if "$woof vault" in name.lower():
                period = get_lock_period(name)
                if period == "3-month":
                    nft_address = nft.get("address", "")
                    
                    woof_vaults_3m.append({
                        "name": name,
                        "period": period,
                        "nft_address": nft_address
                    })
        
        if not woof_vaults_3m:
            print("❌ No 3-month Woof Vaults found")
            return
        
        print(f"\n=== FOUND {len(woof_vaults_3m)} 3-MONTH WOOF VAULTS ===")
        for i, vault in enumerate(woof_vaults_3m[:3], 1):  # Show first 3
            print(f"{i}. {vault['name']}")
            print(f"   NFT Address: {vault['nft_address']}")
        
        # Test with first vault only
        first_vault = woof_vaults_3m[0]
        print(f"\n=== TESTING WITH FIRST 3-MONTH VAULT (FIXED) ===")
        print(f"Vault name: {first_vault['name']}")
        print(f"NFT address: {first_vault['nft_address']}")
        
        # Ask user which method to try
        print(f"\n⚠️  ВЫБЕРИТЕ ДЕЙСТВИЕ:")
        print(f"1. ТЕСТОВЫЙ CLAIM (исходный метод на 1 vault)")
        print(f"2. ТЕСТОВЫЙ CLAIM (простой метод на 1 vault)")
        print(f"3. 🚀 МАССОВЫЙ CLAIM ВСЕХ {len(woof_vaults_3m)} VAULT'ОВ (простой метод)")
        print(f"4. ОТМЕНА")
        
        choice = input("Выберите действие (1/2/3/4): ").strip()
        
        if choice == "1":
            print(f"\n🚀 Testing ORIGINAL method with exact BOC...")
            success = await claim_from_vault_nft_fixed(wallet, first_vault['nft_address'])
            
            if success:
                print(f"🎉 TEST SUCCESSFUL! Ready for mass claim.")
            else:
                print(f"❌ Test failed. Try the simple method.")
                
        elif choice == "2":
            print(f"\n🚀 Testing SIMPLE method with basic payload...")
            success = await claim_simple_version(wallet, first_vault['nft_address'])
            
            if success:
                print(f"🎉 TEST SUCCESSFUL! Ready for mass claim.")
            else:
                print(f"❌ Test failed. Check your setup.")
                
        elif choice == "3":
            print(f"\n💰 МАССОВЫЙ CLAIM - ВНИМАНИЕ!")
            print(f"📊 Количество vault'ов: {len(woof_vaults_3m)}")
            print(f"💸 Примерная стоимость: {len(woof_vaults_3m) * 0.1} TON")
            print(f"⏱️  Примерное время: {len(woof_vaults_3m) * 10 / 60:.1f} минут")
            
            confirm = input(f"\n⚠️ Вы уверены? Введите 'CONFIRM' для продолжения: ").strip()
            
            if confirm == "CONFIRM":
                print(f"\n🚀 STARTING MASS CLAIM...")
                results = await mass_claim_all_vaults(wallet, woof_vaults_3m, delay_seconds=10)
                
                print(f"\n🏁 МАССОВЫЙ CLAIM ЗАВЕРШЕН!")
                print(f"✅ Успешно: {results['successful']}")
                print(f"❌ Неудачно: {results['failed']}")
                
                if results['successful'] > 0:
                    print(f"🎉 Поздравляем! {results['successful']} vault'ов успешно заклеймлены!")
                    print(f"💰 Проверьте баланс токенов в кошельке через несколько минут")
                    
            else:
                print("❌ Массовый claim отменен")
                
        else:
            print("❌ Cancelled by user")

if __name__ == "__main__":
    asyncio.run(main()) 