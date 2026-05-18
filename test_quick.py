#!/usr/bin/env python3
"""Quick test script for OTC Compliance Engine"""

import json
from pathlib import Path

print("=" * 60)
print("OTC DERIVATIVES COMPLIANCE ENGINE - QUICK TEST")
print("=" * 60)

# Test 1: Load trade data
print("\n[TEST 1] Loading trade data...")
trade_file = Path("data/trades.json")
if trade_file.exists():
    with open(trade_file) as f:
        trades = json.load(f)
    print(f"✅ Loaded {len(trades)} trades from {trade_file}")
    print(f"   Sample: T001={trades[0]['trade_id']}, T026={[t['trade_id'] for t in trades if t['trade_id']=='T026'][0]}")
else:
    print(f"❌ File not found: {trade_file}")

# Test 2: Import modules
print("\n[TEST 2] Testing module imports...")
try:
    from src.schemas import ParsedTrade, ComplianceResult
    from src.validators import validate_lei, validate_iso8601_utc_timestamp
    from src.module1_parser import parse_trade
    from src.module2_upi_lookup import lookup_upi
    from src.module3_compliance import check_cftc_compliance
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")

# Test 3: Validate a LEI
print("\n[TEST 3] Testing LEI validator...")
lei = "5493001KJTIIGC8Y1R12"
valid, msg = validate_lei(lei)
print(f"   LEI {lei}: {'✅ VALID' if valid else f'❌ INVALID - {msg}'}")

# Test 4: Parse one trade
print("\n[TEST 4] Parsing first trade (T001)...")
try:
    t1 = trades[0]
    pt1 = parse_trade(t1)
    print(f"✅ Parsed {pt1.trade_id}")
    print(f"   Asset Class: {pt1.asset_class}")
    print(f"   Classification: {pt1.classification_flag}")
    print(f"   Status: {pt1.parse_status}")
    if pt1.parse_errors:
        print(f"   Errors: {pt1.parse_errors}")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check EventContract (T026)
print("\n[TEST 5] Checking EventContract (T026)...")
try:
    t26 = [t for t in trades if t['trade_id'] == 'T026'][0]
    pt26 = parse_trade(t26)
    print(f"✅ Parsed {pt26.trade_id}")
    print(f"   Asset Class: {pt26.asset_class}")
    print(f"   Classification: {pt26.classification_flag}")
    print(f"   Platform Type: {t26.get('platform_type', 'N/A')}")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "=" * 60)
print("QUICK TEST COMPLETE")
print("=" * 60)
