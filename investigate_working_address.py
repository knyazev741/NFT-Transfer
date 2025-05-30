#!/usr/bin/env python3
import os
import requests
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
TONAPI_KEY = os.getenv("TONAPI_KEY")

# Рабочий адрес из примера
working_address = "UQDBH0zomzwYx1kmTRQlh1sQMns8RhthWjyiq_KdnUHZhdi9"

async def investigate_address(address: str):
    """Исследуем рабочий адрес через TonAPI"""
    print(f"=== ИССЛЕДОВАНИЕ РАБОЧЕГО АДРЕСА ===")
    print(f"Адрес: {address}")
    print()
    
    # 1. Получаем общую информацию о контракте
    url = f"https://tonapi.io/v2/accounts/{address}"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"=== ОБЩАЯ ИНФОРМАЦИЯ ===")
                print(f"HTTP Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"Статус: {data.get('status', 'unknown')}")
                    print(f"Баланс: {data.get('balance', 0)} nanoTON")
                    print(f"Активен: {data.get('is_active', False)}")
                    
                    if 'interfaces' in data:
                        print(f"Интерфейсы: {data['interfaces']}")
                    
                    if 'code_hash' in data:
                        print(f"Code Hash: {data['code_hash']}")
                        
                    if 'name' in data:
                        print(f"Имя: {data['name']}")
                        
                    print()
                    
                    # 2. Проверяем это NFT?
                    print(f"=== ПРОВЕРКА NFT ===")
                    nft_url = f"https://tonapi.io/v2/nfts/{address}"
                    async with session.get(nft_url, headers=headers) as nft_response:
                        print(f"NFT API Status: {nft_response.status}")
                        
                        if nft_response.status == 200:
                            nft_data = await nft_response.json()
                            
                            print(f"✅ ЭТО NFT!")
                            
                            if 'metadata' in nft_data:
                                metadata = nft_data['metadata']
                                print(f"Имя NFT: {metadata.get('name', 'неизвестно')}")
                                print(f"Описание: {metadata.get('description', 'нет')}")
                                
                            if 'collection' in nft_data and nft_data['collection']:
                                collection = nft_data['collection']
                                print(f"Коллекция: {collection.get('name', 'неизвестно')}")
                                print(f"Адрес коллекции: {collection.get('address', 'нет')}")
                                
                            if 'owner' in nft_data and nft_data['owner']:
                                owner = nft_data['owner']
                                print(f"Владелец: {owner.get('address', 'неизвестно')}")
                                
                        else:
                            print(f"❌ НЕ NFT или ошибка: {nft_response.status}")
                            print(await nft_response.text())
                    
                    print()
                    
                    # 3. Проверяем доступные методы контракта
                    print(f"=== МЕТОДЫ КОНТРАКТА ===")
                    methods_to_try = [
                        "get_nft_data",
                        "get_vault_address", 
                        "get_vault_data",
                        "get_vault_info",
                        "seqno",
                        "get_wallet_address"
                    ]
                    
                    for method in methods_to_try:
                        try:
                            method_url = f"https://toncenter.com/api/v2/runGetMethod"
                            params = {
                                "address": address,
                                "method": method,
                                "stack": "[]"
                            }
                            if API_KEY:
                                params["api_key"] = API_KEY
                            
                            method_response = requests.get(method_url, params=params, timeout=5)
                            if method_response.status_code == 200:
                                method_data = method_response.json()
                                if method_data.get("ok"):
                                    result = method_data.get("result", {})
                                    if "stack" in result:
                                        print(f"✅ {method}: {result['stack']}")
                                    else:
                                        print(f"✅ {method}: OK")
                                else:
                                    print(f"❌ {method}: {method_data.get('error', 'failed')}")
                            else:
                                print(f"❌ {method}: HTTP {method_response.status_code}")
                        except Exception as e:
                            print(f"❌ {method}: {str(e)}")
                    
                    print()
                    
                    # 4. Получаем последние транзакции
                    print(f"=== ПОСЛЕДНИЕ ТРАНЗАКЦИИ ===")
                    tx_url = f"https://tonapi.io/v2/accounts/{address}/events"
                    async with session.get(tx_url, headers=headers) as tx_response:
                        if tx_response.status == 200:
                            tx_data = await tx_response.json()
                            events = tx_data.get('events', [])
                            
                            for i, event in enumerate(events[:5]):  # Первые 5 транзакций
                                print(f"{i+1}. {event.get('event_id', 'unknown')}")
                                
                                if 'actions' in event:
                                    for action in event['actions']:
                                        action_type = action.get('type', 'unknown')
                                        print(f"   Тип: {action_type}")
                                        
                                        if action_type == 'TonTransfer':
                                            ton_transfer = action.get('TonTransfer', {})
                                            print(f"   Сумма: {ton_transfer.get('amount', 0)} nanoTON")
                                            print(f"   От: {ton_transfer.get('sender', {}).get('address', 'unknown')}")
                                            print(f"   К: {ton_transfer.get('recipient', {}).get('address', 'unknown')}")
                        
                else:
                    text = await response.text()
                    print(f"Ошибка: {text}")
                    
    except Exception as e:
        print(f"Ошибка при исследовании: {e}")

async def main():
    await investigate_address(working_address)
    
    print("\n" + "="*50)
    print("СРАВНЕНИЕ С НАШИМ WOOF VAULT NFT")
    print("="*50)
    
    # Наш NFT адрес из вывода скрипта
    our_nft = "0:0a00ad2a54898ba0bd71c4340103b4efb476f5329e38ceec72c272c01e5e93af"
    await investigate_address(our_nft)

if __name__ == "__main__":
    asyncio.run(main()) 