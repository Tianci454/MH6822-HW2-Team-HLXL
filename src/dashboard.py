"""
Module 5: OTC Derivatives Compliance Dashboard
Streamlit interactive visualization with 4 required charts + written interpretation
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
from typing import Dict, List, Any

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="OTC Derivatives Compliance Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏦 OTC Derivatives Compliance Dashboard")
st.markdown("**Interactive compliance analysis for 28 OTC derivative trades across CFTC and EMIR regimes**")

# ============================================================================
# DATA LOADING & CACHING
# ============================================================================
@st.cache_data
def load_data(compliance_report_path: str, trades_path: str):
    """Load and cache compliance report and trades data"""
    with open(compliance_report_path) as f:
        compliance_data = json.load(f)
    
    with open(trades_path) as f:
        trades_data = json.load(f)
    
    # Create mapping for quick access
    trades_map = {t['trade_id']: t for t in trades_data}
    
    return compliance_data, trades_map

# Load data
COMPLIANCE_REPORT_PATH = "output/compliance_report.json"
TRADES_PATH = "data/trades.json"

if not Path(COMPLIANCE_REPORT_PATH).exists() or not Path(TRADES_PATH).exists():
    st.error("❌ Data files not found. Run `python run_compliance_check.py` first.")
    st.stop()

compliance_data, trades_map = load_data(COMPLIANCE_REPORT_PATH, TRADES_PATH)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def create_compliance_dataframe(compliance_data: List[Dict]) -> pd.DataFrame:
    """Convert compliance data to DataFrame"""
    rows = []
    for trade in compliance_data:
        rows.append({
            'trade_id': trade['trade_id'],
            'asset_class': trade.get('asset_class', 'Unknown'),
            'instrument_type': trade.get('instrument_type', 'Unknown'),
            'cftc_status': trade['cftc_status'],
            'emir_status': trade['emir_status'],
        })
    return pd.DataFrame(rows)

def get_status_color(status: str) -> str:
    """Map compliance status to color"""
    colors = {
        'COMPLIANT': '#2ecc71',           # Green
        'NONCOMPLIANT': '#e74c3c',        # Red
        'CONDITIONAL': '#f39c12',         # Orange
        'NOT_APPLICABLE': '#95a5a6',      # Gray
    }
    return colors.get(status, '#34495e')

def count_field_failures(compliance_data: List[Dict]) -> Dict[str, int]:
    """Count failures by field across all trades and regimes"""
    field_counts = {}
    
    for trade in compliance_data:
        # CFTC field validations
        if 'cftc_field_validations' in trade:
            for field_name, field_info in trade['cftc_field_validations'].items():
                if not field_info.get('valid', False):
                    field_counts[field_name] = field_counts.get(field_name, 0) + 1
        
        # EMIR field validations
        if 'emir_field_validations' in trade:
            for field_name, field_info in trade['emir_field_validations'].items():
                if not field_info.get('valid', False):
                    field_counts[field_name] = field_counts.get(field_name, 0) + 1
    
    return dict(sorted(field_counts.items(), key=lambda x: x[1], reverse=True))

# ============================================================================
# VISUALIZATION 1: COMPLIANCE HEATMAP
# ============================================================================
st.header("📊 Visualization 1: Portfolio Compliance Heatmap")

df_compliance = create_compliance_dataframe(compliance_data)

# Create heatmap data
heatmap_data = []
for _, row in df_compliance.iterrows():
    heatmap_data.append({
        'Trade ID': row['trade_id'],
        'CFTC': row['cftc_status'],
        'EMIR': row['emir_status'],
    })

heatmap_df = pd.DataFrame(heatmap_data).set_index('Trade ID')

# Numeric mapping for heatmap
status_to_num = {
    'COMPLIANT': 3,
    'NONCOMPLIANT': 0,
    'CONDITIONAL': 2,
    'NOT_APPLICABLE': 1,
}

heatmap_values = heatmap_df.applymap(lambda x: status_to_num.get(x, -1))

# Create heatmap
fig_heatmap = go.Figure(data=go.Heatmap(
    z=heatmap_values.values,
    x=heatmap_values.columns,
    y=heatmap_values.index,
    colorscale=[
        [0, '#e74c3c'],           # NONCOMPLIANT - Red
        [0.33, '#95a5a6'],        # NOT_APPLICABLE - Gray
        [0.66, '#f39c12'],        # CONDITIONAL - Orange
        [1, '#2ecc71'],           # COMPLIANT - Green
    ],
    text=heatmap_df.values,
    texttemplate='%{text}',
    textfont={"size": 9},
    hovertemplate='<b>%{y}</b><br>Regime: %{x}<br>Status: %{text}<extra></extra>',
    colorbar=dict(
        title="Status",
        tickvals=[0, 1, 2, 3],
        ticktext=['NONCOMPLIANT', 'NOT_APPLICABLE', 'CONDITIONAL', 'COMPLIANT']
    )
))

fig_heatmap.update_layout(
    title_text="Trade-by-Trade Compliance Matrix (28 trades × 2 regimes)",
    xaxis_title="Regulatory Regime",
    yaxis_title="Trade ID",
    height=800,
    showlegend=False,
)

st.plotly_chart(fig_heatmap, use_container_width=True)

col1_viz1, col2_viz1 = st.columns(2)
total_trades = len(df_compliance)

with col1_viz1:
    compliant_cftc = (df_compliance['cftc_status'] == 'COMPLIANT').sum()
    st.metric("✅ COMPLIANT (CFTC)", f"{compliant_cftc}/{total_trades}", f"{compliant_cftc/total_trades*100:.1f}%")
with col2_viz1:
    compliant_emir = (df_compliance['emir_status'] == 'COMPLIANT').sum()
    st.metric("✅ COMPLIANT (EMIR)", f"{compliant_emir}/{total_trades}", f"{compliant_emir/total_trades*100:.1f}%")
# ============================================================================
# VISUALIZATION 2: FIELD FAILURE FREQUENCY
# ============================================================================
st.header("📉 Visualization 2: Field-Level Failure Frequency")

field_failures = count_field_failures(compliance_data)

if field_failures:
    top_n = min(15, len(field_failures))
    top_fields = dict(list(field_failures.items())[:top_n])
    
    fig_field_freq = go.Figure(data=[
        go.Bar(
            y=list(top_fields.keys()),
            x=list(top_fields.values()),
            orientation='h',
            marker=dict(
                color=list(top_fields.values()),
                colorscale='Reds',
                showscale=True,
            ),
            text=list(top_fields.values()),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Failures: %{x}<extra></extra>',
        )
    ])
    
    fig_field_freq.update_layout(
        title_text=f"Most Frequently Failing Fields (Top {top_n})",
        xaxis_title="Number of Failures (across all trades & regimes)",
        yaxis_title="Field Name",
        height=500,
        showlegend=False,
    )
    
    st.plotly_chart(fig_field_freq, use_container_width=True)
    
    st.info(f"**Finding**: {len(field_failures)} distinct fields failed validation. "
            f"Top issue: `{list(top_fields.keys())[0]}` failed {list(top_fields.values())[0]} times.")
else:
    st.warning("No field failures detected.")

# ============================================================================
# VISUALIZATION 3: ASSET CLASS COMPLIANCE BREAKDOWN
# ============================================================================
st.header("📈 Visualization 3: Asset Class Compliance Breakdown")

asset_class_breakdown = []
for _, row in df_compliance.iterrows():
    asset_class_breakdown.append({
        'Asset Class': row['asset_class'],
        'CFTC Status': row['cftc_status'],
        'EMIR Status': row['emir_status'],
    })

df_ac = pd.DataFrame(asset_class_breakdown)

# Create grouped data for stacked bar chart
cftc_counts = df_ac.groupby(['Asset Class', 'CFTC Status']).size().unstack(fill_value=0)
emir_counts = df_ac.groupby(['Asset Class', 'EMIR Status']).size().unstack(fill_value=0)

# Ensure all status columns exist
for status in ['COMPLIANT', 'NONCOMPLIANT', 'CONDITIONAL', 'NOT_APPLICABLE']:
    if status not in cftc_counts.columns:
        cftc_counts[status] = 0
    if status not in emir_counts.columns:
        emir_counts[status] = 0

# Create subplots
fig_ac = make_subplots(
    rows=1, cols=2,
    subplot_titles=("CFTC Regime", "EMIR Regime"),
    specs=[[{"type": "bar"}, {"type": "bar"}]]
)

# Status colors
status_colors = {
    'COMPLIANT': '#2ecc71',
    'NONCOMPLIANT': '#e74c3c',
    'CONDITIONAL': '#f39c12',
    'NOT_APPLICABLE': '#95a5a6',
}

status_order = ['COMPLIANT', 'NONCOMPLIANT', 'CONDITIONAL', 'NOT_APPLICABLE']

# Add CFTC traces
for status in status_order:
    if status in cftc_counts.columns:
        fig_ac.add_trace(
            go.Bar(
                name=status,
                x=cftc_counts.index,
                y=cftc_counts[status],
                marker_color=status_colors[status],
                hovertemplate='<b>%{x}</b><br>' + status + ': %{y}<extra></extra>',
            ),
            row=1, col=1
        )

# Add EMIR traces
for status in status_order:
    if status in emir_counts.columns:
        fig_ac.add_trace(
            go.Bar(
                name=status,
                x=emir_counts.index,
                y=emir_counts[status],
                marker_color=status_colors[status],
                showlegend=False,
                hovertemplate='<b>%{x}</b><br>' + status + ': %{y}<extra></extra>',
            ),
            row=1, col=2
        )

fig_ac.update_xaxes(title_text="Asset Class", row=1, col=1)
fig_ac.update_xaxes(title_text="Asset Class", row=1, col=2)
fig_ac.update_yaxes(title_text="Count", row=1, col=1)
fig_ac.update_yaxes(title_text="Count", row=1, col=2)

fig_ac.update_layout(
    title_text="Compliance Status by Asset Class",
    barmode='stack',
    height=500,
    hovermode='x unified',
)

st.plotly_chart(fig_ac, use_container_width=True)

# ============================================================================
# VISUALIZATION 4: CLASSIFICATION FRONTIER PANEL (T026, T027, T028)
# ============================================================================
st.header("🌍 Visualization 4: Classification Frontier (Event Contracts)")

frontier_trades = ['T026', 'T027', 'T028']
frontier_data = []

for trade_id in frontier_trades:
    comp_record = next((t for t in compliance_data if t['trade_id'] == trade_id), None)
    trade_record = trades_map.get(trade_id, {})
    
    if comp_record:
        frontier_data.append({
            'Trade ID': trade_id,
            'Asset Class': trade_record.get('asset_class', 'N/A'),
            'Instrument Type': trade_record.get('instrument_type', 'N/A'),
            'Use Case': trade_record.get('use_case', 'N/A'),
            'Platform': trade_record.get('platform', 'N/A'),
            'CFTC Status': comp_record['cftc_status'],
            'EMIR Status': comp_record['emir_status'],
            'Description': trade_record.get('description', 'N/A')[:100] + '...',
        })

df_frontier = pd.DataFrame(frontier_data)

# Display as table
st.markdown("**Event Contracts: Regulatory Asymmetry**")
st.dataframe(
    df_frontier,
    use_container_width=True,
    height=250,
)

# Add details for each trade
for trade_id in frontier_trades:
    with st.expander(f"📋 Details: {trade_id}"):
        comp_record = next((t for t in compliance_data if t['trade_id'] == trade_id), None)
        trade_record = trades_map.get(trade_id, {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Platform**: {trade_record.get('platform', 'N/A')}")
            st.markdown(f"**Platform Type**: {trade_record.get('platform_type', 'N/A')}")
            st.markdown(f"**Cleared**: {trade_record.get('cleared', 'N/A')}")
        
        with col2:
            st.markdown(f"**CFTC Status**: {comp_record['cftc_status']}")
            st.markdown(f"**EMIR Status**: {comp_record['emir_status']}")
            st.markdown(f"**Classification**: {comp_record.get('classification_note', 'N/A')}")

# ============================================================================
# WRITTEN INTERPRETATION (2-3 paragraphs)
# ============================================================================
st.header("📝 Written Interpretation of Results")

interpretation = """
### Key Findings

**1. The Compliance Paradox: Data Quality is Destiny**

The portfolio reveals a critical pattern: regulatory compliance cannot be achieved without pristine identity data. 
Even with the expanded portfolio of 33 trades, only a tiny fraction achieves compliance (e.g., T017, T021). 
This disparity traces directly to LEI validation failures. Eight counterparty LEIs appear in the dataset, but only three 
pass ISO 7064 MOD 97-10 check digits. Trades T013, T017, and T021 satisfy LEI requirements; T017 is the sole CFTC-compliant 
trade because T013 and T021 fail on date-format issues (T013 has execution_timestamp as date-only, not ISO 8601 UTC; 
T021 has maturity_date "9999-99-99"). **Implication**: Even with correct business logic, a compliance engine cannot 
report trades if counterparties lack valid LEIs. This creates a hidden prerequisite: every market participant must 
maintain a current LEI registration.

**2. The Jurisdictional Asymmetry: Prediction Contracts as a Regulatory Arbitrage**

Trades T026, T027, and T028 expose the central thesis of Module 4: the same economic transaction generates 
completely different compliance outcomes. T026 (Kalshi, CFTC DCM) and T028 (also Kalshi, EU FinTech participant) 
both report CFTC status CONDITIONAL—indicating the CFTC's ANPR (91 FR 12516) classification is still in progress. 
Simultaneously, both show EMIR status NOT_APPLICABLE because Germany's Glücksspielstaatsvertrag (GlüStV 2021) 
classifies prediction contracts as gambling, outside derivatives regulation entirely. T027 (Polymarket, offshore via VPN) 
shows NOT_APPLICABLE under both regimes: not a CFTC-regulated DCM, and not reportable to EMIR because the offshore 
platform and VPN access place it outside regulated trading venues. **The engine reveals the gap**: 13 billion USD 
in notional monthly volume (Kalshi, March 2026) flows through instruments that generate zero regulatory visibility. 
A compliant reporting system cannot accept what the regulator has not yet decided is in scope.

**3. Recommendations for the Compliance Team**

Three immediate priorities emerge from the engine's output: (1) **LEI validation infrastructure**: Establish a 
pre-trade check that validates counterparty LEI check digits against GLEIF before trade execution, eliminating the 
post-facto discovery of invalid LEIs in compliance reporting. (2) **Timestamp standardization**: Enforce ISO 8601 UTC 
format at the point of trade capture, not at reporting time. The cost of correction in post-trade compliance is 
audit risk and delayed reporting. (3) **Event contract classification roadmap**: As the CFTC issues the prediction 
market rulemaking, the reporting engine must be updated incrementally. The current NOT_APPLICABLE status for T026 
and T028 will shift to CONDITIONAL or COMPLIANT once the CFTC designates which event-contract platforms fall within 
the derivatives regime. Monitoring the CFTC ANPR (RIN 3038-AF65) is now a compliance-operations dependency.
"""

st.markdown(interpretation)

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
st.divider()
st.header("📊 Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_trades = len(df_compliance)
    st.metric("Total Trades", total_trades)

with col2:
    compliant_cftc = (df_compliance['cftc_status'] == 'COMPLIANT').sum()
    st.metric("CFTC Compliant", compliant_cftc, f"{compliant_cftc/total_trades*100:.1f}%")

with col3:
    compliant_emir = (df_compliance['emir_status'] == 'COMPLIANT').sum()
    st.metric("EMIR Compliant", compliant_emir, f"{compliant_emir/total_trades*100:.1f}%")

with col4:
    novel_trades = len([t for t in compliance_data if t.get('classification_flag') == 'NOVEL_INSTRUMENT_NO_TAXONOMY'])
    st.metric("Novel Instruments", novel_trades)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown("""
---
**Dashboard Information**  
- Data Source: `output/compliance_report.json` + `data/trades.json`
- Regimes: CFTC, EMIR Refit (EU)
- Dashboard Version: 1.0  
- Generated: 2026-05-17
""")
