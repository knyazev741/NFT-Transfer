#!/usr/bin/env python3
import os
import requests
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
TONAPI_KEY = os.getenv("TONAPI_KEY")

address = "EQDcym0-0e5Uqhhx6hSisfCo6SsPClIUojVAkFi0A2YFGKxq"

async def get_account_state(address: str):
    """Get account state using TonAPI"""
    url = f"https://tonapi.io/v2/accounts/{address}"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    text = await response.text()
                    print(f"Account state error: {text}")
                return None
    except Exception as e:
        print(f"Error getting account state: {e}")
        return None

def try_different_seqno_methods(address: str):
    """Try different API endpoints to get seqno"""
    
    # Method 1: TonCenter runGetMethod
    print("=== Method 1: TonCenter runGetMethod ===")
    url = f"https://toncenter.com/api/v2/runGetMethod"
    params = {
        "address": address,
        "method": "seqno",
        "stack": "[]"
    }
    if API_KEY:
        params["api_key"] = API_KEY
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Method 2: TonCenter getAddressInformation  
    print("=== Method 2: TonCenter getAddressInformation ===")
    url = f"https://toncenter.com/api/v2/getAddressInformation"
    params = {"address": address}
    if API_KEY:
        params["api_key"] = API_KEY
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {data}")
        if data.get("ok"):
            result = data.get("result", {})
            print(f"State: {result.get('state', 'unknown')}")
            print(f"Code: {result.get('code', 'none')}")
            print(f"Data: {result.get('data', 'none')}")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print(f"Analyzing wallet: {address}")
    print()
    
    # Get account state
    account_data = await get_account_state(address)
    if account_data:
        print("=== Account Information ===")
        print(f"Status: {account_data.get('status', 'unknown')}")
        print(f"Balance: {account_data.get('balance', 0)} nanoTON")
        print(f"Is Active: {account_data.get('is_active', False)}")
        
        # Check if it's a wallet at all
        if 'code_hash' in account_data:
            print(f"Code Hash: {account_data['code_hash']}")
        
        if 'interfaces' in account_data:
            print(f"Interfaces: {account_data['interfaces']}")
            
        print()
    
    # Try different methods to get seqno
    try_different_seqno_methods(address)

if __name__ == "__main__":
    asyncio.run(main()) 