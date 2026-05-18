#!/usr/bin/env python3
"""Add 5 additional custom trades to trades.json"""

import json
from pathlib import Path

# Load existing trades
with open("data/trades.json") as f:
    trades = json.load(f)

print(f"Loaded {len(trades)} existing trades")

# Create 5 new trades
new_trades = [
# T029: Rates.Swap.Basis - Additional interest rate basis swap (CLEAN - no errors)
    {
        "trade_id": "T029",
        "asset_class": "Rates",
        "instrument_type": "Swap",
        "use_case": "Basis",
        "reporting_counterparty_lei": "5493001KJTIIGC8Y1R12",
        "other_counterparty_lei": "2138002TXD6KSZ3V5X27",
        "uti": "5493001KJTIIGC8Y1R1220260801BAS0001",
        "execution_timestamp": "2026-08-01T10:00:00Z",
        "effective_date": "2026-08-05",
        "maturity_date": "2031-08-05",
        "notional_currency": "JPY",
        "notional_amount": 10000000000,
        "reference_rate_leg1": "JPY-LIBOR-BBA",
        "reference_rate_leg2": "JPY-TONA-OIS-COMPOUND",
        "cleared": False,
        "action_type": "NEW",
        "collateral_portfolio_code": "PORT-M789",
        "initial_margin_posted": 450000,
        "variation_margin_posted": 0
    },
    
    # T030: Credit.Swap.Sovereign - INTENTIONAL ERROR: missing other_counterparty_lei
    {
        "trade_id": "T030",
        "asset_class": "Credit",
        "instrument_type": "Swap",
        "use_case": "Sovereign",
        "reporting_counterparty_lei": "VGRQXHF3J8VDLUA7XE92",
        "other_counterparty_lei": None,  # ❌ INTENTIONAL ERROR: required field is null
        "uti": "VGRQXHF3J8VDLUA7XE9220260901SOV0002",
        "execution_timestamp": "2026-09-01T14:30:00Z",
        "effective_date": "2026-09-05",
        "maturity_date": "2031-09-05",
        "notional_currency": "CHF",
        "notional_amount": 50000000,
        "cleared": False,
        "action_type": "NEW"
    },
    
    # T031: Equity.Option.SingleName_Call - Additional equity option (CLEAN)
    {
        "trade_id": "T031",
        "asset_class": "Equity",
        "instrument_type": "Option",
        "use_case": "SingleName_Call",
        "reporting_counterparty_lei": "1VUV7VQFKUOQSJ21A208",
        "other_counterparty_lei": "4R3ZURLYISNNNMHMK608",
        "uti": "1VUV7VQFKUOQSJ21A20820261001EQO0001",
        "execution_timestamp": "2026-10-01T11:00:00Z",
        "effective_date": "2026-10-05",
        "maturity_date": "2027-01-05",
        "notional_currency": "USD",
        "notional_amount": 12000000,
        "cleared": False,
        "action_type": "NEW"
    },
    
    # T032: EventContract - Sports outcome (INTENTIONAL ERROR: invalid currency code)
    {
        "trade_id": "T032",
        "asset_class": "EventContract",
        "instrument_type": "BinaryEventContract",
        "use_case": "SportsOutcome",
        "description": "Binary event contract on sports championship outcome.",
        "reporting_counterparty_lei": "9695009AXSRNHZE85Y20",
        "other_counterparty_lei": None,
        "uti": "9695009AXSRNHZE85Y2020261015SPO0001",
        "execution_timestamp": "2026-10-15T12:00:00Z",
        "settlement_date": "2026-11-15",
        "notional_currency": "INVALID_SPORTS",  # ❌ INTENTIONAL ERROR: invalid currency
        "number_of_contracts": 150000,
        "contract_size": 1.00,
        "notional_amount": 150000,
        "entry_price": 0.65,
        "platform": "Kalshi",
        "platform_type": "CFTC_REGULATED_DCM",
        "cleared": True,
        "action_type": "NEW"
    },
    
    # T033: Commodities.Forward - Agricultural commodity forward (CLEAN)
    {
        "trade_id": "T033",
        "asset_class": "Commodities",
        "instrument_type": "Forward",
        "use_case": "AgricultureFuture",
        "reporting_counterparty_lei": "5299000J2N45DDNE4Y28",
        "other_counterparty_lei": "9695009AXSRNHZE85Y20",
        "uti": "5299000J2N45DDNE4Y2820261101AGR0001",
        "execution_timestamp": "2026-11-01T09:30:00Z",
        "effective_date": "2026-11-05",
        "maturity_date": "2027-03-05",
        "notional_currency": "USD",
        "notional_amount": 500000,
        "cleared": False,
        "action_type": "NEW"
    }
]

# Append new trades
trades.extend(new_trades)

# Save
with open("data/trades.json", "w") as f:
    json.dump(trades, f, indent=2)

print(f"✅ Added 5 new trades")
print(f"   T029: Rates.Swap.Basis (CLEAN)")
print(f"   T030: Credit.Swap.Sovereign (ERROR: missing other_counterparty_lei)")
print(f"   T031: Equity.Option.SingleName_Call (CLEAN)")
print(f"   T032: EventContract.SportsOutcome (ERROR: invalid currency)")
print(f"   T033: Commodities.Forward.Agriculture (CLEAN)")
print(f"\n✅ Total trades now: {len(trades)}")
