#!/usr/bin/env python3
"""
OTC Derivatives Compliance Engine - Main Entry Point
Orchestrates all modules (1, 2, 3) and launches the Streamlit dashboard (5)
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Import modules
sys.path.insert(0, str(Path(__file__).parent))

from src.module1_parser import parse_trades, serialize_parsed_trades
from src.module2_upi_lookup import lookup_upi_batch
from src.module3_compliance import check_compliance_batch


# ============================================================================
# CONFIGURATION
# ============================================================================

VALID_REGIMES = ['CFTC', 'EMIR', 'ASIC', 'MAS', 'CSA']
DEFAULT_REGIMES = ['CFTC', 'EMIR']

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================================
# PIPELINE ORCHESTRATION
# ============================================================================

def run_pipeline(
    input_file: str,
    regimes: List[str],
    library_path: str = "data/product_definitions",
    verbose: bool = True
) -> Dict[str, Path]:
    """
    Execute full compliance pipeline: Module 1 → 2 → 3
    
    Args:
        input_file: Path to trades.json
        regimes: List of regulatory regimes (e.g., ['CFTC', 'EMIR'])
        library_path: Path to ANNA-DSB product definitions
        verbose: Print progress messages
    
    Returns:
        Dictionary of output file paths
    """
    
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if not Path(library_path).exists():
        raise FileNotFoundError(f"ANNA-DSB library not found: {library_path}")
    
    output_paths = {}
    
    # ========================================================================
    # MODULE 1: TRADE PARSER & INSTRUMENT CLASSIFIER
    # ========================================================================
    if verbose:
        print("\n" + "="*70)
        print("MODULE 1: Trade Parser & Instrument Classifier")
        print("="*70)
    
    try:
        print(f"📖 Reading trades from: {input_file}")
        with open(input_path) as f:
            raw_trades = json.load(f)
        
        print(f"📋 Parsing {len(raw_trades)} trades...")
        parsed_trades = parse_trades(raw_trades)
        
        parsed_output = OUTPUT_DIR / "parsed_trades.json"
        with open(parsed_output, 'w') as f:
            f.write(serialize_parsed_trades(parsed_trades))
        
        output_paths['module1'] = parsed_output
        
        # Summary
        success_count = sum(1 for t in parsed_trades if t.parse_status == 'SUCCESS')
        partial_count = sum(1 for t in parsed_trades if t.parse_status == 'PARTIAL')
        failed_count = sum(1 for t in parsed_trades if t.parse_status == 'FAILED')
        
        novel_count = sum(1 for t in parsed_trades 
                         if t.classification_flag == 'NOVEL_INSTRUMENT_NO_TAXONOMY')
        
        print(f"\n✅ Module 1 Complete")
        print(f"   • SUCCESS: {success_count}/28")
        print(f"   • PARTIAL: {partial_count}/28")
        print(f"   • FAILED: {failed_count}/28")
        print(f"   • Novel instruments (T026-T028): {novel_count}")
        print(f"   • Output: {parsed_output}")
        
    except Exception as e:
        print(f"❌ Module 1 failed: {e}")
        raise
    
    # ========================================================================
    # MODULE 2: UPI LOOKUP ENGINE
    # ========================================================================
    if verbose:
        print("\n" + "="*70)
        print("MODULE 2: UPI Lookup Engine")
        print("="*70)
    
    try:
        print(f"🔍 Looking up UPI templates from library: {library_path}")
        # Convert ParsedTrade objects to dicts for Module 2
        parsed_trades_dicts = [t.to_dict() for t in parsed_trades]
        upi_results = lookup_upi_batch(parsed_trades_dicts, library_path)
        
        upi_output = OUTPUT_DIR / "upi_lookup.json"
        with open(upi_output, 'w') as f:
            json.dump(upi_results, f, indent=2)
        
        output_paths['module2'] = upi_output
        
        # Summary
        found_count = sum(1 for t in upi_results if t['status'] == 'FOUND')
        no_def_count = sum(1 for t in upi_results if t['status'] == 'NO_PRODUCT_DEFINITION')
        not_found_count = sum(1 for t in upi_results if t['status'] == 'NOT_FOUND')
        invalid_count = sum(1 for t in upi_results if t['status'] == 'INVALID_ATTRIBUTES')
        
        heuristic_count = sum(1 for t in upi_results 
                            if any('HEURISTIC MATCH' in w for w in t.get('warnings', [])))
        
        print(f"\n✅ Module 2 Complete")
        print(f"   • FOUND: {found_count}/28")
        print(f"   • NO_PRODUCT_DEFINITION (T026-T028): {no_def_count}/28")
        print(f"   • NOT_FOUND: {not_found_count}/28")
        print(f"   • INVALID_ATTRIBUTES: {invalid_count}/28")
        print(f"   • Heuristic matches: {heuristic_count}")
        print(f"   • Output: {upi_output}")
        
    except Exception as e:
        print(f"❌ Module 2 failed: {e}")
        raise
    
    # ========================================================================
    # MODULE 3: MULTI-JURISDICTIONAL COMPLIANCE CHECKER
    # ========================================================================
    if verbose:
        print("\n" + "="*70)
        print(f"MODULE 3: Multi-Jurisdictional Compliance Checker ({' + '.join(regimes)})")
        print("="*70)
    
    try:
        if not all(r in VALID_REGIMES for r in regimes):
            invalid = [r for r in regimes if r not in VALID_REGIMES]
            raise ValueError(f"Invalid regimes: {invalid}. Valid: {VALID_REGIMES}")
        
        print(f"⚖️  Validating against {len(regimes)} regulatory regime(s): {', '.join(regimes)}")
        compliance_results = check_compliance_batch(
            parsed_trades=parsed_trades,
            upi_results=upi_results,
            raw_trades=raw_trades,
            regimes=regimes
        )
        
        compliance_output = OUTPUT_DIR / "compliance_report.json"
        with open(compliance_output, 'w') as f:
            json.dump(compliance_results, f, indent=2)
        
        output_paths['module3'] = compliance_output
        
        # Summary - for each regime
        for regime in regimes:
            key = f"{regime.lower()}_status"
            compliant = sum(1 for t in compliance_results if t.get(f'{key}') == 'COMPLIANT')
            noncompliant = sum(1 for t in compliance_results if t.get(f'{key}') == 'NONCOMPLIANT')
            conditional = sum(1 for t in compliance_results if t.get(f'{key}') == 'CONDITIONAL')
            not_applicable = sum(1 for t in compliance_results if t.get(f'{key}') == 'NOT_APPLICABLE')
            
            print(f"\n   {regime} Regime:")
            print(f"      • COMPLIANT: {compliant}/28")
            print(f"      • NONCOMPLIANT: {noncompliant}/28")
            print(f"      • CONDITIONAL: {conditional}/28")
            print(f"      • NOT_APPLICABLE: {not_applicable}/28")
        
        print(f"\n✅ Module 3 Complete")
        print(f"   • Output: {compliance_output}")
        
    except Exception as e:
        print(f"❌ Module 3 failed: {e}")
        raise
    
    return output_paths


# ============================================================================
# DASHBOARD LAUNCHER
# ============================================================================

def launch_dashboard(compliance_output: Path, verbose: bool = True):
    """
    Launch the Streamlit dashboard
    
    Args:
        compliance_output: Path to compliance_report.json
        verbose: Print progress
    """
    
    if verbose:
        print("\n" + "="*70)
        print("MODULE 5: Compliance Dashboard (Streamlit)")
        print("="*70)
    
    print("🚀 Launching Streamlit dashboard...")
    print("   • Opening at: http://localhost:8501")
    print("   • Press Ctrl+C to stop the dashboard\n")
    
    try:
        subprocess.run(
            ["streamlit", "run", "src/dashboard.py", "--logger.level=error"],
            check=False
        )
    except FileNotFoundError:
        print("⚠️  Streamlit not found. Install with: pip install streamlit")
        print("   Run 'python src/dashboard.py' directly to launch the dashboard later.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OTC Derivatives Compliance Engine - Full Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_compliance_check.py --input trades.json --regimes CFTC,EMIR
  python run_compliance_check.py --input trades.json --regimes CFTC,EMIR --library data/product_definitions
  python run_compliance_check.py --input trades.json --regimes CFTC,EMIR --no-dashboard
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input trades.json file (required)'
    )
    
    parser.add_argument(
        '--regimes',
        default=','.join(DEFAULT_REGIMES),
        help=f'Comma-separated list of regulatory regimes. Default: {",".join(DEFAULT_REGIMES)}. '
             f'Valid: {", ".join(VALID_REGIMES)}'
    )
    
    parser.add_argument(
        '--library',
        default='data/product_definitions',
        help='Path to ANNA-DSB Product Definitions library'
    )
    
    parser.add_argument(
        '--no-dashboard',
        action='store_true',
        help='Run pipeline only, do not launch Streamlit dashboard'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=True,
        help='Verbose output (default: True)'
    )
    
    args = parser.parse_args()
    
    # Parse regimes
    regimes = [r.strip().upper() for r in args.regimes.split(',')]
    
    # Validate
    if not all(r in VALID_REGIMES for r in regimes):
        invalid = [r for r in regimes if r not in VALID_REGIMES]
        print(f"❌ Invalid regimes: {invalid}")
        print(f"   Valid options: {', '.join(VALID_REGIMES)}")
        sys.exit(1)
    
    print("\n" + "█"*70)
    print("█  OTC DERIVATIVES COMPLIANCE ENGINE")
    print("█  Homework 2: NTU MH6822 RegTech")
    print("█"*70)
    print(f"\n📝 Configuration:")
    print(f"   Input File: {args.input}")
    print(f"   Regimes: {', '.join(regimes)}")
    print(f"   Library: {args.library}")
    print(f"   Dashboard: {'Enabled' if not args.no_dashboard else 'Disabled'}")
    
    try:
        # Run pipeline
        output_paths = run_pipeline(
            input_file=args.input,
            regimes=regimes,
            library_path=args.library,
            verbose=args.verbose
        )
        
        # Summary
        print("\n" + "="*70)
        print("PIPELINE COMPLETE ✅")
        print("="*70)
        print(f"\n📊 Output Files:")
        for module, path in output_paths.items():
            print(f"   • {module}: {path}")
        
        # Launch dashboard if not disabled
        if not args.no_dashboard:
            launch_dashboard(output_paths.get('module3'), verbose=args.verbose)
        else:
            print("\n💡 To view the dashboard later, run:")
            print("   streamlit run src/dashboard.py")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
