"""
Module 1: Trade Parser & Instrument Classifier
Parses raw trade JSON and produces classified trade records
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from src.schemas import ParsedTrade, ParseStatus, ClassificationFlag
from src.validators import validate_iso8601_utc_timestamp, validate_date


# ============================================================================
# CONSTANTS
# ============================================================================

CONVENTIONAL_ASSET_CLASSES = {'Rates', 'Credit', 'FX', 'Equity', 'Commodities'}
NOVEL_ASSET_CLASSES = {'EventContract'}

REQUIRED_FIELDS_BASE = [
    'trade_id',
    'asset_class',
    'instrument_type',
    'use_case',
]

REQUIRED_FIELDS_CONVENTIONAL = [
    'execution_timestamp',
    'effective_date',
    'maturity_date',
]


# ============================================================================
# CLASSIFICATION LOGIC
# ============================================================================

def classify_instrument(trade: Dict[str, Any]) -> str:
    """
    Determine the regulatory taxonomy classification flag for a trade
    
    Returns:
        CONVENTIONAL_DERIVATIVE - asset class present in ANNA-DSB library
        NOVEL_INSTRUMENT_NO_TAXONOMY - asset class outside library (e.g., EventContract)
        CLASSIFICATION_AMBIGUOUS - missing or contradictory fields
    """
    
    asset_class = trade.get("asset_class")
    
    # Check if asset class exists
    if asset_class is None:
        return ClassificationFlag.CLASSIFICATION_AMBIGUOUS.value
    
    # Check if conventional
    if asset_class in CONVENTIONAL_ASSET_CLASSES:
        return ClassificationFlag.CONVENTIONAL_DERIVATIVE.value
    
    # Check if novel
    if asset_class in NOVEL_ASSET_CLASSES:
        return ClassificationFlag.NOVEL_INSTRUMENT_NO_TAXONOMY.value
    
    # Unknown asset class
    return ClassificationFlag.CLASSIFICATION_AMBIGUOUS.value


# ============================================================================
# PARSING & VALIDATION
# ============================================================================

def parse_trade(trade: Dict[str, Any]) -> ParsedTrade:
    """
    Parse a single raw trade record
    
    Steps:
    1. Extract asset_class, instrument_type, use_case
    2. Call classify_instrument()
    3. Validate execution_timestamp (ISO 8601 UTC required)
    4. Validate effective_date and maturity_date (YYYY-MM-DD)
    5. Collect all errors; set parse_status
    
    Returns:
        ParsedTrade with all fields populated
    """
    
    errors: List[str] = []
    
    # ========================================================================
    # STEP 1: Extract core fields
    # ========================================================================
    
    trade_id = trade.get('trade_id', 'UNKNOWN')
    asset_class = trade.get('asset_class')
    instrument_type = trade.get('instrument_type')
    use_case = trade.get('use_case')
    
    # ========================================================================
    # STEP 2: Classify instrument
    # ========================================================================
    
    classification_flag = classify_instrument(trade)
    
    # ========================================================================
    # STEP 3: Validate execution_timestamp
    # ========================================================================
    
    execution_timestamp = trade.get('execution_timestamp')
    if execution_timestamp is None:
        errors.append("execution_timestamp is null")
    else:
        ts_valid, ts_error = validate_iso8601_utc_timestamp(execution_timestamp)
        if not ts_valid:
            errors.append(f"execution_timestamp: {ts_error}")
    
    # ========================================================================
    # STEP 4: Validate effective_date
    # ========================================================================
    
    effective_date = trade.get('effective_date')
    if effective_date is None:
        errors.append("effective_date is null")
    else:
        ed_valid, ed_error = validate_date(effective_date)
        if not ed_valid:
            errors.append(f"effective_date: {ed_error}")
    
    # ========================================================================
    # STEP 5: Validate maturity_date (or expiry_date for options)
    # ========================================================================
    
    maturity_date = trade.get('maturity_date')
    if maturity_date is None:
        errors.append("maturity_date is null")
    else:
        md_valid, md_error = validate_date(maturity_date)
        if not md_valid:
            errors.append(f"maturity_date: {md_error}")
    
    # ========================================================================
    # STEP 6: Extract classified fields (key data for downstream modules)
    # ========================================================================
    
    classified_fields = {
        'notional_currency': trade.get('notional_currency'),
        'notional_amount': trade.get('notional_amount'),
        'cleared': trade.get('cleared'),
        'uti': trade.get('uti'),
        'execution_timestamp': execution_timestamp,
        'effective_date': effective_date,
        'maturity_date': maturity_date,
        'reference_rate': trade.get('reference_rate'),
        'reference_rate_leg1': trade.get('reference_rate_leg1'),
        'reference_rate_leg2': trade.get('reference_rate_leg2'),
        'reference_rate_term_value': trade.get('reference_rate_term_value'),
        'reference_rate_term_unit': trade.get('reference_rate_term_unit'),
        'delivery_type': trade.get('delivery_type'),
        'debt_seniority': trade.get('debt_seniority'),
        'platform': trade.get('platform'),
    }
    
    # ========================================================================
    # STEP 7: Determine parse_status
    # ========================================================================
    
    if len(errors) == 0:
        parse_status = ParseStatus.SUCCESS.value
    elif asset_class is None or instrument_type is None:
        # Missing core classification fields
        parse_status = ParseStatus.FAILED.value
    else:
        # Some errors but core fields present
        parse_status = ParseStatus.PARTIAL.value
    
    # ========================================================================
    # BUILD RESULT
    # ========================================================================
    
    return ParsedTrade(
        trade_id=trade_id,
        parse_status=parse_status,
        asset_class=asset_class,
        instrument_type=instrument_type,
        use_case=use_case,
        classification_flag=classification_flag,
        parse_errors=errors,
        classified_fields=classified_fields,
    )


def parse_trades(raw_trades: List[Dict[str, Any]]) -> List[ParsedTrade]:
    """
    Parse all trades in batch
    
    Args:
        raw_trades: List of raw trade dictionaries from JSON
    
    Returns:
        List of ParsedTrade objects
    """
    
    parsed_trades = []
    
    for raw_trade in raw_trades:
        try:
            parsed_trade = parse_trade(raw_trade)
            parsed_trades.append(parsed_trade)
        except Exception as e:
            # If parsing fails completely, create error record
            trade_id = raw_trade.get('trade_id', 'UNKNOWN')
            parsed_trade = ParsedTrade(
                trade_id=trade_id,
                parse_status=ParseStatus.FAILED.value,
                asset_class=None,
                instrument_type=None,
                use_case=None,
                classification_flag=ClassificationFlag.CLASSIFICATION_AMBIGUOUS.value,
                parse_errors=[f"Exception during parsing: {str(e)}"],
                classified_fields={},
            )
            parsed_trades.append(parsed_trade)
    
    return parsed_trades


# ============================================================================
# JSON SERIALIZATION
# ============================================================================

def serialize_parsed_trades(parsed_trades: List[ParsedTrade]) -> str:
    """
    Serialize parsed trades to JSON
    
    Args:
        parsed_trades: List of ParsedTrade objects
    
    Returns:
        JSON string
    """
    
    data = [trade.to_dict() for trade in parsed_trades]
    return json.dumps(data, indent=2, default=str)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Module 1: Trade Parser')
    parser.add_argument('--input', required=True, help='Input trades.json file')
    parser.add_argument('--output', required=True, help='Output parsed_trades.json file')
    
    args = parser.parse_args()
    
    # Load input
    with open(args.input) as f:
        raw_trades = json.load(f)
    
    # Parse
    print(f"Parsing {len(raw_trades)} trades...")
    parsed_trades = parse_trades(raw_trades)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(serialize_parsed_trades(parsed_trades))
    
    # Summary
    success = sum(1 for t in parsed_trades if t.parse_status == 'SUCCESS')
    partial = sum(1 for t in parsed_trades if t.parse_status == 'PARTIAL')
    failed = sum(1 for t in parsed_trades if t.parse_status == 'FAILED')
    
    print(f"\n✅ Module 1 Complete")
    print(f"   SUCCESS: {success}/{len(parsed_trades)}")
    print(f"   PARTIAL: {partial}/{len(parsed_trades)}")
    print(f"   FAILED: {failed}/{len(parsed_trades)}")
    print(f"   Output: {output_path}")
