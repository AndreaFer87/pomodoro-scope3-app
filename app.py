import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Executive Dashboard", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Executive Strategy: Ottimizzazione Budget e Target Emissioni")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.0, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.0, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.0, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Totale (€)", value=1000000, step=50000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Temporale", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.header("🛡️ Rischio e Churn")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Churn Rate Annuo (%)", 0, 20, 10)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 25, 10)

# --- DATABASE FISSO AGGIORNATO ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 250, 'diff': 3, 'res': 2},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 200, 'diff': 1, 'res': 3},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3, 'res': 5},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.9, 'costo': 500, 'diff': 4, 'res': 2},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.6, 'costo': 450, 'diff': 3, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 5}
}

df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
VOL_TOT_TON = 800000
BASELINE_TOT = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- STANDARDIZZAZIONE ---
def safe_norm(series, invert=False):
    if series.max() == series.min(): return series * 0.0 + 1.0
    if invert:
        return (series.max() - series) / (series.max() - series.min())
    return (series - series.min()) / (series.max() - series.min())

# Impatto Netto depurato dal rischio
df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))

# Standardizzazione componenti
df_p['S_Imp'] = safe_norm(df_p['Imp_Val'])
df_p['S_Cost'] = safe_norm(df_p['costo'], invert=True)
df_p['S_Diff'] = safe_norm(df_p['diff'], invert=True)

# Calcolo Score Finale (MCDA)
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
costo_base = sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())
budget_residuo = budget_max - costo_base

for nome, row in df_p.sort_values(by='Score', ascending=False).iterrows():
    abb_attuale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    if abb_attuale >= target_ton or budget_residuo <= 0:
        break
    
    ha_mancanti = (target_ton - abb_attuale) / row['Imp_Val']
    ha_finanziabili = max(0.0, budget_residuo / row['costo'])
    ha_fisici_liberi = max(0.0, ETTARI_FILIERA - sum(ettari_allocati.values()))
    
    da_aggiungere = min(ha_mancanti, ha_finanziabili, ha_fisici_liberi)
    ettari_allocati[nome] += da_aggiungere
    budget_residuo -= da_aggiungere * row['costo']

# --- CALCOLO KPI ---
abb_finale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
costo_totale = budget_max - budget_residuo
eur_ton_medio = costo_totale / abb_finale if abb_finale > 0 else 0
gap_residuo = max(0.0, target_ton - abb_finale)

# --- BOX KPI ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Superficie Totale", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("CO2 Abbattuta", f"{int(abb_finale)} t")
c3.metric("€/t Medio Pesato", f"{eur_ton_medio:.2f} €")
c4.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
c5.metric("Gap Target (tCO2)", f"{int(gap_residuo)} t", delta_color="inverse")

st.markdown("---")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📅 Proiezione Temporale (Carry-over & Churn)")
    anni = np.arange(2025, orizzonte_anno + 1)
    traiettoria = []
    for i in range(len(anni)):
        progressione = (i + 1) / len(anni)
        efficacia = (abb_finale * progressione) * (1 - (churn_rate/100))**i
        traiettoria.append(BASELINE_TOT - efficacia)
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria, name="Emissione Netta", line=dict(color='black', width=4)))
    fig_line.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT - target_ton]*len(anni), name="Obiettivo", line=dict(dash='dot', color='red')))
    st.plotly_chart(fig_line, use_container_width=True)

with col_r:
    st.subheader("📊 Portfolio Mix Ettari")
    labels = [p for p, ha in ettari_allocati.items() if ha > 0.1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0.1]
    if values:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)
    else:
        st.error("Budget insufficiente!")

# --- WATERFALL ALLINEATO ---
st.subheader("📉 Analisi Variazione Emissioni (Waterfall)")
var_input = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
var_soc = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    name = "Decarbonizzazione", orientation = "v",
    x = ["Baseline 2025", "Variazione Input", "Rimozione SOC", "Emissione Netta Finale"],
    textposition = "outside",
    y = [BASELINE_TOT, var_input, -var_soc, 0],
    measure = ["absolute", "relative", "relative", "total"],
    connector = {"line":{"color":"rgb(63, 63, 63)"}},
))
fig_wf.update_layout(showlegend=False)
st.plotly_chart(fig_wf, use_container_width=True)

st.write("### 🚜 Piano Operativo Suggerito")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ettari_allocati.items() if ha > 0}, orient='index', columns=['Superficie Adottata']))
