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

def get_seqno_toncenter(address: str) -> int:
    """Get wallet seqno using TonCenter API"""
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
        print(f"TonCenter response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"TonCenter data: {data}")
            if data.get("ok") and "stack" in data.get("result", {}):
                stack = data["result"]["stack"]
                if stack and len(stack) > 0:
                    seqno = int(stack[0][1], 16)
                    print(f"TonCenter seqno: {seqno}")
                    return seqno
        return 0
    except Exception as e:
        print(f"Error getting seqno: {e}")
        return 0

async def get_seqno_tonapi(address: str) -> int:
    """Get wallet seqno using TonAPI"""
    url = f"https://tonapi.io/v2/accounts/{address}/methods/seqno"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"TonAPI response: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"TonAPI data: {data}")
                    # TonAPI возвращает данные в другом формате
                    if 'decoded' in data and 'seqno' in data['decoded']:
                        seqno = data['decoded']['seqno']
                        print(f"TonAPI seqno: {seqno}")
                        return seqno
                else:
                    text = await response.text()
                    print(f"TonAPI error: {text}")
                return 0
    except Exception as e:
        print(f"Error getting seqno via TonAPI: {e}")
        return 0

async def get_account_info(address: str):
    """Get account info using TonAPI"""
    url = f"https://tonapi.io/v2/accounts/{address}"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"Account info response: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Account status: {data.get('status', 'unknown')}")
                    print(f"Account balance: {data.get('balance', 0)}")
                    print(f"Account is_active: {data.get('is_active', False)}")
                    return data
                else:
                    text = await response.text()
                    print(f"Account info error: {text}")
                return None
    except Exception as e:
        print(f"Error getting account info: {e}")
        return None

async def main():
    print(f"Checking wallet: {address}")
    print()
    
    print("=== Account Info ===")
    account_info = await get_account_info(address)
    print()
    
    print("=== TonCenter Seqno ===")
    seqno_tc = get_seqno_toncenter(address)
    print()
    
    print("=== TonAPI Seqno ===")
    seqno_ta = await get_seqno_tonapi(address)
    print()
    
    print("=== Summary ===")
    print(f"TonCenter seqno: {seqno_tc}")
    print(f"TonAPI seqno: {seqno_ta}")
    
    if account_info:
        print(f"Account active: {account_info.get('is_active', False)}")
        print(f"Account status: {account_info.get('status', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main()) 