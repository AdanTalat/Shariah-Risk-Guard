import json
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

# ------------------------------------------------------------------ #
# PAGE CONFIG + THEME
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="Islamic Banking Compliance Monitor",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

PURPLE_DARK = "#2e1065"
PURPLE      = "#5b21b6"
PURPLE_SOFT = "#7c3aed"
GOLD        = "#d4af37"
GOLD_SOFT   = "#f5d97a"
BG_CARD     = "#1f0a4d"

st.markdown(f"""
<style>
.stApp {{
    background: linear-gradient(135deg, {PURPLE_DARK} 0%, {PURPLE} 100%);
    color: #f5f5f5;
}}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {PURPLE_DARK} 0%, #1a0640 100%);
    border-right: 2px solid {GOLD};
}}
section[data-testid="stSidebar"] * {{ color: #f5f5f5 !important; }}
h1, h2, h3, h4 {{ color: {GOLD} !important; font-family: Georgia, serif; }}
.block-container {{ padding-top: 1.5rem; }}
div[data-testid="stExpander"] {{
    background: rgba(255,255,255,0.05);
    border: 1px solid {GOLD};
    border-radius: 8px;
    margin-bottom: 8px;
}}
div[data-testid="stExpander"] summary {{ color: {GOLD_SOFT} !important; font-weight: 600; }}
.stButton>button {{
    background: linear-gradient(90deg, {GOLD} 0%, {GOLD_SOFT} 100%);
    color: {PURPLE_DARK};
    font-weight: 700;
    border: none;
    border-radius: 6px;
    padding: 0.6rem 1.4rem;
}}
.stButton>button:hover {{ filter: brightness(1.1); transform: translateY(-1px); }}
.stDownloadButton>button {{
    background: linear-gradient(90deg, {GOLD} 0%, {GOLD_SOFT} 100%);
    color: {PURPLE_DARK}; font-weight: 700; border: none; border-radius: 6px;
}}
.risk-box {{
    padding: 1.2rem; border-radius: 12px; text-align: center;
    font-size: 1.6rem; font-weight: 800; color: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4);
}}
.domain-pill {{
    padding: 6px 10px; border-radius: 6px; margin: 3px 0;
    color: white; font-weight: 600; font-size: 0.9rem;
}}
.shariah-warning {{
    background: #7f1d1d; border: 2px solid {GOLD}; padding: 1rem;
    border-radius: 10px; color: {GOLD_SOFT}; font-weight: 700;
    text-align: center;
}}
.footer {{
    text-align: center; padding: 1.2rem; margin-top: 2rem;
    border-top: 1px solid {GOLD}; color: {GOLD_SOFT}; font-size: 0.85rem;
}}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# KRI METADATA
# ------------------------------------------------------------------ #
KRI_META = {
    1:  ("Regulatory Autonomy Interference Rate",   "%",       "Percentage of political interventions",      0.0, 20.0, 0.1, "number"),
    2:  ("Staff lacking Mandatory Shariah Training","%",       "Percentage of staff lacking Shariah training",0.0, 100.0, 1.0, "number"),
    3:  ("Privileged Accounts without MFA",         "%",       "Percentage of privileged accounts without MFA",0.0,100.0,1.0,"number"),
    4:  ("Patch Delay",                             "days",    "Average patch delay in days",                 0.0, 90.0, 1.0, "number"),
    5:  ("Incident Reporting Delay",                "hours",   "Incident reporting delay in hours",           0.0, 72.0, 0.5, "number"),
    6:  ("Systems without Logging",                 "%",       "Percentage of systems without logging",       0.0,100.0,1.0,"number"),
    7:  ("Encrypted Databases",                     "%",       "Percentage of encrypted databases",           0.0,100.0,1.0,"number"),
    8:  ("SOC Response Time",                       "min",     "SOC response time in minutes",                0.0,300.0,1.0,"number"),
    9:  ("Failed Login Attempts Spike",             "%",       "Percentage spike in failed logins",           0.0,200.0,1.0,"number"),
    10: ("Vendors Not Risk Assessed",               "%",       "Percentage of vendors not risk assessed",     0.0,100.0,1.0,"number"),
    11: ("Backup Recovery Test Frequency",          "interval","Backup test cadence",                         0,   0,   0,   "select"),
    12: ("Systems Not Risk Assessed",               "%",       "Percentage of systems not risk assessed",     0.0,100.0,1.0,"number"),
    13: ("Data Retention Compliance",               "%",       "Percentage of data retention compliance",     0.0,100.0,1.0,"number"),
    14: ("CISO Vacancy Duration",                   "days",    "Days since CISO position vacant",             0,  365,  1,   "number"),
    15: ("Shariah Board IT Approval Rate",          "%",       "Percentage of IT systems with SSB approval",  0.0,100.0,1.0,"number"),
    16: ("Data Sovereignty Violations",             "count",   "Number of data sovereignty violations",       0,   10,  1,   "number"),
    17: ("Halal DR Vendor Compliance",              "%",       "Percentage of Halal DR vendor compliance",    0.0,100.0,1.0,"number"),
    18: ("Riba Detection Rate",                     "%",       "Percentage of transactions flagged for riba", 0.0, 5.0, 0.01,"number"),
    19: ("Shariah Incident Disclosure Delay",       "hours",   "Shariah incident disclosure delay in hours",  0.0,168.0,1.0,"number"),
}

DOMAINS = {
    'Governance':          [1, 14],
    'Human Capital':       [2],
    'Access Control':      [3, 9],
    'Vulnerability':       [4],
    'Incident Response':   [5, 8],
    'Logging':             [6],
    'Data Protection':     [7, 13, 16],
    'Business Continuity': [11, 17],
    'Risk Management':     [10, 12],
    'Shariah':             [2, 15, 16, 17, 18, 19],
}

DOMAIN_SECTIONS = [
    ("A. Governance",          [1, 14]),
    ("B. Human Capital",       [2]),
    ("C. Access Control",      [3, 9]),
    ("D. Vulnerability",       [4]),
    ("E. Incident Response",   [5, 8, 19]),
    ("F. Logging",             [6]),
    ("G. Data Protection",     [7, 13, 16]),
    ("H. Business Continuity", [11, 17]),
    ("I. Risk Management",     [10, 12]),
    ("J. Shariah Integrity",   [15, 18]),
]

RISK_TO_VALUE = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
RISK_COLORS = {
    'Low':      '#28a745',
    'Medium':   '#ffc107',
    'High':     '#fd7e14',
    'Critical': '#dc3545',
    'Zero':     '#7f1d1d',
}
SCORE_COLORS = {0: '#7f1d1d', 1: '#28a745', 2: '#ffc107', 3: '#fd7e14', 4: '#dc3545'}

# ------------------------------------------------------------------ #
# RISK CLASSIFICATION (per spec)
# ------------------------------------------------------------------ #
def get_kri_risk_level(kri_id, value):
    if kri_id == 1:
        if value == 0: return 'Low'
        elif value <= 2: return 'Medium'
        else: return 'High'
    elif kri_id == 2:
        if value < 5: return 'Low'
        elif value <= 15: return 'Medium'
        else: return 'Critical'
    elif kri_id == 3:
        if value == 0: return 'Low'
        elif value <= 10: return 'Medium'
        else: return 'Critical'
    elif kri_id == 4:
        if value < 3: return 'Low'
        elif value <= 7: return 'Medium'
        else: return 'High'
    elif kri_id == 5:
        if value < 2: return 'Low'
        elif value <= 6: return 'Medium'
        else: return 'High'
    elif kri_id == 6:
        if value <= 5: return 'Low'
        elif value <= 19: return 'Medium'
        else: return 'High'
    elif kri_id == 7:
        if value == 100: return 'Low'
        elif value >= 90: return 'Medium'
        else: return 'Critical'
    elif kri_id == 8:
        if value < 15: return 'Low'
        elif value <= 60: return 'Medium'
        else: return 'High'
    elif kri_id == 9:
        if value < 5: return 'Low'
        elif value <= 20: return 'Medium'
        else: return 'High'
    elif kri_id == 10:
        if value == 0: return 'Low'
        elif value <= 10: return 'Medium'
        else: return 'High'
    elif kri_id == 11:
        if value == 'Quarterly': return 'Low'
        elif value == 'Bi-annually': return 'Low'
        elif value == 'Annually': return 'Medium'
        else: return 'Critical'
    elif kri_id == 12:
        if value == 0: return 'Low'
        elif value <= 5: return 'Medium'
        else: return 'High'
    elif kri_id == 13:
        if value == 100: return 'Low'
        elif value >= 90: return 'Medium'
        else: return 'High'
    elif kri_id == 14:
        if value == 0: return 'Low'
        elif value <= 30: return 'Medium'
        else: return 'Critical'
    elif kri_id == 15:
        if value > 90: return 'Low'
        elif value >= 75: return 'Medium'
        elif value >= 60: return 'High'
        else: return 'Critical'
    elif kri_id == 16:
        if value == 0: return 'Low'
        elif value == 1: return 'Medium'
        elif value <= 3: return 'High'
        else: return 'Critical'
    elif kri_id == 17:
        if value == 100: return 'Low'
        elif value >= 95: return 'Medium'
        elif value >= 90: return 'High'
        else: return 'Critical'
    elif kri_id == 18:
        if value < 0.1: return 'Low'
        elif value <= 0.5: return 'Medium'
        elif value <= 1: return 'High'
        else: return 'Critical'
    elif kri_id == 19:
        if value < 12: return 'Low'
        elif value <= 48: return 'Medium'
        elif value <= 96: return 'High'
        else: return 'Critical'
    return 'Low'


def calculate_domain_scores(kri_risk_levels):
    domain_scores = {}
    for domain, kri_list in DOMAINS.items():
        values = [RISK_TO_VALUE[kri_risk_levels[k]] for k in kri_list]
        domain_scores[domain] = max(values)

    shariah_kris = DOMAINS['Shariah']
    if any(kri_risk_levels[k] == 'Critical' for k in shariah_kris):
        domain_scores['Shariah'] = 0
    return domain_scores


def determine_overall_risk(domain_scores):
    if domain_scores['Shariah'] == 0:
        return 'CRITICAL'
    for d, s in domain_scores.items():
        if d != 'Shariah' and s == 4:
            return 'CRITICAL'
    high_count = sum(1 for s in domain_scores.values() if s == 3)
    medium_count = sum(1 for s in domain_scores.values() if s == 2)
    if high_count >= 3:   return 'HIGH'
    elif high_count >= 1: return 'HIGH'
    elif medium_count >= 3: return 'MEDIUM'
    else: return 'LOW'


def calculate_numeric_score(domain_scores):
    high_count = sum(1 for s in domain_scores.values() if s == 3)
    critical_count = sum(1 for s in domain_scores.values() if s == 4)
    shariah_zero = 1 if domain_scores['Shariah'] == 0 else 0
    numeric = 100 - (high_count * 15) - (critical_count * 30) - (shariah_zero * 50)
    return max(0, min(100, numeric))


# ------------------------------------------------------------------ #
# SIDEBAR
# ------------------------------------------------------------------ #
st.sidebar.markdown(f"<h2 style='color:{GOLD};'>🕌 Bank Information</h2>", unsafe_allow_html=True)

bank_name     = st.sidebar.text_input("Bank Name", value="Meezan Bank Ltd")
bank_type     = st.sidebar.selectbox("Bank Type",
                    ["Full-Fledged Islamic Bank", "Islamic Window of Conventional Bank"])
assess_date   = st.sidebar.date_input("Assessment Date", value=date.today())
assessor_name = st.sidebar.text_input("Assessor Name", value="")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='color:{GOLD};'>💾 Save / Load</h3>", unsafe_allow_html=True)

uploaded = st.sidebar.file_uploader("Load previous assessment (JSON)", type=["json"])
loaded_data = None
if uploaded is not None:
    try:
        loaded_data = json.loads(uploaded.read().decode("utf-8"))
        st.sidebar.success("Assessment loaded.")
    except Exception as e:
        st.sidebar.error(f"Invalid file: {e}")

# ------------------------------------------------------------------ #
# HEADER
# ------------------------------------------------------------------ #
st.markdown(f"""
<div style='text-align:center; padding: 1rem; border:2px solid {GOLD}; border-radius:12px;
            background: rgba(0,0,0,0.25); margin-bottom: 1rem;'>
  <h1 style='margin:0;'>🕌 Islamic Banking Compliance & Risk Monitor</h1>
  <p style='color:{GOLD_SOFT}; margin:0;'>Domain-Worst Risk Model · SBP + AAOIFI + IFSB-16</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
# KRI INPUTS
# ------------------------------------------------------------------ #
st.markdown("## 📋 KRI Assessment Inputs")
kri_values = {}

def default_for(kri_id):
    if loaded_data and "kri_values" in loaded_data:
        v = loaded_data["kri_values"].get(str(kri_id))
        if v is not None:
            if kri_id == 11: return v
            try: return float(v)
            except: return v
    if kri_id == 11: return "Quarterly"
    return 0.0

for section_title, kri_ids in DOMAIN_SECTIONS:
    with st.expander(f"**{section_title}**", expanded=(section_title.startswith("A"))):
        cols = st.columns(min(3, len(kri_ids)))
        for i, kid in enumerate(kri_ids):
            name, unit, helptxt, mn, mx, step, kind = KRI_META[kid]
            with cols[i % len(cols)]:
                label = f"KRI #{kid}: {name} ({unit})"
                if kind == "select":
                    options = ["Quarterly", "Bi-annually", "Annually", ">1 Year"]
                    dflt = default_for(kid)
                    if dflt not in options: dflt = "Quarterly"
                    kri_values[kid] = st.selectbox(label, options,
                                                   index=options.index(dflt), help=helptxt)
                else:
                    kri_values[kid] = st.number_input(
                        label,
                        min_value=float(mn), max_value=float(mx),
                        value=float(default_for(kid)),
                        step=float(step), help=helptxt,
                    )

st.markdown("")
calc_col, save_col = st.columns([1, 1])
with calc_col:
    calc_clicked = st.button("🧮 Calculate Risk Assessment", use_container_width=True)
with save_col:
    save_clicked = st.button("💾 Prepare Save File", use_container_width=True)

# ------------------------------------------------------------------ #
# COMPUTE + RENDER
# ------------------------------------------------------------------ #
def render_results(kri_values):
    # Validation
    for kid, val in kri_values.items():
        if isinstance(val, (int, float)) and val < 0:
            st.error(f"KRI #{kid} cannot be negative.")
            return None

    kri_levels = {k: get_kri_risk_level(k, v) for k, v in kri_values.items()}
    domain_scores = calculate_domain_scores(kri_levels)
    overall = determine_overall_risk(domain_scores)
    numeric = calculate_numeric_score(domain_scores)

    st.markdown("---")
    st.markdown("## 🎯 Results Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    overall_color = {
        'LOW': '#28a745', 'MEDIUM': '#ffc107',
        'HIGH': '#fd7e14', 'CRITICAL': '#dc3545'
    }[overall]
    overall_emoji = {'LOW': '✅', 'MEDIUM': '⚠️', 'HIGH': '🔴', 'CRITICAL': '🚨'}[overall]

    with c1:
        st.markdown("### Overall Risk")
        st.markdown(
            f"<div class='risk-box' style='background:{overall_color};'>"
            f"{overall_emoji}<br>{overall}</div>",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("### Numeric Score")
        gauge_color = ('#28a745' if numeric >= 80 else
                       '#ffc107' if numeric >= 60 else
                       '#fd7e14' if numeric >= 40 else '#dc3545')
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=numeric,
            number={'font': {'color': GOLD, 'size': 36}},
            gauge={
                'axis': {'range': [0, 100], 'tickcolor': GOLD_SOFT},
                'bar': {'color': gauge_color},
                'bgcolor': 'rgba(0,0,0,0)',
                'steps': [
                    {'range': [0, 40],   'color': '#7f1d1d'},
                    {'range': [40, 60],  'color': '#9a3412'},
                    {'range': [60, 80],  'color': '#92400e'},
                    {'range': [80, 100], 'color': '#14532d'},
                ],
                'threshold': {'line': {'color': GOLD, 'width': 3},
                              'thickness': 0.8, 'value': numeric},
            }))
        fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor='rgba(0,0,0,0)',
                          font={'color': GOLD_SOFT})
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        st.markdown("### Domain Scores")
        for d, s in domain_scores.items():
            color = SCORE_COLORS[s]
            label = "ZERO (Shariah)" if (d == 'Shariah' and s == 0) else f"Score: {s}"
            st.markdown(
                f"<div class='domain-pill' style='background:{color};'>"
                f"{d} — {label}</div>",
                unsafe_allow_html=True,
            )

    with c4:
        st.markdown("### Shariah Status")
        if domain_scores['Shariah'] == 0:
            st.markdown(
                "<div class='shariah-warning'>🚨 SHARIAH NON-COMPLIANCE DETECTED<br>"
                "Immediate SSB notification required (within 24h).</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='risk-box' style='background:{SCORE_COLORS[domain_scores['Shariah']]};'>"
                f"Shariah OK<br>Score: {domain_scores['Shariah']}</div>",
                unsafe_allow_html=True,
            )

    # Domain breakdown table
    st.markdown("---")
    st.markdown("## 📊 Domain Breakdown")
    risk_label_for_score = {0: 'CRITICAL (Shariah Zero)', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
    rows = []
    for d, kri_list in DOMAINS.items():
        s = domain_scores[d]
        rows.append({
            "Domain": d,
            "Score (0-4)": s,
            "Risk Level": risk_label_for_score[s],
            "KRIs": ", ".join(f"#{k}" for k in kri_list),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # KRI table
    st.markdown("## 🔍 All 19 KRIs")
    kri_rows = []
    for kid in range(1, 20):
        name, unit, *_ = KRI_META[kid]
        kri_rows.append({
            "#": kid, "KRI": name,
            "Value": kri_values[kid],
            "Unit": unit,
            "Risk": kri_levels[kid],
        })
    st.dataframe(pd.DataFrame(kri_rows), use_container_width=True, hide_index=True)

    # High-risk areas
    st.markdown("## ⚠️ High-Risk Areas")
    high_areas = [(d, s) for d, s in domain_scores.items() if s == 0 or s >= 3]
    if not high_areas:
        st.success("No high-risk domains detected. Maintain current controls.")
    else:
        for d, s in high_areas:
            if s == 0:
                st.error(f"🚨 **{d}** — SHARIAH ZERO: critical Islamic violation. "
                         "Notify SSB and SBP within 24h. Suspend affected Islamic products.")
            elif s == 4:
                st.error(f"🚨 **{d}** — CRITICAL (score 4). Immediate remediation required.")
            else:
                st.warning(f"🔴 **{d}** — HIGH (score 3). Escalate to CISO; remediation plan in 2 weeks.")

    # Recommendations
    st.markdown("## 📝 Compliance Recommendations")
    recs = {
        'LOW':      "Continue monitoring. Maintain current controls. Next assessment in 6 months.",
        'MEDIUM':   "Review medium-risk domains within 90 days. Develop remediation plan for domains with score ≥ 2.",
        'HIGH':     "Management review required within 30 days. Escalate to CISO and SSB. Remediation plan due in 2 weeks.",
        'CRITICAL': "Immediate action required. Notify SBP and SSB within 24 hours. Suspend affected Islamic products until remediation.",
    }
    st.info(recs[overall])

    return {
        "kri_values": kri_values,
        "kri_levels": kri_levels,
        "domain_scores": domain_scores,
        "overall": overall,
        "numeric": numeric,
        "rows": rows,
        "kri_rows": kri_rows,
        "high_areas": high_areas,
        "recommendation": recs[overall],
    }


# ------------------------------------------------------------------ #
# PDF EXPORT
# ------------------------------------------------------------------ #
def build_pdf(meta, result):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles['Title'],
                                 textColor=colors.HexColor(PURPLE_DARK), fontSize=18)
    h2 = ParagraphStyle("H2", parent=styles['Heading2'],
                        textColor=colors.HexColor(PURPLE), spaceAfter=6)
    body = styles['BodyText']

    story = []
    story.append(Paragraph("Islamic Banking Compliance Report", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Bank:</b> {meta['bank_name']}", body))
    story.append(Paragraph(f"<b>Type:</b> {meta['bank_type']}", body))
    story.append(Paragraph(f"<b>Assessment Date:</b> {meta['assess_date']}", body))
    story.append(Paragraph(f"<b>Assessor:</b> {meta['assessor_name'] or 'N/A'}", body))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Overall Result", h2))
    overall_tbl = Table([
        ["Overall Risk Level", result['overall']],
        ["Numeric Score (0-100)", f"{result['numeric']}"],
        ["Model", "Domain-Worst Risk Model"],
    ], colWidths=[60*mm, 100*mm])
    overall_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(PURPLE)),
        ('TEXTCOLOR',  (0, 0), (0, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(GOLD)),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(overall_tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Domain Scores", h2))
    dom_data = [["Domain", "Score", "Risk Level", "KRIs"]]
    for r in result['rows']:
        dom_data.append([r['Domain'], str(r['Score (0-4)']), r['Risk Level'], r['KRIs']])
    dom_tbl = Table(dom_data, colWidths=[45*mm, 20*mm, 50*mm, 45*mm])
    dom_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PURPLE_DARK)),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(dom_tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph("All 19 KRIs", h2))
    kri_data = [["#", "KRI", "Value", "Unit", "Risk"]]
    for r in result['kri_rows']:
        kri_data.append([str(r['#']), r['KRI'], str(r['Value']), r['Unit'], r['Risk']])
    kri_tbl = Table(kri_data, colWidths=[10*mm, 75*mm, 25*mm, 20*mm, 20*mm])
    kri_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PURPLE_DARK)),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(kri_tbl)
    story.append(PageBreak())

    story.append(Paragraph("Top High-Risk Areas", h2))
    if not result['high_areas']:
        story.append(Paragraph("No high-risk domains detected.", body))
    else:
        for d, s in result['high_areas'][:5]:
            tag = ("SHARIAH ZERO (Critical Islamic Violation)" if s == 0
                   else "CRITICAL" if s == 4 else "HIGH")
            story.append(Paragraph(f"<b>{d}</b> — {tag} (score {s})", body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Recommendation", h2))
    story.append(Paragraph(result['recommendation'], body))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>Disclaimer: This tool uses the Domain-Worst Risk Model. "
        "For actual regulatory compliance, consult SBP and SSB guidelines.</i>",
        body))
    doc.build(story)
    buf.seek(0)
    return buf


# ------------------------------------------------------------------ #
# MAIN FLOW
# ------------------------------------------------------------------ #
if "result" not in st.session_state:
    st.session_state.result = None

if calc_clicked:
    st.session_state.result = render_results(kri_values)
elif st.session_state.result is not None:
    st.session_state.result = render_results(kri_values)

if save_clicked:
    save_payload = {
        "bank_name": bank_name,
        "bank_type": bank_type,
        "assess_date": str(assess_date),
        "assessor_name": assessor_name,
        "kri_values": {str(k): v for k, v in kri_values.items()},
        "saved_at": datetime.now().isoformat(),
    }
    st.download_button(
        "⬇️ Download Assessment JSON",
        data=json.dumps(save_payload, indent=2),
        file_name=f"assessment_{bank_name.replace(' ', '_')}_{assess_date}.json",
        mime="application/json",
    )

if st.session_state.result is not None:
    st.markdown("---")
    st.markdown("## 📤 Export")
    meta = {
        "bank_name": bank_name, "bank_type": bank_type,
        "assess_date": str(assess_date), "assessor_name": assessor_name,
    }
    pdf_buf = build_pdf(meta, st.session_state.result)
    st.download_button(
        "📄 Export Report as PDF",
        data=pdf_buf,
        file_name=f"compliance_report_{bank_name.replace(' ', '_')}_{assess_date}.pdf",
        mime="application/pdf",
    )

    # Compare with loaded
    if loaded_data and "kri_values" in loaded_data:
        st.markdown("## 🔁 Comparison with Loaded Assessment")
        prev_kri = {int(k): v for k, v in loaded_data["kri_values"].items()}
        prev_levels = {k: get_kri_risk_level(k, v) for k, v in prev_kri.items()}
        prev_domains = calculate_domain_scores(prev_levels)
        prev_overall = determine_overall_risk(prev_domains)
        prev_numeric = calculate_numeric_score(prev_domains)
        cur = st.session_state.result
        delta = cur['numeric'] - prev_numeric
        trend = ("📈 Improvement" if delta > 0
                 else "📉 Deterioration" if delta < 0 else "➡️ No change")
        st.info(f"**Previous:** {prev_overall} (score {prev_numeric}) → "
                f"**Current:** {cur['overall']} (score {cur['numeric']}) — "
                f"{trend} ({delta:+d} pts)")

# ------------------------------------------------------------------ #
# FOOTER
# ------------------------------------------------------------------ #
st.markdown(
    "<div class='footer'>This tool uses the <b>Domain-Worst Risk Model</b>. "
    "For actual regulatory compliance, consult SBP and SSB guidelines.</div>",
    unsafe_allow_html=True,
)
