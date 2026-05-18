#!/usr/bin/env python3
"""Quick diagnostic test"""

import sys
print("Python version:", sys.version)

print("\n[TEST 1] Loading trade data...")
import json
with open("data/trades.json") as f:
    trades = json.load(f)
print(f"✅ Loaded {len(trades)} trades")

print("\n[TEST 2] Importing schemas...")
from src.schemas import ParsedTrade
print("✅ Schemas imported")

print("\n[TEST 3] Importing validators...")
from src.validators import validate_lei
print("✅ Validators imported")

print("\n[TEST 4] Testing LEI validation...")
valid, msg = validate_lei("5493001KJTIIGC8Y1R12")
print(f"✅ LEI validation works: {valid}")

print("\n[TEST 5] Importing module1...")
from src.module1_parser import parse_trade
print("✅ Module 1 imported")

print("\n[TEST 6] Parsing one trade...")
t1 = trades[0]
pt1 = parse_trade(t1)
print(f"✅ Parsed {pt1.trade_id}: {pt1.parse_status}")

print("\n✅ ALL TESTS PASSED!")
