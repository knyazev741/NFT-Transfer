#!/usr/bin/env python3
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from typing import List, Dict
from collections import defaultdict

# Load environment variables
load_dotenv()

# Constants
TONAPI_KEY = os.getenv("TONAPI_KEY")
TARGET_ADDRESS = os.getenv("TARGET_ADDRESS")

async def get_nft_items(client: aiohttp.ClientSession, address: str) -> List[Dict]:
    """Get all NFTs owned by an address using TonAPI"""
    url = f"https://tonapi.io/v2/accounts/{address}/nfts"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with client.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("nft_items", [])
            else:
                print(f"Error getting NFTs: {response.status} - {await response.text()}")
                return []
    except Exception as e:
        print(f"Error getting NFTs: {str(e)}")
        return []

def get_lock_period(nft_name: str) -> str:
    """Extract lock period from NFT name"""
    nft_name = nft_name.lower()
    if "1-month lock" in nft_name:
        return "1 Month"
    elif "2-month lock" in nft_name:
        return "2 Months"
    elif "3-month lock" in nft_name:
        return "3 Months"
    elif "6-month lock" in nft_name:
        return "6 Months"
    elif "1-year lock" in nft_name:
        return "1 Year"
    return "Unknown"

async def main():
    print("=== Woof Vault Counter ===")
    
    if not TONAPI_KEY:
        print("Error: TONAPI_KEY not found in .env file")
        return
        
    if not TARGET_ADDRESS:
        print("Error: TARGET_ADDRESS not found in .env file")
        return
    
    print(f"Checking Woof vaults for address: {TARGET_ADDRESS}")
    
    async with aiohttp.ClientSession() as session:
        nfts = await get_nft_items(session, TARGET_ADDRESS)
        
        if not nfts:
            print("No NFTs found for this address")
            return
            
        # Count Woof vaults by lock period
        vault_counts = defaultdict(int)
        for nft in nfts:
            name = nft.get("metadata", {}).get("name", "")
            if "$woof vault" in name.lower():
                period = get_lock_period(name)
                vault_counts[period] += 1
        
        total_vaults = sum(vault_counts.values())
        
        print("\n=== Results ===")
        print("-" * 50)
        print(f"Total NFTs found: {len(nfts)}")
        print(f"Total Woof vaults: {total_vaults}")
        print("\nBreakdown by lock period:")
        
        # Sort periods in a specific order
        period_order = ["1 Month", "2 Months", "3 Months", "6 Months", "1 Year", "Unknown"]
        for period in period_order:
            count = vault_counts[period]
            if count > 0:
                percentage = (count / total_vaults * 100)
                print(f"{period}: {count} vaults ({percentage:.1f}%)")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 