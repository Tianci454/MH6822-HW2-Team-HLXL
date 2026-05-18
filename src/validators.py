"""
Validation utilities for LEI, UTI, and other identifiers
Implements ISO standards: LEI (7064 MOD 97-10), UTI (ISO 23897)
"""

import re
from typing import Tuple, Optional


# ============================================================================
# LEI VALIDATION (ISO 7064 MOD 97-10)
# ============================================================================

def compute_lei_check_digits(lei_body: str) -> str:
    """
    Compute LEI check digits (positions 19-20)
    
    Algorithm (ISO 7064 MOD 97-10):
    1. Convert 18-char LEI body to numeric string (A=10, B=11, ..., Z=35)
    2. Append "00" to make verification string
    3. Compute: 98 - (numeric_value mod 97)
    4. Result is check digits (zero-padded to 2 digits)
    
    Args:
        lei_body: First 18 characters of LEI
    
    Returns:
        Two-digit check digit string (e.g., "12")
    """
    if not lei_body or len(lei_body) != 18:
        return ""
    
    # Step 1: Convert to numeric
    numeric_str = ""
    for char in lei_body:
        if char.isdigit():
            numeric_str += char
        elif char.isalpha():
            # A=10, B=11, ..., Z=35
            numeric_str += str(ord(char.upper()) - ord('A') + 10)
    
    # Step 2: Append "00"
    verification_str = numeric_str + "00"
    
    # Step 3: Compute mod 97
    verification_num = int(verification_str)
    remainder = verification_num % 97
    
    # Step 4: Compute check digits
    check_digits = 98 - remainder
    
    return f"{check_digits:02d}"


def validate_lei(lei: Optional[str]) -> Tuple[bool, str]:
    """
    Validate LEI format and check digits
    
    Args:
        lei: 20-character LEI string
    
    Returns:
        (is_valid, error_message)
    """
    
    if lei is None:
        return False, "LEI is null"
    
    if not isinstance(lei, str):
        return False, f"LEI must be string, got {type(lei).__name__}"
    
    if len(lei) != 20:
        return False, f"LEI must be 20 characters, got {len(lei)}"
    
    # Check format: 18 alphanumeric + 2 digits
    if not lei[:18].isalnum():
        return False, "LEI positions 1-18 must be alphanumeric"
    
    if not lei[18:20].isdigit():
        return False, "LEI positions 19-20 must be digits (check digits)"
    
    # Validate check digits
    computed_check = compute_lei_check_digits(lei[:18])
    actual_check = lei[18:20]
    
    if computed_check != actual_check:
        return False, f"LEI check digits invalid: expected {computed_check}, got {actual_check}"
    
    return True, ""


# ============================================================================
# UTI VALIDATION (ISO 23897)
# ============================================================================

def validate_uti(uti: Optional[str], reporting_lei: Optional[str]) -> Tuple[bool, str]:
    """
    Validate UTI format according to ISO 23897
    
    Rules:
    1. Maximum 52 characters
    2. First 20 characters = valid LEI (namespace)
    3. Namespace LEI must equal reporting counterparty LEI
    4. Suffix (chars 21+) = uppercase alphanumeric + hyphens only
    
    Args:
        uti: UTI string to validate
        reporting_lei: Reporting counterparty LEI (must match UTI namespace)
    
    Returns:
        (is_valid, error_message)
    """
    
    if uti is None:
        return False, "UTI is null"
    
    if not isinstance(uti, str):
        return False, f"UTI must be string, got {type(uti).__name__}"
    
    # Rule 1: Maximum length
    if len(uti) > 52:
        return False, f"UTI exceeds maximum length of 52 characters (length={len(uti)})"
    
    if len(uti) < 20:
        return False, f"UTI must be at least 20 characters (namespace), got {len(uti)}"
    
    # Extract namespace
    namespace = uti[:20]
    
    # Rule 2: Namespace must be valid LEI
    lei_valid, lei_error = validate_lei(namespace)
    if not lei_valid:
        return False, f"UTI namespace (first 20 chars) invalid LEI: {lei_error}"
    
    # Rule 3: Namespace LEI must match reporting LEI
    if reporting_lei is None:
        return False, "Reporting LEI is null but required for UTI validation"
    
    if namespace != reporting_lei:
        return False, (
            f"UTI namespace LEI ({namespace}) does not match "
            f"reporting counterparty LEI ({reporting_lei})"
        )
    
    # Rule 4: Suffix validation
    if len(uti) > 20:
        suffix = uti[20:]
        # Pattern: only uppercase letters, digits, and hyphens
        if not re.match(r'^[A-Z0-9\-]+$', suffix):
            return False, (
                f"UTI suffix must contain only uppercase letters, digits, and hyphens. "
                f"Got: {suffix}"
            )
    
    return True, ""


# ============================================================================
# ISO 8601 TIMESTAMP VALIDATION
# ============================================================================

def validate_iso8601_utc_timestamp(timestamp: Optional[str]) -> Tuple[bool, str]:
    """
    Validate ISO 8601 UTC timestamp format
    
    Valid formats:
    - 2024-12-19T09:35:00Z
    - 2024-12-19T09:35:00.123Z
    - 2024-12-19T09:35:00+00:00
    
    Args:
        timestamp: Timestamp string to validate
    
    Returns:
        (is_valid, error_message)
    """
    
    if timestamp is None:
        return False, "Timestamp is null"
    
    if not isinstance(timestamp, str):
        return False, f"Timestamp must be string, got {type(timestamp).__name__}"
    
    # Pattern: ISO 8601 with UTC indicator (Z or +00:00)
    iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|(\+|-)\d{2}:\d{2})$'
    
    if not re.match(iso8601_pattern, timestamp):
        return False, (
            f"Timestamp not in ISO 8601 UTC format. "
            f"Expected: 2024-12-19T09:35:00Z, got: {timestamp}"
        )
    
    # Must end with Z or +00:00 or -00:00 (UTC)
    if not (timestamp.endswith('Z') or '+00:00' in timestamp or timestamp.endswith('00:00')):
        # Check if it's actually UTC offset +00:00
        if not ('+00:00' in timestamp or '-00:00' in timestamp.split('T')[-1]):
            return False, "Timestamp must be in UTC timezone (Z or ±00:00)"
    
    return True, ""


# ============================================================================
# DATE VALIDATION
# ============================================================================

def validate_date(date_str: Optional[str]) -> Tuple[bool, str]:
    """
    Validate date format YYYY-MM-DD
    
    Args:
        date_str: Date string
    
    Returns:
        (is_valid, error_message)
    """
    
    if date_str is None:
        return False, "Date is null"
    
    if not isinstance(date_str, str):
        return False, f"Date must be string, got {type(date_str).__name__}"
    
    # Pattern: YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False, f"Date not in YYYY-MM-DD format: {date_str}"
    
    # Validate actual date
    try:
        year, month, day = date_str.split('-')
        year, month, day = int(year), int(month), int(day)
        
        if not (1 <= month <= 12):
            return False, f"Invalid month: {month}"
        
        # Simple day validation (no leap year handling needed)
        days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if not (1 <= day <= days_in_month[month - 1]):
            return False, f"Invalid day: {day} for month {month}"
        
        # Reject placeholder dates like 9999-99-99
        if year == 9999 or month == 99 or day == 99:
            return False, "Placeholder date not allowed (9999-99-99)"
        
    except (ValueError, IndexError) as e:
        return False, f"Date parsing error: {e}"
    
    return True, ""


# ============================================================================
# CURRENCY CODE VALIDATION
# ============================================================================

def is_valid_iso_currency(currency_code: Optional[str]) -> bool:
    """
    Quick check if currency code looks valid
    Does not require pycountry
    
    Args:
        currency_code: ISO 4217 currency code
    
    Returns:
        True if valid format (3 uppercase letters)
    """
    if not currency_code or not isinstance(currency_code, str):
        return False
    
    # ISO 4217: 3 uppercase letters
    # Special commodities: XAU (gold), XAG (silver), XPT (platinum), XPD (palladium)
    if len(currency_code) == 3 and currency_code.isupper():
        return True
    
    return False


# ============================================================================
# ENUM VALIDATION
# ============================================================================

def validate_enum(value: Optional[str], valid_values: set) -> Tuple[bool, str]:
    """
    Validate value against enumeration
    
    Args:
        value: Value to validate
        valid_values: Set of valid values
    
    Returns:
        (is_valid, error_message)
    """
    
    if value is None:
        return False, "Value is null"
    
    if value not in valid_values:
        return False, f"Value '{value}' not in valid set: {sorted(valid_values)}"
    
    return True, ""
