"""
Islamic Banking Regulatory Compliance & Risk Monitoring Tool
=============================================================
Streamlit application monitoring dual-regulatory compliance for Islamic banks
in Pakistan: SBP conventional requirements + Shariah Governance Framework
(AAOIFI, IFSB-16).

Run with:  streamlit run app.py
"""

import json
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

# --------------------------------------------------------------------------- #
# PAGE CONFIG & THEME
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Islamic Banking Compliance & Risk Monitor",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

PURPLE_DARK = "#2E1065"
PURPLE = "#5B21B6"
PURPLE_LIGHT = "#8B5CF6"
GOLD = "#F5C518"
CREAM = "#FAF7F2"

CUSTOM_CSS = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, #1E1B4B 0%, #2E1065 50%, #4C1D95 100%);
    }}
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {PURPLE_DARK} 0%, #1E1B4B 100%);
    }}
    section[data-testid="stSidebar"] * {{
        color: {CREAM} !important;
    }}
    .main-header {{
        background: linear-gradient(90deg, {PURPLE_DARK}, {PURPLE});
        padding: 1.5rem 2rem;
        border-radius: 16px;
        border: 2px solid {GOLD};
        box-shadow: 0 8px 32px rgba(245, 197, 24, 0.15);
        margin-bottom: 1.5rem;
        text-align: center;
    }}
    .main-header h1 {{
        color: {GOLD};
        margin: 0;
        font-family: 'Georgia', serif;
        font-size: 2.2rem;
        letter-spacing: 1px;
    }}
    .main-header p {{
        color: {CREAM};
        margin: 0.4rem 0 0 0;
        font-size: 1rem;
        opacity: 0.9;
    }}
    .arabic-ornament {{
        color: {GOLD};
        font-size: 1.4rem;
        letter-spacing: 8px;
        text-align: center;
        margin: 0.3rem 0;
    }}
    .metric-card {{
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(245, 197, 24, 0.3);
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        height: 100%;
    }}
    .metric-card h3 {{
        color: {GOLD};
        font-size: 0.95rem;
        margin: 0 0 0.6rem 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .metric-card .big-value {{
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0.3rem 0;
    }}
    .metric-card p, .metric-card li {{
        color: {CREAM};
    }}
    .stExpander {{
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(245, 197, 24, 0.25) !important;
        border-radius: 12px !important;
        margin-bottom: 0.6rem;
    }}
    .stExpander summary {{
        color: {GOLD} !important;
        font-weight: 600 !important;
    }}
    .stExpander p, .stExpander label, .stExpander div {{
        color: {CREAM};
    }}
    div[data-testid="stMarkdownContainer"] {{
        color: {CREAM};
    }}
    label {{
        color: {CREAM} !important;
    }}
    .stButton > button {{
        background: linear-gradient(90deg, {GOLD}, #E0A800);
        color: {PURPLE_DARK};
        font-weight: 700;
        border: none;
        padding: 0.6rem 1.6rem;
        border-radius: 10px;
        transition: transform 0.15s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(245, 197, 24, 0.4);
        color: {PURPLE_DARK};
    }}
    .footer {{
        text-align: center;
        padding: 1rem;
        color: {CREAM};
        opacity: 0.75;
        font-size: 0.85rem;
        border-top: 1px solid rgba(245, 197, 24, 0.3);
        margin-top: 2rem;
    }}
    .stDataFrame {{
        background: rgba(255,255,255,0.95);
        border-radius: 10px;
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# KRI DEFINITIONS (19 indicators)
# --------------------------------------------------------------------------- #
# Each KRI specifies: name, unit, weight, regulatory reference, category,
# input config, and a `classify(value) -> "Low"|"Medium"|"High"|"Critical"`
# function based on the threshold table.

def cls_kri1(v):  # Regulatory Autonomy Interference (%)
    if v == 0: return "Low"
    if 1 <= v <= 2: return "Medium"
    return "High"

def cls_kri2(v):  # Staff lacking Mandatory Shariah Training (%)
    if v < 5: return "Low"
    if 5 <= v <= 15: return "Medium"
    return "Critical"

def cls_kri3(v):  # Privileged Accounts without MFA (%)
    if v == 0: return "Low"
    if 1 <= v <= 10: return "Medium"
    return "Critical"

def cls_kri4(v):  # Patch Delay (days)
    if v < 3: return "Low"
    if 3 <= v <= 7: return "Medium"
    return "High"

def cls_kri5(v):  # Incident Reporting Delay (hours)
    if v < 2: return "Low"
    if 2 <= v <= 6: return "Medium"
    return "High"

def cls_kri6(v):  # Systems without Logging (%)
    if v <= 5: return "Low"
    if 6 <= v <= 19: return "Medium"
    return "High"

def cls_kri7(v):  # Unencrypted Databases (PII) (%) - higher coverage = lower risk
    if v == 100: return "Low"
    if 90 <= v <= 99: return "Medium"
    return "Critical"

def cls_kri8(v):  # SOC Response Time (minutes)
    if v < 15: return "Low"
    if 15 <= v <= 60: return "Medium"
    return "High"

def cls_kri9(v):  # Failed Login Attempts Spike (%)
    if v < 5: return "Low"
    if 5 <= v <= 20: return "Medium"
    return "High"

def cls_kri10(v):  # Vendors Not Risk Assessed (%)
    if v == 0: return "Low"
    if 1 <= v <= 10: return "Medium"
    return "High"

def cls_kri11(choice):  # Backup Recovery Test Frequency (interval)
    mapping = {
        "Quarterly": "Low",
        "Bi-annually": "Low",
        "Annually": "Medium",
        ">1 Year": "Critical",
    }
    return mapping.get(choice, "Critical")

def cls_kri12(v):  # Systems Not Risk Assessed (%)
    if v == 0: return "Low"
    if 1 <= v <= 5: return "Medium"
    return "High"

def cls_kri13(v):  # Data Retention Compliance (%) - higher = lower risk
    if v == 100: return "Low"
    if 90 <= v <= 99: return "Medium"
    return "High"

def cls_kri14(v):  # CISO Vacancy Duration (days)
    if v == 0: return "Low"
    if 1 <= v <= 30: return "Medium"
    return "Critical"

def cls_kri15(v):  # Shariah Board IT Approval Rate (%) - higher = lower risk
    if v > 90: return "Low"
    if 75 <= v <= 90: return "Medium"
    if 60 <= v <= 74: return "High"
    return "Critical"

def cls_kri16(v):  # Data Sovereignty Violations (count)
    if v == 0: return "Low"
    if v == 1: return "Medium"
    if 2 <= v <= 3: return "High"
    return "Critical"

def cls_kri17(v):  # Halal DR Vendor Compliance (%) - higher = lower risk
    if v == 100: return "Low"
    if 95 <= v <= 99: return "Medium"
    if 90 <= v <= 94: return "High"
    return "Critical"

def cls_kri18(v):  # Riba Detection Rate (%)
    if v < 0.1: return "Low"
    if 0.1 <= v <= 0.5: return "Medium"
    if 0.6 <= v <= 1.0: return "High"
    return "Critical"

def cls_kri19(v):  # Shariah Incident Disclosure Delay (hours)
    if v < 12: return "Low"
    if 12 <= v <= 48: return "Medium"
    if 49 <= v <= 96: return "High"
    return "Critical"


KRIS = [
    {"id": 1,  "name": "Regulatory Autonomy Interference Rate",      "unit": "%",       "weight": 0.05, "ref": "SBP IBD Circular",     "cls": cls_kri1,  "category": "A"},
    {"id": 2,  "name": "Staff lacking Mandatory Shariah Training",   "unit": "%",       "weight": 0.10, "ref": "SBP SGF / AAOIFI",     "cls": cls_kri2,  "category": "B"},
    {"id": 3,  "name": "Privileged Accounts without MFA",            "unit": "%",       "weight": 0.10, "ref": "SBP ETRMF",            "cls": cls_kri3,  "category": "C"},
    {"id": 4,  "name": "Patch Delay",                                "unit": "days",    "weight": 0.05, "ref": "SBP ETRMF",            "cls": cls_kri4,  "category": "D"},
    {"id": 5,  "name": "Incident Reporting Delay",                   "unit": "hours",   "weight": 0.10, "ref": "SBP IRMG",             "cls": cls_kri5,  "category": "E"},
    {"id": 6,  "name": "Systems without Logging",                    "unit": "%",       "weight": 0.05, "ref": "SBP ETRMF",            "cls": cls_kri6,  "category": "F"},
    {"id": 7,  "name": "Unencrypted Databases (PII coverage)",       "unit": "%",       "weight": 0.10, "ref": "SBP / PDPB",           "cls": cls_kri7,  "category": "G"},
    {"id": 8,  "name": "SOC Response Time",                          "unit": "minutes", "weight": 0.10, "ref": "SBP ETRMF",            "cls": cls_kri8,  "category": "E"},
    {"id": 9,  "name": "Failed Login Attempts Spike",                "unit": "%",       "weight": 0.05, "ref": "SBP ETRMF",            "cls": cls_kri9,  "category": "C"},
    {"id": 10, "name": "Vendors Not Risk Assessed",                  "unit": "%",       "weight": 0.05, "ref": "SBP Outsourcing",      "cls": cls_kri10, "category": "I"},
    {"id": 11, "name": "Backup Recovery Test Frequency",             "unit": "interval","weight": 0.10, "ref": "SBP BCP Guidelines",   "cls": cls_kri11, "category": "H"},
    {"id": 12, "name": "Systems Not Risk Assessed",                  "unit": "%",       "weight": 0.05, "ref": "SBP ETRMF",            "cls": cls_kri12, "category": "I"},
    {"id": 13, "name": "Data Retention Compliance",                  "unit": "%",       "weight": 0.05, "ref": "SBP / PDPB",           "cls": cls_kri13, "category": "G"},
    {"id": 14, "name": "CISO Vacancy Duration",                      "unit": "days",    "weight": 0.05, "ref": "SBP Governance",       "cls": cls_kri14, "category": "A"},
    {"id": 15, "name": "Shariah Board IT Approval Rate",             "unit": "%",       "weight": 0.10, "ref": "SBP SGF / AAOIFI",     "cls": cls_kri15, "category": "A"},
    {"id": 16, "name": "Data Sovereignty Violations",                "unit": "count",   "weight": 0.10, "ref": "SBP Cloud Policy",     "cls": cls_kri16, "category": "G"},
    {"id": 17, "name": "Halal DR Vendor Compliance",                 "unit": "%",       "weight": 0.05, "ref": "AAOIFI / IFSB-16",     "cls": cls_kri17, "category": "H"},
    {"id": 18, "name": "Riba Detection Rate",                        "unit": "%",       "weight": 0.10, "ref": "AAOIFI Shariah Stds",  "cls": cls_kri18, "category": "J"},
    {"id": 19, "name": "Shariah Incident Disclosure Delay",          "unit": "hours",   "weight": 0.08, "ref": "IFSB-16 / SSB",        "cls": cls_kri19, "category": "J"},
]
KRI_BY_ID = {k["id"]: k for k in KRIS}

MULTIPLIER = {"Low": 0.25, "Medium": 0.50, "High": 0.75, "Critical": 1.00}

LEVEL_COLOR = {
    "Low":      "#16A34A",
    "Medium":   "#EAB308",
    "High":     "#F97316",
    "Critical": "#DC2626",
}
LEVEL_EMOJI = {"Low": "✅", "Medium": "⚠️", "High": "🔴", "Critical": "🚨"}
LEVEL_RANK  = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


# --------------------------------------------------------------------------- #
# SESSION STATE
# --------------------------------------------------------------------------- #
def default_values():
    return {
        1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 100.0, 8: 0.0,
        9: 0.0, 10: 0.0, 11: "Bi-annually", 12: 0.0, 13: 100.0, 14: 0.0,
        15: 100.0, 16: 0, 17: 100.0, 18: 0.0, 19: 0.0,
    }

if "values" not in st.session_state:
    st.session_state["values"] = default_values()
if "results" not in st.session_state:
    st.session_state["results"] = None


# --------------------------------------------------------------------------- #
# HEADER
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
    <div class="main-header">
        <div class="arabic-ornament">۞ ✦ ۞ ✦ ۞</div>
        <h1>🕌 Islamic Banking Compliance & Risk Monitor</h1>
        <p>SBP Regulations · Shariah Governance Framework · AAOIFI · IFSB-16</p>
        <div class="arabic-ornament">۞ ✦ ۞ ✦ ۞</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# SIDEBAR — BANK INFO + SAVE/LOAD
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## 🏦 Bank Information")
    bank_name = st.text_input("Bank Name", value="Meezan Islamic Bank")
    bank_type = st.selectbox(
        "Bank Type",
        ["Full-Fledged Islamic Bank", "Islamic Window of Conventional Bank"],
    )
    assessment_date = st.date_input("Assessment Date", value=date.today())
    assessor_name = st.text_input("Assessor Name", value="Compliance Officer")

    st.markdown("---")
    st.markdown("## 💾 Save / Load Assessment")

    # Save
    save_payload = {
        "bank_name": bank_name,
        "bank_type": bank_type,
        "assessment_date": str(assessment_date),
        "assessor_name": assessor_name,
        "values": {str(k): v for k, v in st.session_state["values"].items()},
    }
    st.download_button(
        "⬇️ Save Assessment (JSON)",
        data=json.dumps(save_payload, indent=2),
        file_name=f"assessment_{assessment_date}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("⬆️ Load Assessment", type=["json"])
    if uploaded is not None:
        try:
            loaded = json.load(uploaded)
            loaded_vals = loaded.get("values", {})
            new_vals = default_values()
            for k_str, v in loaded_vals.items():
                k = int(k_str)
                if k in new_vals:
                    new_vals[k] = v
            st.session_state["values"] = new_vals
            st.success("Assessment loaded. Scroll down and click Calculate.")
        except Exception as e:
            st.error(f"Failed to load file: {e}")


# --------------------------------------------------------------------------- #
# KRI INPUT SECTIONS
# --------------------------------------------------------------------------- #
st.markdown("## 📋 KRI Assessment Inputs")
st.caption("Enter current measured values for each Key Risk Indicator, then click **Calculate Risk Score**.")

vals = st.session_state["values"]

def num_input(kri_id, label, mn, mx, step, fmt=None):
    cur = vals.get(kri_id, 0)
    try:
        cur = float(cur)
    except Exception:
        cur = 0.0
    cur = max(mn, min(mx, cur))
    out = st.number_input(
        label, min_value=float(mn), max_value=float(mx),
        value=float(cur), step=float(step),
        key=f"kri_{kri_id}", format=fmt,
    )
    vals[kri_id] = out
    return out

# Section A — Governance & Independence
with st.expander("🏛️ Section A — Governance & Independence (KRIs 1, 14, 15)", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1: num_input(1,  "KRI 1 — Regulatory Autonomy Interference Rate (%)", 0, 20, 0.1)
    with c2: num_input(14, "KRI 14 — CISO Vacancy Duration (days)",             0, 365, 1)
    with c3: num_input(15, "KRI 15 — Shariah Board IT Approval Rate (%)",       0, 100, 1)

# Section B — Human Capital
with st.expander("👥 Section B — Human Capital (KRI 2)"):
    num_input(2, "KRI 2 — Staff lacking Mandatory Shariah Training (%)", 0, 100, 1)

# Section C — Access Control & Authentication
with st.expander("🔐 Section C — Access Control & Authentication (KRIs 3, 9)"):
    c1, c2 = st.columns(2)
    with c1: num_input(3, "KRI 3 — Privileged Accounts without MFA (%)", 0, 100, 1)
    with c2: num_input(9, "KRI 9 — Failed Login Attempts Spike (%)",     0, 200, 1)

# Section D — Vulnerability & Patch Management
with st.expander("🛡️ Section D — Vulnerability & Patch Management (KRI 4)"):
    num_input(4, "KRI 4 — Patch Delay (days)", 0, 90, 1)

# Section E — Incident Response
with st.expander("🚨 Section E — Incident Response (KRIs 5, 8, 19)"):
    c1, c2, c3 = st.columns(3)
    with c1: num_input(5,  "KRI 5 — Incident Reporting Delay (hours)",         0, 72, 0.5)
    with c2: num_input(8,  "KRI 8 — SOC Response Time (minutes)",              0, 300, 1)
    with c3: num_input(19, "KRI 19 — Shariah Incident Disclosure Delay (hrs)", 0, 168, 1)

# Section F — Logging & Monitoring
with st.expander("📊 Section F — Logging & Monitoring (KRI 6)"):
    num_input(6, "KRI 6 — Systems without Logging (%)", 0, 100, 1)

# Section G — Data Protection
with st.expander("🔒 Section G — Data Protection (KRIs 7, 13, 16)"):
    c1, c2, c3 = st.columns(3)
    with c1: num_input(7,  "KRI 7 — Encrypted PII Database Coverage (%)", 0, 100, 1)
    with c2: num_input(13, "KRI 13 — Data Retention Compliance (%)",      0, 100, 1)
    with c3: num_input(16, "KRI 16 — Data Sovereignty Violations (count)", 0, 10, 1)

# Section H — Business Continuity
with st.expander("♻️ Section H — Business Continuity (KRIs 11, 17)"):
    c1, c2 = st.columns(2)
    with c1:
        opts = ["Quarterly", "Bi-annually", "Annually", ">1 Year"]
        cur11 = vals.get(11, "Bi-annually")
        if cur11 not in opts:
            cur11 = "Bi-annually"
        choice = st.selectbox(
            "KRI 11 — Backup Recovery Test Frequency",
            opts, index=opts.index(cur11), key="kri_11",
        )
        vals[11] = choice
    with c2:
        num_input(17, "KRI 17 — Halal DR Vendor Compliance (%)", 0, 100, 1)

# Section I — Risk Management
with st.expander("📐 Section I — Risk Management (KRIs 10, 12)"):
    c1, c2 = st.columns(2)
    with c1: num_input(10, "KRI 10 — Vendors Not Risk Assessed (%)", 0, 100, 1)
    with c2: num_input(12, "KRI 12 — Systems Not Risk Assessed (%)", 0, 100, 1)

# Section J — Shariah Compliance
with st.expander("☪️ Section J — Shariah Compliance (KRI 18)"):
    num_input(18, "KRI 18 — Riba Detection Rate (%)", 0, 5, 0.01, fmt="%.2f")


# --------------------------------------------------------------------------- #
# CALCULATION
# --------------------------------------------------------------------------- #
def compute_results(values: dict):
    rows = []
    total = 0.0
    counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for kri in KRIS:
        v = values[kri["id"]]
        level = kri["cls"](v)
        mult = MULTIPLIER[level]
        contribution = kri["weight"] * mult * 100
        total += contribution
        counts[level] += 1
        rows.append({
            "ID": kri["id"],
            "KRI": kri["name"],
            "Value": v,
            "Unit": kri["unit"],
            "Weight (%)": round(kri["weight"] * 100, 1),
            "Risk Level": level,
            "Multiplier": mult,
            "Contribution": round(contribution, 2),
            "Reference": kri["ref"],
            "Status": LEVEL_EMOJI[level],
        })
    score = round(total, 2)
    if score <= 30:
        overall = "Low"
    elif score <= 55:
        overall = "Medium"
    elif score <= 75:
        overall = "High"
    else:
        overall = "Critical"
    return {
        "score": score,
        "overall": overall,
        "rows": rows,
        "counts": counts,
        "df": pd.DataFrame(rows),
    }


st.markdown("---")
calc_col, _ = st.columns([1, 4])
with calc_col:
    if st.button("🧮  Calculate Risk Score", use_container_width=True):
        try:
            for kri in KRIS:
                v = vals[kri["id"]]
                if isinstance(v, (int, float)) and v < 0:
                    raise ValueError(f"KRI {kri['id']} has a negative value.")
            st.session_state["results"] = compute_results(vals)
        except Exception as e:
            st.error(f"Calculation error: {e}")

results = st.session_state["results"]


# --------------------------------------------------------------------------- #
# DASHBOARD
# --------------------------------------------------------------------------- #
def gauge_figure(score: float):
    if score <= 30:
        bar_color = LEVEL_COLOR["Low"]
    elif score <= 55:
        bar_color = LEVEL_COLOR["Medium"]
    elif score <= 75:
        bar_color = LEVEL_COLOR["High"]
    else:
        bar_color = LEVEL_COLOR["Critical"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": GOLD, "size": 42}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": CREAM, "tickfont": {"color": CREAM}},
            "bar": {"color": bar_color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 2,
            "bordercolor": GOLD,
            "steps": [
                {"range": [0, 30],   "color": "rgba(22,163,74,0.35)"},
                {"range": [30, 55],  "color": "rgba(234,179,8,0.35)"},
                {"range": [55, 75],  "color": "rgba(249,115,22,0.35)"},
                {"range": [75, 100], "color": "rgba(220,38,38,0.45)"},
            ],
            "threshold": {
                "line": {"color": GOLD, "width": 4},
                "thickness": 0.85, "value": score,
            },
        },
    ))
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color=CREAM),
    )
    return fig


if results:
    st.markdown("## 📊 Risk Dashboard")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card"><h3>Overall Risk Score</h3>', unsafe_allow_html=True)
        st.plotly_chart(gauge_figure(results["score"]), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        lvl = results["overall"]
        color = LEVEL_COLOR[lvl]
        emoji = LEVEL_EMOJI[lvl]
        st.markdown(
            f"""
            <div class="metric-card">
                <h3>Risk Level</h3>
                <div style="font-size:4rem;">{emoji}</div>
                <div class="big-value" style="color:{color};">{lvl.upper()}</div>
                <p>Score: <b>{results['score']}</b> / 100</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        sorted_rows = sorted(
            results["rows"],
            key=lambda r: (-LEVEL_RANK[r["Risk Level"]], -r["Contribution"]),
        )
        top3 = sorted_rows[:3]
        items_html = ""
        for r in top3:
            c = LEVEL_COLOR[r["Risk Level"]]
            items_html += (
                f"<li style='margin-bottom:0.5rem;'>"
                f"<b>KRI {r['ID']}:</b> {r['KRI']}<br>"
                f"<small>Value: {r['Value']} {r['Unit']} · "
                f"<span style='color:{c}; font-weight:700;'>{r['Risk Level']}</span></small>"
                f"</li>"
            )
        st.markdown(
            f"""
            <div class="metric-card" style="text-align:left;">
                <h3 style="text-align:center;">Top 3 High-Risk Areas</h3>
                <ul style="padding-left:1.1rem; margin:0;">{items_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        c = results["counts"]
        compliant_pct = round(((c["Low"] + c["Medium"]) / 19) * 100, 1)
        st.markdown(
            f"""
            <div class="metric-card" style="text-align:left;">
                <h3 style="text-align:center;">Regulatory Summary</h3>
                <p>✅ Low: <b>{c['Low']}</b></p>
                <p>⚠️ Medium: <b>{c['Medium']}</b></p>
                <p>🔴 High: <b>{c['High']}</b></p>
                <p>🚨 Critical: <b>{c['Critical']}</b></p>
                <hr style="border-color:rgba(245,197,24,0.3);">
                <p style="text-align:center; font-size:1.3rem;">
                    Compliant: <b style="color:{GOLD};">{compliant_pct}%</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------- Compliance Status Table ---------------- #
    st.markdown("## 📑 Compliance Status Table")
    filt = st.selectbox(
        "Filter by Risk Level",
        ["All", "Low", "Medium", "High", "Critical"],
        index=0,
    )
    df = results["df"][["ID", "KRI", "Value", "Unit", "Risk Level", "Reference", "Status"]].copy()
    if filt != "All":
        df = df[df["Risk Level"] == filt]

    def color_level(val):
        return f"color: {LEVEL_COLOR.get(val, '#000')}; font-weight: 700;"

    styled = df.style.map(color_level, subset=["Risk Level"])
    st.dataframe(styled, use_container_width=True, height=520)
    
    # ---------------- PDF Export ---------------- #
    def build_pdf() -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        def mcell(text, h=5, font=None):
            if font:
                pdf.set_font(*font)
            pdf.set_x(pdf.l_margin)
            usable = pdf.w - pdf.l_margin - pdf.r_margin
            pdf.multi_cell(usable, h, str(text))

        # Title bar
        pdf.set_fill_color(46, 16, 101)
        pdf.rect(0, 0, 210, 28, "F")
        pdf.set_text_color(245, 197, 24)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_xy(10, 8)
        pdf.cell(0, 8, "Islamic Banking Compliance & Risk Report", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(10)
        pdf.cell(0, 6, "SBP - Shariah Governance Framework - AAOIFI - IFSB-16", ln=True)

        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Bank Information", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Bank Name: {bank_name}", ln=True)
        pdf.cell(0, 6, f"Bank Type: {bank_type}", ln=True)
        pdf.cell(0, 6, f"Assessment Date: {assessment_date}", ln=True)
        pdf.cell(0, 6, f"Assessor: {assessor_name}", ln=True)
        pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Overall Risk Assessment", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 6, f"Total Risk Score: {results['score']} / 100", ln=True)
        pdf.cell(0, 6, f"Overall Risk Level: {results['overall'].upper()}", ln=True)
        cnt = results["counts"]
        pdf.cell(0, 6, f"Distribution -> Low: {cnt['Low']} | Medium: {cnt['Medium']} | High: {cnt['High']} | Critical: {cnt['Critical']}", ln=True)

        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "KRI Summary", ln=True)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(91, 33, 182)
        pdf.set_text_color(255, 255, 255)
        widths = [10, 78, 28, 22, 22, 30]
        headers = ["#", "KRI", "Value", "Weight%", "Level", "Reference"]
        pdf.set_x(pdf.l_margin)
        for w, h in zip(widths, headers):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        for r in results["rows"]:
            row = [
                str(r["ID"]),
                r["KRI"][:55],
                f"{r['Value']} {r['Unit']}",
                f"{r['Weight (%)']}",
                r["Risk Level"],
                r["Reference"][:22],
            ]
            pdf.set_x(pdf.l_margin)
            for w, txt in zip(widths, row):
                pdf.cell(w, 6, str(txt), border=1)
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Top 3 High-Risk Areas", ln=True)
        sorted_rows_pdf = sorted(
            results["rows"],
            key=lambda r: (-LEVEL_RANK[r["Risk Level"]], -r["Contribution"]),
        )
        recs_per_level = {
            "Low":      "Maintain monitoring; document control evidence.",
            "Medium":   "Schedule remediation review within 90 days.",
            "High":     "Escalate to CISO; remediate within 30 days.",
            "Critical": "Immediate remediation; notify SBP / SSB within 24 hours.",
        }
        for r in sorted_rows_pdf[:3]:
            mcell(f"KRI {r['ID']} - {r['KRI']} ({r['Risk Level']})", h=6, font=("Helvetica", "B", 10))
            mcell(f"   Current Value: {r['Value']} {r['Unit']}", h=5, font=("Helvetica", "", 9))
            mcell(f"   Recommendation: {recs_per_level[r['Risk Level']]}", h=5)
            pdf.ln(1)

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Overall Recommendation", ln=True)
        overall_recs = {
            "Low":      "Continue monitoring. Maintain current controls.",
            "Medium":   "Review medium-risk KRIs within 90 days.",
            "High":     "Management review required within 30 days. Escalate to CISO.",
            "Critical": "Immediate action required. Notify SBP and SSB within 24 hours.",
        }
        mcell(overall_recs[results["overall"]], h=6, font=("Helvetica", "", 10))

        pdf.ln(4)
        pdf.set_text_color(100, 100, 100)
        mcell(
            "Disclaimer: This tool is for educational purposes. For actual regulatory "
            "compliance, consult SBP and SSB guidelines.",
            h=4,
            font=("Helvetica", "I", 8),
        )

        out = pdf.output(dest="S")
        if isinstance(out, str):
            return out.encode("latin-1")
        return bytes(out)

    st.markdown("## 📄 Export")
    try:
        pdf_bytes = build_pdf()
        st.download_button(
            "⬇️  Export Report as PDF",
            data=pdf_bytes,
            file_name=f"compliance_report_{assessment_date}.pdf",
            mime="application/pdf",
            use_container_width=False,
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")

else:
    st.info("👆 Enter your KRI values above and click **Calculate Risk Score** to view the dashboard.")


# --------------------------------------------------------------------------- #
# FOOTER
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="footer">
        🕌 <b>Disclaimer:</b> This tool is for educational purposes.
        For actual regulatory compliance, consult SBP and SSB guidelines.<br>
        © Islamic Banking Compliance Monitor · Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
