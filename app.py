import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Scope 3 Journey", layout="wide")

# CSS BLINDATO: Per mantenere i font stabili e i box coerenti
st.markdown("""
    <style>
    .main-title {
        font-size: 48px !important;
        font-weight: bold !important;
        color: #2E7D32 !important;
        margin-bottom: 0px !important;
        display: block;
    }
    .sub-title {
        font-size: 20px !important;
        color: #555555 !important;
        margin-bottom: 30px !important;
        display: block;
    }
    [data-testid="stMetricLabel"] {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #1E1E1E !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 40px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TITOLI ---
st.markdown('<p class="main-title">🌱 Plan & Govern your Scope 3 journey</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Executive Strategy Tool - optimize your Reg Ag investment by maximizing climatic ROI</p>', unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
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
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 15)

# --- DATABASE PRATICHE ---
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

# --- FUNZIONE DI OTTIMIZZAZIONE (MCDA - WHM) ---
def run_optimization(wi, wc, wd, s_buffer, p_min):
    d = df_p.copy()
    d['Imp_Val'] = ((-d['d_emiss'] + d['d_carb'] + LOSS_SOC_BASE_HA) * (1 - s_buffer/100))
    
    # Normalizzazione lineare
    d['S_Imp'] = (d['Imp_Val'] - d['Imp_Val'].min()) / (d['Imp_Val'].max() - d['Imp_Val'].min() + 0.01)
    d['S_Cost'] = (d['costo'].max() - d['costo']) / (d['costo'].max() - d['costo'].min() + 0.01)
    d['S_Diff'] = (5 - d['diff']) / (5 - 1 + 0.01)
    
    # Media Armonica Pesata (WHM)
    d['Score'] = (wi+wc+wd) / ((wi/d['S_Imp'].clip(0.01)) + (wc/d['S_Cost'].clip(0.01)) + (wd/d['S_Diff'].clip(0.01)))
    
    ha_alloc = {p: 0.0 for p in d.index}
    pratiche_facili = d[d['diff'] <= 3].index
    if not pratiche_facili.empty:
        ha_base = (ETTARI_FILIERA * (p_min/100)) / len(pratiche_facili)
        for p in pratiche_facili: ha_alloc[p] = ha_base
    
    budget_usato = sum(ha_alloc[p] * d.at[p, 'costo'] for p in ha_alloc)
    budget_res = budget_annuo - budget_usato
    
    for nome, row in d.sort_values(by='Score', ascending=False).iterrows():
        if budget_res <= 0: break
        da_agg = min(budget_res / row['costo'], ETTARI_FILIERA - sum(ha_alloc.values()))
        if da_agg > 0:
            ha_alloc[nome] += da_agg
            budget_res -= da_agg * row['costo']
            
    return ha_alloc, d['Imp_Val'], budget_res

# Esecuzione
ha_current, imp_vals, final_budget_res = run_optimization(w_imp, w_cost, w_diff, safety_buffer, prob_minima)
beneficio_annuo = sum(ha_current[p] * imp_vals[p] for p in ha_current)

# --- CALCOLO TRAIETTORIA ---
anni = list(range(2025, anno_target + 1))
traiettoria = [BASELINE_TOT_ANNUA]
stock_acc = 0
for a in anni[1:]:
    stock_acc = (stock_acc * (100-perdita_carb)/100 * (100-churn_rate)/100) + beneficio_annuo
    traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)

# --- KPI BOXES ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ettari Programma", f"{int(sum(ha_current.values()))} ha")
c2.metric(f"CO2 Rimossa {anno_target}", f"{int(stock_acc)} t")

with c3:
    valore_roi = (budget_annuo - final_budget_res) / beneficio_annuo if beneficio_annuo > 0 else 0
    st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; border: 1px solid #ddd; height: 135px;">
            <p style="margin:0; font-size:18px; font-weight:bold; color:#1E1E1E;">ROI CLIMATICO</p>
            <p style="margin:0; font-size:32px; font-weight:bold; color:#1a73e8;">{valore_roi:.2f} €</p>
            <p style="margin:0; font-size:12px; color:#555;">euro investiti / tCO2 rimossa</p>
        </div>
    """, unsafe_allow_html=True)

with c4:
    color_budget = "#2E7D32" if final_budget_res >= 0 else "#D32F2F"
    label_budget = "BUDGET RESIDUO" if final_budget_res >= 0 else "BUDGET MANCANTE"
    st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; border: 2px solid {color_budget}; height: 135px;">
            <p style="margin:0; font-size:18px; font-weight:bold; color:#1E1E1E;">{label_budget}</p>
            <p style="margin:0; font-size:32px; font-weight:bold; color:{color_budget};">€ {int(final_budget_res):,}</p>
            <p style="margin:0; font-size:12px; color:#555;">rispetto al limite annuo</p>
        </div>
    """, unsafe_allow_html=True)

with c5:
    soglia_limite = BASELINE_TOT_ANNUA * (1 - target_decarb/100)
    gap_val = traiettoria[-1] - soglia_limite
    color_gap = "#2E7D32" if gap_val <= 0 else "#D32F2F"
    st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; border: 2px solid {color_gap}; height: 135px;">
            <p style="margin:0; font-size:18px; font-weight:bold; color:#1E1E1E;">GAP AL TARGET</p>
            <p style="margin:0; font-size:32px; font-weight:bold; color:{color_gap};">{int(gap_val)} t</p>
            <p style="margin:0; font-size:12px; font-weight:bold; color:{color_gap};">{"SOTTO TARGET 🌱" if gap_val <= 0 else "SOPRA TARGET ⚠️"}</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- GRAFICI ---
l, r = st.columns([1.6, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni Net Scope 3")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni, y=traiettoria, mode='lines+markers', line=dict(color='green', width=4), name="Net Scope 3"))
    fig.add_trace(go.Scatter(x=anni, y=[soglia_limite]*len(anni), line=dict(dash='dot', color='red'), name="Target"))
    st.plotly_chart(fig, use_container_width=True)
with r:
    st.subheader("📊 Mix Pratiche")
    st.plotly_chart(go.Figure(data=[go.Pie(labels=list(ha_current.keys()), values=list(ha_current.values()), hole=.4)]), use_container_width=True)

# --- TABELLA PIANO OPERATIVO ---
st.write("### 🚜 Piano Operativo Suggerito")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ha_current.items() if ha > 0}, orient='index', columns=['Ettari']))

st.markdown("---")

# --- ROBUSTEZZA IN FONDO ---
st.subheader("🧪 Robustness Check")
with st.expander("Analisi di Sensibilità (±20% sui pesi delle priorità strategiche)"):
    h1, _, _ = run_optimization(w_imp*1.2, w_cost, w_diff, safety_buffer, prob_minima)
    h2, _, _ = run_optimization(w_imp, w_cost*1.2, w_diff, safety_buffer, prob_minima)
    h3, _, _ = run_optimization(w_imp, w_cost, w_diff*1.2, safety_buffer, prob_minima)
    sens_df = pd.DataFrame({"Attuale": ha_current, "Focus CO2+": h1, "Focus Risparmio+": h2, "Focus Facilità+": h3}).T
    st.bar_chart(sens_df)
    st.caption("Verifica se la strategia è 'No-Regret': le proporzioni dovrebbero rimanere stabili al variare dei pesi.")
