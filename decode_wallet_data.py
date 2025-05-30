#!/usr/bin/env python3
import base64
from tonsdk.boc import Cell

# Data from wallet AFTER second transaction  
data_b64 = "te6cckEBAQEAKgAAUAAABVwpqaMXhSqhXUMSsX25E+5+XOg1DlimhSpgf7BIrhzmBQR0CcA3qka/"

# Decode base64 to bytes
data_bytes = base64.b64decode(data_b64)

print("=== Wallet v3r2 Data Structure ===")
print(f"Data bytes length: {len(data_bytes)}")
print(f"Data hex: {data_bytes.hex()}")

# Create Cell from bytes
try:
    cell = Cell()
    cell.bits.write_bytes(data_bytes)
    
    # Try to parse manually from hex
    hex_data = data_bytes.hex()
    print(f"Raw hex data: {hex_data}")
    
    # Manual parsing - first 4 bytes should be seqno
    if len(data_bytes) >= 4:
        seqno_bytes = data_bytes[:4]
        seqno = int.from_bytes(seqno_bytes, 'big')
        print(f"Manual seqno (big endian): {seqno}")
        
        seqno_le = int.from_bytes(seqno_bytes, 'little') 
        print(f"Manual seqno (little endian): {seqno_le}")
        
    # Manual hex parsing
    if len(hex_data) >= 8:  # At least 32 bits for seqno
        seqno_hex = hex_data[:8]  # First 32 bits
        seqno = int(seqno_hex, 16)
        print(f"Manual seqno from hex: {seqno}")
        
    if len(hex_data) >= 16:  # 64 bits for seqno + wallet_id
        wallet_id_hex = hex_data[8:16]  # Next 32 bits
        wallet_id = int(wallet_id_hex, 16)
        print(f"Manual wallet_id: {wallet_id}")
        
    # Try to decode the BOC header to find actual data
    print(f"\n=== BOC Header Analysis ===")
    
    # Look for data pattern after BOC header
    # BOC format usually has some header bytes, then actual data
    for i in range(min(20, len(data_bytes) - 4)):
        chunk = data_bytes[i:i+4]
        seqno_candidate = int.from_bytes(chunk, 'big')
        if 0 < seqno_candidate < 1000000:  # Reasonable seqno range
            print(f"Potential seqno at offset {i}: {seqno_candidate}")
    
except Exception as e:
    print(f"Error: {e}")
    
    # Just parse raw bytes
    print(f"\n=== Raw bytes analysis ===")
    for i in range(0, min(len(data_bytes), 32), 4):
        chunk = data_bytes[i:i+4]
        if len(chunk) == 4:
            value = int.from_bytes(chunk, 'big')
            print(f"Bytes {i}-{i+3}: {chunk.hex()} = {value}") 