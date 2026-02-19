import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Robustness Dashboard", layout="wide")

# CSS BLINDATO
st.markdown("""
    <style>
    .main-title { font-size: 48px !important; font-weight: bold !important; color: #2E7D32 !important; margin-bottom: 0px !important; }
    .sub-title { font-size: 22px !important; color: #555555 !important; margin-bottom: 30px !important; }
    [data-testid="stMetricLabel"] { font-size: 24px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌱 Plan & Govern your Scope 3 journey</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Executive Strategy Tool - optimize your Reg Ag investment by maximizing climatic ROI</p>', unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("⚖️ Pesi Strategici (WHM)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.01, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.01, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.01, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)
anno_target = st.sidebar.select_slider("Orizzonte Temporale Target", options=[2026, 2027, 2028, 2029, 2030, 2035], value=2030)

st.sidebar.header("⏳ Dinamiche Temporali")
churn_rate = st.sidebar.slider("Tasso abbandono incentivi annuo (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 40) 

# --- DATA E LOGICA WHM ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 250, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 200, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.9, 'costo': 500, 'diff': 4},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.6, 'costo': 450, 'diff': 3},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5}
}
df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

def run_optimization(wi, wc, wd):
    d = df_p.copy()
    d['Imp_Val'] = ((-d['d_emiss'] + d['d_carb'] + LOSS_SOC_BASE_HA) * 0.8) # 20% safety buffer fisso
    # Normalizzazione lineare come da MCDA Index Tool
    d['S_Imp'] = (d['Imp_Val'] - d['Imp_Val'].min()) / (d['Imp_Val'].max() - d['Imp_Val'].min() + 0.01)
    d['S_Cost'] = (d['costo'].max() - d['costo']) / (d['costo'].max() - d['costo'].min() + 0.01)
    d['S_Diff'] = (5 - d['diff']) / (5 - 1 + 0.01)
    # Media Armonica Pesata (WHM) - Logica Cinelli
    d['Score'] = (wi+wc+wd) / ((wi/d['S_Imp'].clip(0.01)) + (wc/d['S_Cost'].clip(0.01)) + (wd/d['S_Diff'].clip(0.01)))
    
    # Allocazione Budget
    ha_alloc = {p: 0.0 for p in d.index}
    budget_res = budget_annuo
    for nome, row in d.sort_values(by='Score', ascending=False).iterrows():
        da_agg = min(budget_res / row['costo'], ETTARI_FILIERA - sum(ha_alloc.values()))
        if da_agg > 0:
            ha_alloc[nome] += da_agg
            budget_res -= da_agg * row['costo']
    return ha_alloc, d['Imp_Val']

# Esecuzione principale
ha_current, imp_vals = run_optimization(w_imp, w_cost, w_diff)
stock = sum(ha_current[p] * imp_vals[p] for p in ha_current)

# --- TRAIETTORIA ---
anni = list(range(2025, anno_target + 1))
traiettoria = [BASELINE_TOT_ANNUA]
curr_stock = 0
for a in anni[1:]:
    curr_stock = (curr_stock * (100-perdita_carb)/100 * (100-churn_rate)/100) + stock
    traiettoria.append(BASELINE_TOT_ANNUA - curr_stock)

# --- UI KPI ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ettari Programma", f"{int(sum(ha_current.values()))} ha")
c2.metric(f"CO2 Rimossa {anno_target}", f"{int(curr_stock)} t")

with c3:
    valore_roi = (budget_annuo - (budget_annuo - sum(ha_current[p]*df_p.at[p,'costo'] for p in ha_current))) / stock if stock > 0 else 0
    st.markdown(f'<div style="text-align:center;background:#f0f2f6;padding:10px;border-radius:10px;border:1px solid #ddd;"><p style="margin:0;font-size:18px;font-weight:bold;">ROI CLIMATICO</p><p style="margin:0;font-size:32px;font-weight:bold;color:#1a73e8;">{valore_roi:.2f} €</p><p style="margin:0;font-size:12px;">euro / tCO2 rimossa</p></div>', unsafe_allow_html=True)

c4.metric("Budget Residuo", f"€ {int(budget_annuo - sum(ha_current[p]*df_p.at[p,'costo'] for p in ha_current)):,}")

with c5:
    gap_val = traiettoria[-1] - (BASELINE_TOT_ANNUA * (1 - target_decarb/100))
    color = "#2E7D32" if gap_val <= 0 else "#D32F2F"
    st.markdown(f'<div style="text-align:center;background:#f0f2f6;padding:10px;border-radius:10px;border:2px solid {color};"><p style="margin:0;font-size:18px;font-weight:bold;">GAP AL TARGET</p><p style="margin:0;font-size:32px;font-weight:bold;color:{color};">{int(gap_val)} t</p><p style="margin:0;font-size:12px;font-weight:bold;color:{color};">{"SOTTO TARGET 🌱" if gap_val <=0 else "SOPRA TARGET ⚠️"}</p></div>', unsafe_allow_html=True)

st.markdown("---")

# --- ANALISI DI ROBUSTEZZA (CINELLI CHECK) ---
st.subheader("🧪 Cinelli Robustness Check (Sensitivity Analysis)")
expander = st.expander("Clicca per vedere come cambierebbe il piano variando i pesi del ±20%")
with expander:
    col_sens = st.columns(3)
    # Test CO2 +20%
    ha_plus_co2, _ = run_optimization(w_imp*1.2, w_cost, w_diff)
    # Test Costo +20%
    ha_plus_cost, _ = run_optimization(w_imp, w_cost*1.2, w_diff)
    # Test Facilità +20%
    ha_plus_diff, _ = run_optimization(w_imp, w_cost, w_diff*1.2)
    
    sens_df = pd.DataFrame({
        "Mix Attuale": ha_current,
        "Focus CO2 (+20%)": ha_plus_co2,
        "Focus Risparmio (+20%)": ha_plus_cost,
        "Focus Semplicità (+20%)": ha_plus_diff
    }).T
    st.bar_chart(sens_df)
    st.info("Se le barre rimangono simili tra i vari scenari, la tua strategia è 'ROBUSTA'.")

st.markdown("---")
l, r = st.columns([1.6, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni, y=traiettoria, mode='lines+markers', line=dict(color='green', width=4), name="Emissione Netta"))
    fig.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT_ANNUA * (1 - target_decarb/100)]*len(anni), line=dict(dash='dot', color='red'), name="Target"))
    st.plotly_chart(fig, use_container_width=True)

with r:
    st.subheader("📊 Mix Pratiche")
    labels = [p for p, ha in ha_current.items() if ha > 0]
    values = [ha for p, ha in ha_current.items() if ha > 0]
    st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)
