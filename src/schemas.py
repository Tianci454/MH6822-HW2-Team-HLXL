"""
Pydantic dataclasses for OTC Derivatives Compliance Engine
Defines all key data structures across modules
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ParseStatus(str, Enum):
    """Status of trade parsing"""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ClassificationFlag(str, Enum):
    """Instrument classification flag"""
    CONVENTIONAL_DERIVATIVE = "CONVENTIONAL_DERIVATIVE"
    NOVEL_INSTRUMENT_NO_TAXONOMY = "NOVEL_INSTRUMENT_NO_TAXONOMY"
    CLASSIFICATION_AMBIGUOUS = "CLASSIFICATION_AMBIGUOUS"


class UpiStatus(str, Enum):
    """UPI lookup result status"""
    FOUND = "FOUND"
    NO_PRODUCT_DEFINITION = "NO_PRODUCT_DEFINITION"
    NOT_FOUND = "NOT_FOUND"
    INVALID_ATTRIBUTES = "INVALID_ATTRIBUTES"


class ComplianceStatus(str, Enum):
    """Compliance check result status"""
    COMPLIANT = "COMPLIANT"
    NONCOMPLIANT = "NONCOMPLIANT"
    CONDITIONAL = "CONDITIONAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ============================================================================
# MODULE 1: TRADE PARSER
# ============================================================================

@dataclass
class ParsedTrade:
    """Output of Module 1: Trade parsing and classification"""
    trade_id: str
    parse_status: str  # SUCCESS | PARTIAL | FAILED
    asset_class: Optional[str]
    instrument_type: Optional[str]
    use_case: Optional[str]
    classification_flag: str  # CONVENTIONAL_DERIVATIVE | NOVEL_INSTRUMENT_NO_TAXONOMY | CLASSIFICATION_AMBIGUOUS
    parse_errors: List[str] = field(default_factory=list)
    classified_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return asdict(self)


# ============================================================================
# MODULE 2: UPI LOOKUP
# ============================================================================

@dataclass
class UpiLookupResult:
    """Output of Module 2: UPI lookup"""
    trade_id: str
    status: str  # FOUND | NO_PRODUCT_DEFINITION | NOT_FOUND | INVALID_ATTRIBUTES
    matched_template: Optional[str]
    upi_code: Optional[str]
    classification_note: Optional[str]
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return asdict(self)


# ============================================================================
# MODULE 3: COMPLIANCE CHECKER
# ============================================================================

@dataclass
class FieldValidation:
    """Validation result for a single field"""
    field_name: str
    value: Any
    valid: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'value': self.value,
            'valid': self.valid,
            'error': self.error_message
        }


@dataclass
class ComplianceResult:
    """Output of Module 3: Compliance check"""
    trade_id: str
    asset_class: Optional[str]
    instrument_type: Optional[str]
    use_case: Optional[str]
    classification_flag: Optional[str]
    cftc_status: str  # COMPLIANT | NONCOMPLIANT | CONDITIONAL | NOT_APPLICABLE
    emir_status: str
    cftc_field_validations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    emir_field_validations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cftc_notes: Optional[str] = None
    emir_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return asdict(self)


# ============================================================================
# COMMON DATA STRUCTURES
# ============================================================================

@dataclass
class TradeFieldValidation:
    """For storing individual field validation results"""
    field_name: str
    required: bool
    value: Any
    valid: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'value': self.value,
            'valid': self.valid,
            'error': self.error
        }
