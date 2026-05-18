"""
Module 3: Multi-Jurisdictional Compliance Checker
Validates trades against CFTC and EMIR regulatory requirements
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from src.schemas import ParsedTrade, ComplianceResult, ComplianceStatus
from src.validators import validate_lei, validate_uti, is_valid_iso_currency


# ============================================================================
# FIELD REQUIREMENTS BY JURISDICTION
# ============================================================================

# Common Data Elements (CDE) - Required by all regimes
COMMON_REQUIRED_FIELDS = [
    'uti',
    'upi',  # Not in all trades, but required if reportable
    'reporting_counterparty_lei',
    'other_counterparty_lei',
    'execution_timestamp',
    'effective_date',
    'maturity_date',
    'notional_currency',
    'notional_amount',
    'action_type',
    'cleared',
]

# CFTC-specific (USA)
CFTC_SPECIFIC_FIELDS = [
    'platform',
]

# EMIR-specific (EU) - includes margin fields
EMIR_SPECIFIC_FIELDS = [
    'platform',
    'collateral_portfolio_code',  # Required by EMIR (can be null if not cleared)
    'initial_margin_posted',       # Required by EMIR (0 is acceptable, null is not)
    'variation_margin_posted',     # Required by EMIR
]

# MAS-specific (Singapore)
MAS_SPECIFIC_FIELDS = [
    'platform',
    'collateral_portfolio_code',
    'initial_margin_posted',
    'variation_margin_posted',
]


# ============================================================================
# COMPLIANCE LOGIC
# ============================================================================

def check_field_presence(trade: Dict[str, Any], field_name: str) -> Tuple[bool, Any]:
    """
    Check if a field is present and not null
    
    Returns:
        (is_valid, value)
    """
    value = trade.get(field_name)
    
    # Special handling for numeric 0 values (valid, not null)
    if field_name in ['initial_margin_posted', 'variation_margin_posted']:
        if value is None:
            return False, value
        # 0 is acceptable
        return True, value
    
    # For other fields, null is invalid
    if value is None:
        return False, value
    
    return True, value


def validate_lei_field(trade: Dict[str, Any], field_name: str) -> Tuple[bool, str]:
    """
    Validate LEI field in trade
    
    Returns:
        (is_valid, error_message)
    """
    lei = trade.get(field_name)
    
    if lei is None:
        return False, f"{field_name} is null"
    
    lei_valid, lei_error = validate_lei(lei)
    if not lei_valid:
        return False, lei_error
    
    return True, ""


def validate_uti_field(trade: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate UTI field in trade against reporting LEI
    
    Returns:
        (is_valid, error_message)
    """
    uti = trade.get('uti')
    reporting_lei = trade.get('reporting_counterparty_lei')
    
    if uti is None:
        return False, "uti is null"
    
    uti_valid, uti_error = validate_uti(uti, reporting_lei)
    if not uti_valid:
        return False, uti_error
    
    return True, ""


def check_cftc_compliance(
    parsed_trade: ParsedTrade,
    upi_result: Dict[str, Any],
    raw_trade: Dict[str, Any]
) -> ComplianceResult:
    """
    Check CFTC compliance for a trade
    
    Rules:
    - EventContract on CFTC DCM → CONDITIONAL (awaiting ANPR classification)
    - EventContract not on CFTC DCM → NOT_APPLICABLE
    - Conventional derivative → validate all fields
    
    Args:
        parsed_trade: Module 1 output
        upi_result: Module 2 output
        raw_trade: Original trade data
    
    Returns:
        ComplianceResult with CFTC status
    """
    
    trade_id = parsed_trade.trade_id
    classification_flag = parsed_trade.classification_flag
    
    # ========================================================================
    # SPECIAL HANDLING: NOVEL INSTRUMENTS (T026-T028)
    # ========================================================================
    
    if classification_flag == 'NOVEL_INSTRUMENT_NO_TAXONOMY':
        # Check if it's on a CFTC-regulated DCM (e.g., Kalshi)
        platform_type = raw_trade.get('platform_type', '')
        
        if platform_type == 'CFTC_REGULATED_DCM':
            # CFTC DCM → CONDITIONAL (awaiting ANPR 91 FR 12516)
            status = ComplianceStatus.CONDITIONAL.value
            note = (
                "EventContract on CFTC-regulated DCM (Kalshi). "
                "Classification pending CFTC ANPR 91 FR 12516 (Prediction Markets). "
                "Currently flagged CONDITIONAL pending rulemaking."
            )
        else:
            # Not CFTC regulated → NOT_APPLICABLE
            status = ComplianceStatus.NOT_APPLICABLE.value
            note = (
                "EventContract not on CFTC-regulated platform. "
                "Not within current scope of CFTC reporting requirements."
            )
        
        return ComplianceResult(
            trade_id=trade_id,
            asset_class=parsed_trade.asset_class,
            instrument_type=parsed_trade.instrument_type,
            use_case=parsed_trade.use_case,
            classification_flag=classification_flag,
            cftc_status=status,
            emir_status='N/A',  # Not evaluated for EMIR here
            cftc_notes=note,
        )
    
    # ========================================================================
    # CONVENTIONAL DERIVATIVES: VALIDATE ALL FIELDS
    # ========================================================================
    
    field_validations: Dict[str, Dict[str, Any]] = {}
    errors = []
    
    # === Validate core LEI and UTI ===
    
    # Reporting counterparty LEI
    lei_rep_valid, lei_rep_error = validate_lei_field(raw_trade, 'reporting_counterparty_lei')
    field_validations['reporting_counterparty_lei'] = {
        'value': raw_trade.get('reporting_counterparty_lei'),
        'valid': lei_rep_valid,
        'error': lei_rep_error if lei_rep_error else None,
    }
    if not lei_rep_valid:
        errors.append(lei_rep_error)
    
    # Other counterparty LEI
    lei_other_valid, lei_other_error = validate_lei_field(raw_trade, 'other_counterparty_lei')
    field_validations['other_counterparty_lei'] = {
        'value': raw_trade.get('other_counterparty_lei'),
        'valid': lei_other_valid,
        'error': lei_other_error if lei_other_error else None,
    }
    if not lei_other_valid:
        errors.append(lei_other_error)
    
    # UTI
    uti_valid, uti_error = validate_uti_field(raw_trade)
    field_validations['uti'] = {
        'value': raw_trade.get('uti'),
        'valid': uti_valid,
        'error': uti_error if uti_error else None,
    }
    if not uti_valid:
        errors.append(uti_error)
    
    # === Validate other common fields ===
    
    # execution_timestamp
    ts_present, ts_value = check_field_presence(raw_trade, 'execution_timestamp')
    field_validations['execution_timestamp'] = {
        'value': ts_value,
        'valid': ts_present and ts_value in parsed_trade.classified_fields.values(),
        'error': None if ts_present else 'execution_timestamp is null',
    }
    if not ts_present:
        errors.append('execution_timestamp is null')
    
    # effective_date
    ed_present, ed_value = check_field_presence(raw_trade, 'effective_date')
    field_validations['effective_date'] = {
        'value': ed_value,
        'valid': ed_present and ed_value in parsed_trade.classified_fields.values(),
        'error': None if ed_present else 'effective_date is null',
    }
    if not ed_present:
        errors.append('effective_date is null')
    
    # maturity_date
    md_present, md_value = check_field_presence(raw_trade, 'maturity_date')
    field_validations['maturity_date'] = {
        'value': md_value,
        'valid': md_present and md_value in parsed_trade.classified_fields.values(),
        'error': None if md_present else 'maturity_date is null',
    }
    if not md_present:
        errors.append('maturity_date is null')
    
    # notional_currency (ISO 4217)
    currency = raw_trade.get('notional_currency')
    currency_valid = is_valid_iso_currency(currency)
    field_validations['notional_currency'] = {
        'value': currency,
        'valid': currency_valid,
        'error': None if currency_valid else f'Invalid currency code: {currency}',
    }
    if not currency_valid:
        errors.append(f'notional_currency: Invalid currency code: {currency}')
    
    # notional_amount
    amount = raw_trade.get('notional_amount')
    amount_valid = amount is not None and isinstance(amount, (int, float)) and amount >= 0
    field_validations['notional_amount'] = {
        'value': amount,
        'valid': amount_valid,
        'error': None if amount_valid else f'notional_amount must be non-negative number, got {amount}',
    }
    if not amount_valid:
        errors.append(f'notional_amount: {amount} is invalid')
    
    # action_type
    action_type = raw_trade.get('action_type')
    action_valid = action_type in {'NEW', 'MODIFY', 'CANCEL', 'CORRECT', 'TERMINATE'}
    field_validations['action_type'] = {
        'value': action_type,
        'valid': action_valid,
        'error': None if action_valid else f'action_type {action_type} not in valid enum',
    }
    if not action_valid:
        errors.append(f'action_type: {action_type} not in valid enum')
    
    # cleared
    cleared = raw_trade.get('cleared')
    cleared_valid = cleared is not None and isinstance(cleared, bool)
    field_validations['cleared'] = {
        'value': cleared,
        'valid': cleared_valid,
        'error': None if cleared_valid else 'cleared must be boolean',
    }
    if not cleared_valid:
        errors.append('cleared: must be boolean')
    
    # === Determine status ===
    
    if len(errors) == 0:
        status = ComplianceStatus.COMPLIANT.value
    else:
        status = ComplianceStatus.NONCOMPLIANT.value
    
    return ComplianceResult(
        trade_id=trade_id,
        asset_class=parsed_trade.asset_class,
        instrument_type=parsed_trade.instrument_type,
        use_case=parsed_trade.use_case,
        classification_flag=classification_flag,
        cftc_status=status,
        emir_status='N/A',
        cftc_field_validations=field_validations,
        cftc_notes='; '.join(errors) if errors else None,
    )


def check_emir_compliance(
    parsed_trade: ParsedTrade,
    upi_result: Dict[str, Any],
    raw_trade: Dict[str, Any]
) -> ComplianceResult:
    """
    Check EMIR (EU) compliance for a trade
    
    Rules:
    - EventContract → NOT_APPLICABLE (GlüStV 2021 gambling classification in EU)
    - Conventional derivative → validate all fields including margin fields
    
    Args:
        parsed_trade: Module 1 output
        upi_result: Module 2 output
        raw_trade: Original trade data
    
    Returns:
        ComplianceResult with EMIR status
    """
    
    trade_id = parsed_trade.trade_id
    classification_flag = parsed_trade.classification_flag
    
    # ========================================================================
    # SPECIAL HANDLING: NOVEL INSTRUMENTS (T026-T028)
    # ========================================================================
    
    if classification_flag == 'NOVEL_INSTRUMENT_NO_TAXONOMY':
        # All event contracts → NOT_APPLICABLE under EMIR
        # Reason: Germany's Glücksspielstaatsvertrag (GlüStV 2021) and equivalent
        # national gambling laws classify prediction contracts as illegal gambling
        
        status = ComplianceStatus.NOT_APPLICABLE.value
        note = (
            "EventContract classified as illegal gambling under EU national law "
            "(Germany: Glücksspielstaatsvertrag, GlüStV 2021). "
            "Not within scope of EMIR derivatives reporting."
        )
        
        return ComplianceResult(
            trade_id=trade_id,
            asset_class=parsed_trade.asset_class,
            instrument_type=parsed_trade.instrument_type,
            use_case=parsed_trade.use_case,
            classification_flag=classification_flag,
            cftc_status='N/A',
            emir_status=status,
            emir_notes=note,
        )
    
    # ========================================================================
    # CONVENTIONAL DERIVATIVES: VALIDATE ALL FIELDS + MARGIN FIELDS
    # ========================================================================
    
    field_validations: Dict[str, Dict[str, Any]] = {}
    errors = []
    
    # === Validate core LEI and UTI (same as CFTC) ===
    
    lei_rep_valid, lei_rep_error = validate_lei_field(raw_trade, 'reporting_counterparty_lei')
    field_validations['reporting_counterparty_lei'] = {
        'value': raw_trade.get('reporting_counterparty_lei'),
        'valid': lei_rep_valid,
        'error': lei_rep_error if lei_rep_error else None,
    }
    if not lei_rep_valid:
        errors.append(lei_rep_error)
    
    lei_other_valid, lei_other_error = validate_lei_field(raw_trade, 'other_counterparty_lei')
    field_validations['other_counterparty_lei'] = {
        'value': raw_trade.get('other_counterparty_lei'),
        'valid': lei_other_valid,
        'error': lei_other_error if lei_other_error else None,
    }
    if not lei_other_valid:
        errors.append(lei_other_error)
    
    uti_valid, uti_error = validate_uti_field(raw_trade)
    field_validations['uti'] = {
        'value': raw_trade.get('uti'),
        'valid': uti_valid,
        'error': uti_error if uti_error else None,
    }
    if not uti_valid:
        errors.append(uti_error)
    
    # === Validate other common fields ===
    
    ts_present, ts_value = check_field_presence(raw_trade, 'execution_timestamp')
    field_validations['execution_timestamp'] = {
        'value': ts_value,
        'valid': ts_present,
        'error': None if ts_present else 'execution_timestamp is null',
    }
    if not ts_present:
        errors.append('execution_timestamp is null')
    
    ed_present, ed_value = check_field_presence(raw_trade, 'effective_date')
    field_validations['effective_date'] = {
        'value': ed_value,
        'valid': ed_present,
        'error': None if ed_present else 'effective_date is null',
    }
    if not ed_present:
        errors.append('effective_date is null')
    
    md_present, md_value = check_field_presence(raw_trade, 'maturity_date')
    field_validations['maturity_date'] = {
        'value': md_value,
        'valid': md_present,
        'error': None if md_present else 'maturity_date is null',
    }
    if not md_present:
        errors.append('maturity_date is null')
    
    currency = raw_trade.get('notional_currency')
    currency_valid = is_valid_iso_currency(currency)
    field_validations['notional_currency'] = {
        'value': currency,
        'valid': currency_valid,
        'error': None if currency_valid else f'Invalid currency code: {currency}',
    }
    if not currency_valid:
        errors.append(f'notional_currency: Invalid currency code: {currency}')
    
    amount = raw_trade.get('notional_amount')
    amount_valid = amount is not None and isinstance(amount, (int, float)) and amount >= 0
    field_validations['notional_amount'] = {
        'value': amount,
        'valid': amount_valid,
        'error': None if amount_valid else f'notional_amount must be non-negative number',
    }
    if not amount_valid:
        errors.append(f'notional_amount: {amount} is invalid')
    
    action_type = raw_trade.get('action_type')
    action_valid = action_type in {'NEW', 'MODIFY', 'CANCEL', 'CORRECT', 'TERMINATE'}
    field_validations['action_type'] = {
        'value': action_type,
        'valid': action_valid,
        'error': None if action_valid else f'action_type {action_type} not in valid enum',
    }
    if not action_valid:
        errors.append(f'action_type: {action_type} not in valid enum')
    
    cleared = raw_trade.get('cleared')
    cleared_valid = cleared is not None and isinstance(cleared, bool)
    field_validations['cleared'] = {
        'value': cleared,
        'valid': cleared_valid,
        'error': None if cleared_valid else 'cleared must be boolean',
    }
    if not cleared_valid:
        errors.append('cleared: must be boolean')
    
    # === EMIR-SPECIFIC: Margin fields (required) ===
    
    # collateral_portfolio_code (required, can be null if not reportable)
    # For EMIR: if cleared, must have collateral_portfolio_code
    coll_code = raw_trade.get('collateral_portfolio_code')
    coll_valid = coll_code is not None  # Must not be null
    field_validations['collateral_portfolio_code'] = {
        'value': coll_code,
        'valid': coll_valid,
        'error': None if coll_valid else 'collateral_portfolio_code is required by EMIR',
    }
    if not coll_valid:
        errors.append('collateral_portfolio_code is required by EMIR')
    
    # initial_margin_posted (required, 0 is acceptable)
    init_margin = raw_trade.get('initial_margin_posted')
    init_valid = init_margin is not None  # 0 is acceptable, null is not
    field_validations['initial_margin_posted'] = {
        'value': init_margin,
        'valid': init_valid,
        'error': None if init_valid else 'initial_margin_posted is required by EMIR (0 is acceptable)',
    }
    if not init_valid:
        errors.append('initial_margin_posted is required by EMIR')
    
    # variation_margin_posted (required, 0 is acceptable)
    var_margin = raw_trade.get('variation_margin_posted')
    var_valid = var_margin is not None  # 0 is acceptable, null is not
    field_validations['variation_margin_posted'] = {
        'value': var_margin,
        'valid': var_valid,
        'error': None if var_valid else 'variation_margin_posted is required by EMIR (0 is acceptable)',
    }
    if not var_valid:
        errors.append('variation_margin_posted is required by EMIR')
    
    # === Determine status ===
    
    if len(errors) == 0:
        status = ComplianceStatus.COMPLIANT.value
    else:
        status = ComplianceStatus.NONCOMPLIANT.value
    
    return ComplianceResult(
        trade_id=trade_id,
        asset_class=parsed_trade.asset_class,
        instrument_type=parsed_trade.instrument_type,
        use_case=parsed_trade.use_case,
        classification_flag=classification_flag,
        cftc_status='N/A',
        emir_status=status,
        emir_field_validations=field_validations,
        emir_notes='; '.join(errors) if errors else None,
    )


def check_compliance_batch(
    parsed_trades: List[ParsedTrade],
    upi_results: List[Dict[str, Any]],
    raw_trades: List[Dict[str, Any]],
    regimes: List[str]
) -> List[Dict[str, Any]]:
    """
    Check compliance for all trades against specified regimes
    
    Args:
        parsed_trades: Module 1 outputs
        upi_results: Module 2 outputs
        raw_trades: Original trade records
        regimes: List of regimes to check (e.g., ['CFTC', 'EMIR'])
    
    Returns:
        List of compliance results (as dicts for JSON serialization)
    """
    
    results = []
    
    # Create index for quick lookup
    upi_by_trade = {r['trade_id']: r for r in upi_results}
    raw_by_trade = {t['trade_id']: t for t in raw_trades}
    
    for parsed_trade in parsed_trades:
        trade_id = parsed_trade.trade_id
        upi_result = upi_by_trade.get(trade_id, {})
        raw_trade = raw_by_trade.get(trade_id, {})
        
        compliance_result = ComplianceResult(
            trade_id=trade_id,
            asset_class=parsed_trade.asset_class,
            instrument_type=parsed_trade.instrument_type,
            use_case=parsed_trade.use_case,
            classification_flag=parsed_trade.classification_flag,
            cftc_status='N/A',
            emir_status='N/A',
        )
        
        # Check CFTC
        if 'CFTC' in regimes:
            cftc_result = check_cftc_compliance(parsed_trade, upi_result, raw_trade)
            compliance_result.cftc_status = cftc_result.cftc_status
            compliance_result.cftc_field_validations = cftc_result.cftc_field_validations
            compliance_result.cftc_notes = cftc_result.cftc_notes
        
        # Check EMIR
        if 'EMIR' in regimes:
            emir_result = check_emir_compliance(parsed_trade, upi_result, raw_trade)
            compliance_result.emir_status = emir_result.emir_status
            compliance_result.emir_field_validations = emir_result.emir_field_validations
            compliance_result.emir_notes = emir_result.emir_notes
        
        results.append(compliance_result.to_dict())
    
    return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Module 3: Compliance Checker')
    parser.add_argument('--trades', required=True, help='Original trades.json')
    parser.add_argument('--parsed', required=True, help='Module 1 parsed_trades.json')
    parser.add_argument('--upi', required=True, help='Module 2 upi_lookup.json')
    parser.add_argument('--output', required=True, help='Output compliance_report.json')
    parser.add_argument('--regimes', default='CFTC,EMIR', help='Comma-separated regimes')
    
    args = parser.parse_args()
    
    regimes = [r.strip() for r in args.regimes.split(',')]
    
    # Load inputs
    with open(args.trades) as f:
        raw_trades = json.load(f)
    with open(args.parsed) as f:
        parsed_data = json.load(f)
        parsed_trades = [ParsedTrade(**t) for t in parsed_data]
    with open(args.upi) as f:
        upi_results = json.load(f)
    
    # Check compliance
    print(f"Checking compliance for {len(parsed_trades)} trades...")
    compliance_results = check_compliance_batch(parsed_trades, upi_results, raw_trades, regimes)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(compliance_results, f, indent=2)
    
    print(f"\n✅ Module 3 Complete")
    print(f"   Output: {output_path}")
