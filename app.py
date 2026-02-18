import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Dashboard Finale", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Sistema di Governance: Ottimizzazione Standardizzata e Traiettoria Temporale")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Decisionali (MCDA)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.0, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.0, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.0, 1.0, 0.2)

st.sidebar.header("🎯 Target & Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Temporale", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.header("🛡️ Rischio & Permanenza")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Churn Rate Annuo (%)", 0, 20, 10)
prob_minima = st.sidebar.slider("Quota Probabilistica Minima (%)", 0, 25, 10, 
                                 help="Ettari minimi garantiti alle pratiche con Difficoltà < 3")

# --- DATABASE FISSO ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'costo': 250, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.0, 'costo': 200, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 4},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9, 'costo': 450, 'diff': 3},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5}
}

df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
VOL_TOT_TON = 800000
BASELINE_TOT = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- FUNZIONE STANDARDIZZAZIONE ---
def safe_norm(series, invert=False):
    if series.max() == series.min(): return series * 0.0 + 1.0
    if invert:
        return (series.max() - series) / (series.max() - series.min())
    return (series - series.min()) / (series.max() - series.min())

# --- CALCOLI INDICATORI ---
df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
df_p['S_Imp'] = safe_norm(df_p['Imp_Val'])
df_p['S_Cost'] = safe_norm(df_p['costo'], invert=True)
df_p['S_Diff'] = safe_norm(df_p['diff'], invert=True)

# Calcolo Score Finale (MCDA Standardizzato)
df_p['Score'] = (df_p['S_Imp'] * w_imp) + (df_p['S_Cost'] * w_cost) + (df_p['S_Diff'] * w_diff)

# --- ALLOCAZIONE IBRIDA ---
ettari_allocati = {p: 0.0 for p in df_p.index}

# 1. Quota Probabilistica (Diff < 3)
pratiche_facili = df_p[df_p['diff'] < 3].index
if not pratiche_facili.empty:
    ha_base = (ETTARI_FILIERA * (prob_minima/100)) / len(pratiche_facili)
    for p in pratiche_facili:
        ettari_allocati[p] = ha_base

# 2. Allocazione ROI-Driven sul Budget Residuo
target_ton = BASELINE_TOT * (target_decarb/100)
budget_residuo = budget_max - sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())
df_sorted = df_p.sort_values(by='Score', ascending=False)

for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    if abb_attuale >= target_ton or budget_residuo <= 0: break
    
    ha_mancanti = (target_ton - abb_attuale) / row['Imp_Val']
    ha_finanziabili = max(0.0, budget_residuo / row['costo'])
    ha_fisici_liberi = max(0.0, ETTARI_FILIERA - sum(ettari_allocati.values()))
    
    da_aggiungere = min(ha_mancanti, ha_finanziabili, ha_fisici_liberi)
    ettari_allocati[nome] += da_aggiungere
    budget_residuo -= da_aggiungere * row['costo']

# --- LOGICA CARRY-OVER & CHURN ---
anni = np.arange(2025, orizzonte_anno + 1)
abb_a_regime = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
traiettoria = []
for i in range(len(anni)):
    progressione = (i + 1) / len(anni)
    # Carry-over influenzato dal Churn Rate cumulativo
    efficacia = (abb_a_regime * progressione) * (1 - (churn_rate/100))**i
    traiettoria.append(BASELINE_TOT - efficacia)

# --- VISUALIZZAZIONE KPI ---
c1, c2, c3, c4 = st.columns(4)
abb_finale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
c1.metric("Superficie Totale", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("CO2 Abbattuta (Regime)", f"{int(abb_finale)} t")
c3.metric("Budget Speso", f"€ {int(budget_max - budget_residuo):,}")
c4.metric("EF Finale Target", f"{((BASELINE_TOT - abb_finale)/VOL_TOT_TON)*1000:.2f} kg/t")

st.markdown("---")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📅 Traiettoria Temporale (Carry-over & Churn)")
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria, name="Emissione Netta Proiettata", 
                                 line=dict(color='black', width=4), mode='lines+markers'))
    fig_line.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT - target_ton]*len(anni), 
                                 name="Target Decarb.", line=dict(dash='dot', color='red')))
    fig_line.update_layout(yaxis_title="t CO2e", margin=dict(l=0,r=0,b=0,t=30))
    st.plotly_chart(fig_line, use_container_width=True)

with col_r:
    st.subheader("📊 Mix Portafoglio Ottimizzato")
    labels = [p for p, ha in ettari_allocati.items() if ha > 1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 1]
    if values:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)
    else:
        st.error("Budget insufficiente per attivare le pratiche.")

# --- ANALISI DETTAGLIATA ---
st.markdown("---")
st.subheader("📉 Analisi Variazione Emissioni (Waterfall)")
mix_d_emiss = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
mix_d_carb = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    x = ["Baseline 2025", "Variazione Input", "Rimozione SOC", "Risultato Netto"],
    y = [BASELINE_TOT, mix_d_emiss, -mix_d_carb, 0],
    measure = ["absolute", "relative", "relative", "total"]
))
st.plotly_chart(fig_wf, use_container_width=True)

st.write("### 📋 Tabella di Ranking e Parametri Standardizzati")
st.dataframe(df_p[['Imp_Val', 'S_Imp', 'S_Cost', 'S_Diff', 'Score']].sort_values(by='Score', ascending=False))
