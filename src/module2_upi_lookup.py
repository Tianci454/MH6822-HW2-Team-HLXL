"""
Module 2: UPI Lookup Engine
Matches trade records to ANNA-DSB product definition templates
and validates attributes against codesets
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from difflib import SequenceMatcher
import re
from dataclasses import dataclass, asdict


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class UpiLookupResult:
    """Result of UPI lookup for a single trade"""
    trade_id: str
    status: str  # FOUND | NO_PRODUCT_DEFINITION | NOT_FOUND | INVALID_ATTRIBUTES
    matched_template: Optional[str]
    upi_code: Optional[str]
    classification_note: Optional[str]
    validation_errors: List[str]
    warnings: List[str]


# ============================================================================
# GLOBAL CODESET CACHE
# ============================================================================

_CODESET_CACHE: Dict[str, Dict] = {}


def load_codeset(library_path: str, codeset_name: str) -> Dict[str, Any]:
    """
    Load and cache codeset from ANNA-DSB library
    Codesets are in: data/product_definitions/PROD/OTC-Products/codesets/
    """
    global _CODESET_CACHE
    
    if codeset_name in _CODESET_CACHE:
        return _CODESET_CACHE[codeset_name]
    
    codeset_path = Path(library_path) / "PROD" / "OTC-Products" / "codesets" / f"{codeset_name}.json"
    
    if not codeset_path.exists():
        return {}
    
    with open(codeset_path) as f:
        codeset_data = json.load(f)
    
    _CODESET_CACHE[codeset_name] = codeset_data
    return codeset_data


# ============================================================================
# TEMPLATE MATCHING: TWO-LAYER STRATEGY
# ============================================================================

def find_product_template(
    asset_class: str,
    instrument_type: str,
    use_case: str,
    library_path: str
) -> Tuple[Optional[Dict], Optional[str], float]:
    """
    Two-layer template matching strategy:
    
    Layer 1: EXACT MATCH
    - Look for file: {AssetClass}.{InstrumentType}.{UseCase}.UPI.V*.json
    
    Layer 2: HEURISTIC MATCH (if exact fails)
    - Use token overlap / edit distance algorithm
    - Returns template + heuristic_note + match_score
    
    Returns:
        (template_dict, matched_filename, match_score)
        where match_score: 1.0 = exact, < 1.0 = heuristic
    """
    
    lib_path = Path(library_path)
    asset_dir = lib_path / "PROD" / "OTC-Products" / "UPI" / asset_class
    
    if not asset_dir.exists():
        return None, None, 0.0
    
    # === LAYER 1: EXACT MATCH ===
    exact_pattern = f"{asset_class}.{instrument_type}.{use_case}.UPI.V*.json"
    exact_matches = list(asset_dir.glob(exact_pattern))
    
    if exact_matches:
        matched_file = exact_matches[0]
        with open(matched_file) as f:
            template = json.load(f)
        return template, matched_file.stem, 1.0
    
    # === LAYER 2: HEURISTIC MATCH ===
    all_templates = sorted(asset_dir.glob("*.UPI.V*.json"))

    best_match = None
    best_score = -1.0
    best_filename = None

    for template_file in all_templates:
        parts = template_file.stem.split('.')
        if len(parts) < 3:
            continue

        template_instrument = parts[1]
        template_use_case = parts[2]

        if template_instrument != instrument_type:
            continue

        use_case_sim = SequenceMatcher(None, use_case, template_use_case).ratio()

        if use_case_sim > best_score:
            best_score = use_case_sim
            best_match = template_file
            best_filename = template_file.stem

    if best_match:
        with open(best_match) as f:
            template = json.load(f)
        return template, best_filename, best_score
    
    return None, None, 0.0


# ============================================================================
# ATTRIBUTE VALIDATION
# ============================================================================

def validate_attributes(
    trade: Dict[str, Any],
    template: Dict[str, Any],
    library_path: str
) -> Tuple[List[str], List[str]]:
    """
    Validate trade attributes against template constraints
    
    Returns:
        (errors_list, warnings_list)
    """
    errors = []
    warnings = []
    
    # Get template attributes
    template_attrs = template.get('Attributes', {})
    
    if not template_attrs:
        # No attribute validation in template
        return errors, warnings
    
    # === 1. CURRENCY VALIDATION (ISO 4217) ===
    if 'NotionalCurrency' in template_attrs and 'notional_currency' in trade:
        currency = trade.get('notional_currency')
        iso_currencies = load_codeset(library_path, 'ISOCurrencyCode')
        
        # ISO currencies are keyed by code
        valid_currencies = set(iso_currencies.keys()) if iso_currencies else set()
        # Add special cases like XAU (gold)
        valid_currencies.update(['XAU', 'XAG', 'XPT', 'XPD'])
        
        if currency and currency not in valid_currencies:
            errors.append(f"Invalid currency code: {currency} (not in ISO 4217)")
    
    # === 2. REFERENCE RATE VALIDATION ===
    for rate_field in ['reference_rate', 'reference_rate_leg1', 'reference_rate_leg2']:
        if rate_field in trade and trade.get(rate_field):
            rate_code = trade[rate_field]
            
            rate_codeset = load_codeset(library_path, 'FpmlRatesReferenceRate')
            valid_rates = set(rate_codeset.keys()) if rate_codeset else set()
            
            if rate_code not in valid_rates:
                # Check for LIBOR (deprecated but still valid)
                if 'LIBOR' in rate_code:
                    warnings.append(
                        f"Field '{rate_field}': {rate_code} is a deprecated LIBOR code "
                        "(LIBOR ceased in June 2023). Legacy trades remain reportable but "
                        "migration to SOFR/SONIA recommended."
                    )
                else:
                    errors.append(
                        f"Field '{rate_field}': {rate_code} not in FpmlRatesReferenceRate codeset"
                    )
    
    # === 3. TERM UNIT VALIDATION ===
    for term_field in ['reference_rate_term_unit', 'reference_rate_term_leg1_unit', 
                       'reference_rate_term_leg2_unit']:
        if term_field in trade and trade.get(term_field):
            term_unit = trade[term_field]
            valid_units = {'DAYS', 'WEEK', 'MNTH', 'YEAR'}
            
            if term_unit not in valid_units:
                errors.append(
                    f"Field '{term_field}': {term_unit} not in enum {valid_units}"
                )
    
    # === 4. TERM VALUE VALIDATION ===
    for term_field in ['reference_rate_term_value', 'reference_rate_term_leg1_value',
                       'reference_rate_term_leg2_value']:
        if term_field in trade and trade.get(term_field) is not None:
            term_value = trade[term_field]
            
            # Term value constraints: -999 to 999, not 0
            if not isinstance(term_value, (int, float)):
                errors.append(f"Field '{term_field}': {term_value} is not numeric")
            elif term_value == 0:
                errors.append(f"Field '{term_field}': {term_value} cannot be 0")
            elif not (-999 <= term_value <= 999):
                errors.append(
                    f"Field '{term_field}': {term_value} outside range [-999, 999]"
                )
    
    # === 5. DELIVERY TYPE VALIDATION ===
    if 'delivery_type' in trade and trade.get('delivery_type'):
        delivery_type = trade['delivery_type']
        valid_delivery = {'CASH', 'PHYS', 'OPTL'}
        
        if delivery_type not in valid_delivery:
            errors.append(
                f"Field 'delivery_type': {delivery_type} not in enum {valid_delivery}"
            )
    
    # === 6. DEBT SENIORITY VALIDATION ===
    if 'debt_seniority' in trade and trade.get('debt_seniority'):
        seniority = trade['debt_seniority']
        valid_seniority = {'SNDB', 'SNSR', 'JUND', 'MEZZANINE'}
        
        if seniority not in valid_seniority:
            errors.append(
                f"Field 'debt_seniority': {seniority} not in enum {valid_seniority}"
            )
    
    return errors, warnings


# ============================================================================
# UPI CODE GENERATION (Mock)
# ============================================================================

def generate_upi_code(template_name: str, trade: Dict[str, Any]) -> str:
    """
    Generate a deterministic mock UPI code (12-char base32-like alphanumeric)
    
    In production, real UPIs are issued by ANNA-DSB live API.
    This mock is for demonstration purposes.
    
    Strategy: Hash template name + key trade attributes
    """
    import hashlib
    
    # Concatenate UPI-defining attributes (not notional amount, dates, or counterparties)
    key_attrs = [
        template_name,
        trade.get('notional_currency', ''),
        trade.get('reference_rate', ''),
        trade.get('reference_rate_term_value', ''),
        trade.get('reference_rate_term_unit', ''),
        trade.get('instrument_type', ''),
        trade.get('use_case', ''),
    ]
    
    key_string = '|'.join(str(v) for v in key_attrs)
    
    # Hash and convert to base32-like characters
    hash_obj = hashlib.sha256(key_string.encode())
    hash_hex = hash_obj.hexdigest()[:12]  # First 12 hex chars
    
    # Convert to alphanumeric (0-9, A-V for base32-like)
    base32_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    upi_code = ''
    for i, char in enumerate(hash_hex):
        hex_val = int(char, 16)
        upi_code += base32_chars[hex_val % len(base32_chars)]
    
    return upi_code[:20]  # Real UPIs are 20 chars


# ============================================================================
# MAIN LOOKUP FUNCTION
# ============================================================================

def lookup_upi(parsed_trade: Dict[str, Any], library_path: str) -> Dict[str, Any]:
    """
    Full UPI lookup workflow for a single trade
    
    Decision tree:
    1. Is this a NOVEL instrument (T026-T028)?
       → NO_PRODUCT_DEFINITION (with classification_note)
    
    2. Find matching template
       a. Exact match? → Continue
       b. Heuristic match? → Continue (with note)
       c. No match? → NOT_FOUND
    
    3. Validate attributes against template
       a. Errors found? → INVALID_ATTRIBUTES
       b. Clean? → FOUND
    """
    
    trade_id = parsed_trade['trade_id']
    classification_flag = parsed_trade.get('classification_flag')
    
    # === STEP 1: Check if NOVEL ===
    if classification_flag == 'NOVEL_INSTRUMENT_NO_TAXONOMY':
        asset_class = parsed_trade.get('asset_class', 'Unknown')
        instrument_type = parsed_trade.get('instrument_type', 'Unknown')
        
        return {
            'trade_id': trade_id,
            'status': 'NO_PRODUCT_DEFINITION',
            'matched_template': None,
            'upi_code': None,
            'classification_note': (
                f"Instrument type '{instrument_type}' under asset class '{asset_class}' "
                f"has no product definition in the ANNA-DSB UPI library. This reflects the "
                f"current regulatory classification of prediction and event contracts as outside "
                f"the OTC derivatives taxonomy in most jurisdictions. Refer to Module 4 for "
                f"classification analysis."
            ),
            'validation_errors': [],
            'warnings': [],
        }
    
    # === STEP 2: Find Template ===
    asset_class = parsed_trade.get('asset_class', 'Unknown')
    instrument_type = parsed_trade.get('instrument_type', 'Unknown')
    use_case = parsed_trade.get('use_case', 'Unknown')
    
    raw_trade_data = parsed_trade.get('classified_fields', {})
    
    template, matched_name, match_score = find_product_template(
        asset_class, instrument_type, use_case, library_path
    )
    
    if template is None:
        return {
            'trade_id': trade_id,
            'status': 'NOT_FOUND',
            'matched_template': None,
            'upi_code': None,
            'classification_note': (
                f"No product definition template found for "
                f"{asset_class}.{instrument_type}.{use_case}"
            ),
            'validation_errors': [
                f"No matching template: {asset_class}/{instrument_type}/{use_case}"
            ],
            'warnings': [],
        }
    
    # === STEP 3: Validate Attributes ===
    errors, warnings = validate_attributes(raw_trade_data, template, library_path)
    
    # Determine status
    if errors:
        status = 'INVALID_ATTRIBUTES'
    else:
        status = 'FOUND'
    
    # Generate UPI code
    upi_code = generate_upi_code(matched_name, raw_trade_data) if status == 'FOUND' else None
    
    # Add heuristic match warning if applicable
    if match_score < 1.0:
        warnings.append(
            f"HEURISTIC MATCH: Requested use_case '{use_case}' differs from matched template "
            f"'{matched_name.split('.')[-3]}' (score: {match_score:.2f}). "
            f"No exact match found in product library. Consider requesting product definition "
            f"for {asset_class}.{instrument_type}.{use_case}.UPI."
        )
    
    return {
        'trade_id': trade_id,
        'status': status,
        'matched_template': matched_name,
        'upi_code': upi_code,
        'classification_note': None,
        'validation_errors': errors,
        'warnings': warnings,
    }


def lookup_upi_batch(parsed_trades: List[Dict], library_path: str) -> List[Dict]:
    """
    Perform UPI lookup for all trades in batch
    """
    results = []
    
    for parsed_trade in parsed_trades:
        result = lookup_upi(parsed_trade, library_path)
        results.append(result)
    
    return results
