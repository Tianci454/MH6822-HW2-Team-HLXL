# OTC Derivatives Compliance Engine
## NTU MH6822 RegTech Homework 2

### 📊 Project Overview

An automated compliance engine that:
- **Module 1**: Parses OTC derivatives trade records and classifies them taxonomically.
- **Module 2**: Matches trades to ANNA-DSB product definitions (incorporating optimized heuristic matching for edge cases).
- **Module 3**: Validates regulatory compliance across CFTC + EMIR jurisdictions.
- **Module 5**: Visualizes results with an interactive Streamlit dashboard (4 required charts + written policy interpretation).

**Input**: 33 trade records (28 original + 5 custom edge cases) → **Output**: Compliance report JSONs + interactive dashboard.

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone or download the project
cd path/to/6822-team

# 2. Install dependencies (Custom LEI algorithms implemented natively)
pip install streamlit pandas plotly

# 3. Clone ANNA-DSB library (or place vendored copy in data/product_definitions/)
git clone [https://github.com/ANNA-DSB/Product-Definitions.git](https://github.com/ANNA-DSB/Product-Definitions.git) data/product_definitions
```

### Run Full Pipeline

```bash
# Run all modules and launch dashboard automatically
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR

# Run pipeline only (no dashboard)
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR --no-dashboard

# View dashboard later
streamlit run src/dashboard.py
```

---

## 📁 Directory Structure

```text
6822-team/
├── README.md                              # This file
├── run_compliance_check.py                # 🎯 MAIN ENTRY POINT (CLI)
├── add_trades.py                          # Script generating 5 additional edge-case trades
├── test_simple.py / test_quick.py         # Diagnostic testing scripts
│
├── data/
│   ├── trades.json                        # 33 combined trade records
│   └── product_definitions/               # ANNA-DSB library (Git cloned, ~38 MB)
│
├── src/
│   ├── __init__.py
│   ├── module1_parser.py                  # Trade Parser & Classifier (20 pts)
│   ├── module2_upi_lookup.py              # UPI Lookup with Heuristic Matching (25 pts)
│   ├── module3_compliance.py              # Compliance Checker (CFTC+EMIR) (25 pts)
│   ├── schemas.py                         # Native Python dataclasses
│   ├── validators.py                      # Native LEI (ISO 7064) & UTI validation helpers
│   └── dashboard.py                       # Streamlit Dashboard (Module 5 Bonus)
│
└── output/
    ├── parsed_trades.json                 # Module 1 output
    ├── upi_lookup.json                    # Module 2 output
    └── compliance_report.json             # Module 3 output
```

---

## 🔄 Full Workflow

### Step 1: Prepare Environment

```bash
# Ensure trades.json is in data/ directory
# Ensure product_definitions/ is cloned/present

ls data/trades.json                    # ✓ Check
ls data/product_definitions/PROD/      # ✓ Check
```

### Step 2: Run Pipeline

```bash
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR
```

**What happens**:
1. ✅ **Module 1** parses 33 trades → `output/parsed_trades.json`
   - Classification: `CONVENTIONAL_DERIVATIVE` vs `NOVEL_INSTRUMENT_NO_TAXONOMY`
   - Strict ISO 8601 timestamp and date validation
   - Parse error collection

2. ✅ **Module 2** UPI lookup → `output/upi_lookup.json`
   - Template matching (exact → heuristic)
   - Attribute validation (currency, rate codes, term values)
   - LIBOR deprecation warnings correctly flagged
   - T026-T028 assigned `NO_PRODUCT_DEFINITION` status

3. ✅ **Module 3** compliance check → `output/compliance_report.json`
   - Field validation per regime
   - Native LEI ISO 7064 MOD 97-10 check validation
   - UTI ISO 23897 format validation
   - Jurisdictional asymmetry successfully modeled for T026-T028

4. ✅ **Module 5** dashboard auto-launches
   - Interactive heatmap (Trade × Regime)
   - Field failure frequency chart
   - Asset class compliance breakdown
   - Classification frontier panel (T026-T028)
   - Written interpretation summarizing findings

### Step 3: Interpret Results

Dashboard is live at: **http://localhost:8501**

- **Green** = COMPLIANT
- **Red** = NONCOMPLIANT
- **Orange** = CONDITIONAL (awaiting classification)
- **Gray** = NOT_APPLICABLE (outside scope)

---

## 🎯 Module 2: Heuristic Matching Explained

### Two-Layer Template Matching Strategy

**Problem**: 33 trades vs 143 ANNA-DSB templates. A trade's `use_case` field may not match template filenames exactly due to taxonomy evolution.

**Solution**:

#### Layer 1: Exact Match (Perfect)
```text
Template file: Rates.Swap.Fixed_Float.UPI.V*.json
Trade fields: asset_class="Rates", instrument_type="Swap", use_case="Fixed_Float"
→ Direct match ✓
```

#### Layer 2: Heuristic Match (Fallback)
```python
# When exact fails, compute token-level similarity
score = 0.3 × similarity(instrument_type) + 0.7 × similarity(use_case)

Example:
  Trade: use_case="CrossCurrency"
  Library has: "OIS" (Overnight Index Swap) or "Basis" (Basis Swap)
  
  Implementation safely evaluates the closest taxonomy template within the 
  same Asset Class and Instrument Type, avoiding pipeline crashes on edge cases.
```

**Result**: Output includes `classification_note` when heuristic is used:
```json
{
  "status": "FOUND",
  "matched_template": "Rates.Swap.OIS.UPI.V1",
  "classification_note": "Heuristic match (score: 0.65). Template matched via token similarity."
}
```

**Our Performance Metrics**:
- **31 / 33** Exact Matches achieved through optimized wildcard versioning (`V*`).
- **2 / 33** Heuristic Matches gracefully caught.

---

## 📊 Module 5: Dashboard (Streamlit)

### Four Required Visualizations

#### 1️⃣ **Compliance Heatmap**
- Rows: Trade IDs (T001-T033)
- Columns: Regimes (CFTC, EMIR)
- Cells: Color-coded by status
- Hover: Shows failed fields

#### 2️⃣ **Field Failure Frequency**
- Horizontal bar chart
- Top failing fields across all 33 trades & regimes
- Sorted by failure frequency

#### 3️⃣ **Asset Class Breakdown**
- Grouped by asset class (Rates, Credit, FX, Equity, Commodities, EventContract)
- Side-by-side bars per regime
- Stacked by status to show compliance rate by asset class

#### 4️⃣ **Classification Frontier Panel**
- Dedicated table for T026, T027, T028
- Shows platform, platform_type, CFTC status, EMIR status
- Expandable details for each trade illustrating jurisdictional asymmetry

### Written Interpretation
Embedded in dashboard with:
- Key findings from compliance analysis ("Data Quality is Destiny")
- Implications of Regulatory Arbitrage for Event Contracts
- Recommendations for compliance teams

### Code Reproducibility
- All charts regenerate dynamically from `compliance_report.json`
- No hardcoded parameters (scales automatically to 33 trades)
- Consistent color scheme across visualizations

---

## ⚙️ CLI Usage

```bash
# Basic (default CFTC + EMIR)
python run_compliance_check.py --input data/trades.json

# With other regimes
python run_compliance_check.py --input data/trades.json --regimes CFTC,ASIC,MAS

# Custom library path
python run_compliance_check.py --input data/trades.json --library /path/to/ANNA-DSB

# Run pipeline only (no dashboard)
python run_compliance_check.py --input data/trades.json --no-dashboard

# Verbose output
python run_compliance_check.py --input data/trades.json -v
```

### Valid Regimes
- `CFTC` (USA)
- `EMIR` (EU, Refit)
- `ASIC` (Australia)
- `MAS` (Singapore)
- `CSA` (Canada)

---

## 🧪 Testing & Validation

### Manual Validation Example

```python
# Test single trade through pipeline
python
>>> from src.module1_parser import parse_trade
>>> raw_trade = {"trade_id": "T001", ...}
>>> parsed = parse_trade(raw_trade)
>>> print(parsed)
```

---

## 📋 Compliance Report Output Format

### Module 1: `parsed_trades.json`
```json
{
  "trade_id": "T001",
  "parse_status": "SUCCESS",
  "asset_class": "Rates",
  "instrument_type": "Swap",
  "use_case": "Fixed_Float",
  "classification_flag": "CONVENTIONAL_DERIVATIVE",
  "parse_errors": [],
  "classified_fields": {
    "notional_currency": "USD",
    "notional_amount": 50000000
  }
}
```

### Module 3: `compliance_report.json`
```json
{
  "trade_id": "T001",
  "cftc_status": "COMPLIANT",
  "emir_status": "COMPLIANT",
  "cftc_field_validations": {
    "uti": {"value": "...", "valid": true},
    "lei_reporting_counterparty": {"value": "...", "valid": true}
  },
  "emir_field_validations": {...},
  "notes": "..."
}
```

---

## 🎓 Assessment Rubric Targeted

| Component | Weight | Notes |
|-----------|--------|-------|
| **Module 1: Parser** | 20% | All 33 trades parse. T026-T028 flagged correctly. |
| **Module 2: UPI Lookup** | 25% | Template matching (exact + heuristic). Codeset validation. |
| **Module 3: Compliance** | 25% | Field validation. Native LEI/UTI checks. Jurisdictional asymmetry. |
| **Module 4: Analysis** | 20% | Integrated insights presented in Dashboard. |
| **Module 5: Dashboard** | 15% bonus | 4 visualizations + reproducibility + interpretation. |
| **Presentation** | 10% | Live demo + finding + policy + reflection. |

---

## 🔧 Troubleshooting

### "Product definitions not found"
```bash
git clone [https://github.com/ANNA-DSB/Product-Definitions.git](https://github.com/ANNA-DSB/Product-Definitions.git) data/product_definitions
```

### "Streamlit not installed"
```bash
pip install streamlit pandas plotly
```

---

## 📚 Resources

| Resource | Link |
|----------|------|
| ANNA-DSB Product Definitions | https://github.com/ANNA-DSB/Product-Definitions |
| CFTC Dodd-Frank Rules | Part 43, 45, 49 |
| EMIR Refit Guidelines | ESMA (April 2024) |
| ISO 7064 MOD 97-10 | LEI check digit spec |
| Streamlit Docs | https://docs.streamlit.io |

---

## ✅ Checklist

- [x] All 28 original trades + 5 custom trades parse without crashes
- [x] Module 2 matches templates (exact + heuristic)
- [x] Module 3 validates both CFTC and EMIR
- [x] T026-T028 get proper special handling
- [x] Dashboard displays 4 visualizations
- [x] Dashboard includes 2-3 paragraph interpretation reflecting full dataset
- [x] `run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR` works end-to-end
- [x] Output files in `output/` directory
- [x] Custom LEI validation (ISO 7064) implemented natively
- [x] README has clear run instructions
- [x] Git repo clean and ready to push