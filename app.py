import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Scope 3 Journey", layout="wide")

# CSS AGGIORNATO: Font più grandi e uniformità box
st.markdown("""
    <style>
    .main-title { font-size: 52px !important; font-weight: bold !important; color: #2E7D32 !important; }
    .sub-title { font-size: 24px !important; color: #555555 !important; margin-bottom: 30px !important; }
    
    /* Ingrandimento font Sidebar e Slider */
    .stSlider label, .stNumberInput label, .stSelectSlider label { font-size: 20px !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { width: 400px !important; }

    /* Stile Box KPI */
    .kpi-box {
        text-align: center; 
        padding: 15px; 
        background-color: #f0f2f6; 
        border-radius: 12px; 
        border: 1px solid #ddd; 
        height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label { margin:0; font-size: 20px !important; font-weight: bold; color: #1E1E1E; }
    .kpi-value { margin:0; font-size: 36px !important; font-weight: bold; }
    .kpi-sub { margin:0; font-size: 14px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# --- TITOLI ---
st.markdown('<p class="main-title">🌱 Plan & Govern your Scope 3 journey</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Executive Strategy Tool - optimize your Reg Ag investment by maximizing climatic ROI</p>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.01, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.01, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.01, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)
anno_target = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035], value=2030)

st.sidebar.header("⏳ Dinamiche Temporali")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 15)

# --- DATI E LOGICA ---
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
RESA_TOM_HA = 80 # ton/ha
PROD_TOT_TON = ETTARI_FILIERA * RESA_TOM_HA
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

def run_optimization(wi, wc, wd, s_buffer, p_min, t_pct):
    d = df_p.copy()
    d['Imp_Val'] = ((-d['d_emiss'] + d['d_carb'] + LOSS_SOC_BASE_HA) * (1 - s_buffer/100))
    d['S_Imp'] = (d['Imp_Val'] - d['Imp_Val'].min()) / (d['Imp_Val'].max() - d['Imp_Val'].min() + 0.01)
    d['S_Cost'] = (d['costo'].max() - d['costo']) / (d['costo'].max() - d['costo'].min() + 0.01)
    d['S_Diff'] = (5 - d['diff']) / (5 - 1 + 0.01)
    d['Score'] = (wi+wc+wd) / ((wi/d['S_Imp'].clip(0.01)) + (wc/d['S_Cost'].clip(0.01)) + (wd/d['S_Diff'].clip(0.01)))
    
    ha_alloc = {p: 0.0 for p in d.index}
    target_ton = BASELINE_TOT_ANNUA * (t_pct / 100)
    
    # Adozione spontanea
    pratiche_facili = d[d['diff'] <= 3].index
    if not pratiche_facili.empty:
        for p in pratiche_facili: ha_alloc[p] = (ETTARI_FILIERA * (p_min/100)) / len(pratiche_facili)

    # Allocazione Budget con STOP al target
    budget_disp = budget_annuo
    for nome, row in d.sort_values(by='Score', ascending=False).iterrows():
        beneficio_attuale = sum(ha_alloc[p] * d.at[p, 'Imp_Val'] for p in ha_alloc)
        if beneficio_attuale >= target_ton: break
        
        costo_attuale = sum(ha_alloc[p] * d.at[p, 'costo'] for p in ha_alloc)
        budget_rimanente = budget_disp - costo_attuale
        if budget_rimanente <= 0: break
        
        gap_co2 = target_ton - beneficio_attuale
        da_agg = min(gap_co2 / row['Imp_Val'], budget_rimanente / row['costo'], ETTARI_FILIERA - sum(ha_alloc.values()))
        ha_alloc[nome] += max(0, da_agg)

    usato = sum(ha_alloc[p] * d.at[p, 'costo'] for p in ha_alloc)
    return ha_alloc, d['Imp_Val'], budget_disp - usato

ha_current, imp_vals, budget_res = run_optimization(w_imp, w_cost, w_diff, safety_buffer, prob_minima, target_decarb)
beneficio_annuo = sum(ha_current[p] * imp_vals[p] for p in ha_current)
target_ton_annuo = BASELINE_TOT_ANNUA * (target_decarb / 100)
impronta_specifica = (BASELINE_TOT_ANNUA - beneficio_annuo) * 1000 / PROD_TOT_TON

# --- KPI BOXES ---
st.markdown("---")
cols = st.columns(6)

labels = ["Ettari Programma", f"CO2 Rimossa {anno_target}", "ROI Climatico", "Impronta 🍅", "Budget", "Gap Target"]
# Box 1: Ettari
cols[0].markdown(f'<div class="kpi-box"><p class="kpi-label">{labels[0]}</p><p class="kpi-value" style="color:#1E1E1E;">{int(sum(ha_current.values()))}</p><p class="kpi-sub">ettari totali</p></div>', unsafe_allow_html=True)
# Box 2: CO2
cols[1].markdown(f'<div class="kpi-box"><p class="kpi-label">{labels[1]}</p><p class="kpi-value" style="color:#1E1E1E;">{int(beneficio_annuo)}</p><p class="kpi-sub">tCO2e/anno</p></div>', unsafe_allow_html=True)
# Box 3: ROI
roi = (budget_annuo - budget_res) / beneficio_annuo if beneficio_annuo > 0 else 0
cols[2].markdown(f'<div class="kpi-box"><p class="kpi-label">{labels[2]}</p><p class="kpi-value" style="color:#1a73e8;">{roi:.2f} €</p><p class="kpi-sub">investimento/tCO2</p></div>', unsafe_allow_html=True)
# Box 4: Impronta Pomodoro
cols[3].markdown(f'<div class="kpi-box"><p class="kpi-label">{labels[3]}</p><p class="kpi-value" style="color:#E64A19;">{impronta_specifica:.2f}</p><p class="kpi-sub">kg CO2/ton</p></div>', unsafe_allow_html=True)

# Box 5: Budget Dinamico
gap_climatico = target_ton_annuo - beneficio_annuo
if gap_climatico > 0:
    val_b = gap_climatico * (budget_annuo/beneficio_annuo if beneficio_annuo > 0 else 150)
    col_b, lab_b = "#D32F2F", "BUDGET MANCANTE"
else:
    val_b = budget_res
    col_b, lab_b = "#2E7D32", "BUDGET RESIDUO"
cols[4].markdown(f'<div class="kpi-box" style="border: 2px solid {col_b};"><p class="kpi-label">{lab_b}</p><p class="kpi-value" style="color:{col_b};">€ {int(val_b):,}</p><p class="kpi-sub">vs limite annuo</p></div>', unsafe_allow_html=True)

# Box 6: Gap Target
col_g = "#2E7D32" if gap_climatico <= 0 else "#D32F2F"
cols[5].markdown(f'<div class="kpi-box" style="border: 2px solid {col_g};"><p class="kpi-label">GAP TARGET</p><p class="kpi-value" style="color:{col_g};">{int(gap_climatico)} t</p><p class="kpi-sub">{"OK 🌱" if gap_climatico <= 0 else "MANCANTE ⚠️"}</p></div>', unsafe_allow_html=True)

st.markdown("---")

# --- GRAFICI E TABELLA ---
l, r = st.columns([1.5, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni Net Scope 3")
    anni = list(range(2025, anno_target + 1))
    # Semplificazione traiettoria per visualizzazione immediata
    traiettoria = [BASELINE_TOT_ANNUA - (beneficio_annuo * (i/len(anni))) for i in range(len(anni))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni, y=traiettoria, mode='lines+markers', line=dict(color='green', width=4)))
    fig.update_layout(font=dict(size=18))
    st.plotly_chart(fig, use_container_width=True)

with r:
    st.subheader("📊 Mix Pratiche Ottimizzato")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ha_current.keys()), values=list(ha_current.values()), hole=.4)])
    fig_pie.update_layout(font=dict(size=16))
    st.plotly_chart(fig_pie, use_container_width=True)

st.write("### 🚜 Piano Operativo")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ha_current.items() if ha > 0}, orient='index', columns=['Superficie Target']))

st.markdown("---")
st.subheader("🧪 Robustness Check")
with st.expander("Analisi di Sensibilità (MCDA Robustness)"):
    h1, _, _ = run_optimization(w_imp*1.2, w_cost, w_diff, safety_buffer, prob_minima, target_decarb)
    h2, _, _ = run_optimization(w_imp, w_cost*1.2, w_diff, safety_buffer, prob_minima, target_decarb)
    sens_df = pd.DataFrame({"Attuale": ha_current, "Focus Impatto": h1, "Focus Costo": h2}).T
    st.bar_chart(sens_df)
