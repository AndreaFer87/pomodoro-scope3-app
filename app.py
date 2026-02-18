import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# --- DATABASE PRATICHE (Aggiornato con i tuoi ultimi valori) ---
# res: Stabilità Rese (1-5), diff: Difficoltà (1-5)
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300, 'res': 4, 'diff': 2},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2,  'costo': 200, 'res': 5, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'res': 4, 'diff': 1},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3,  'costo': 500, 'res': 4, 'diff': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.5, 'd_carb': 1.46, 'costo': 300, 'res': 5, 'diff': 3},
    'Int. + Minima Lav.':   {'d_emiss': -0.4, 'd_carb': 2.9,  'costo': 450, 'res': 4, 'diff': 3},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'res': 3, 'diff': 5}
}
df_p = pd.DataFrame(pratiche).T

# --- SIDEBAR ---
st.sidebar.header("🕹️ Controllo Strategico")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo (€)", value=500000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 10, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte", options=[2026, 2027, 2028, 2029, 2030])

st.sidebar.subheader("🛡️ Gestione Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate = st.sidebar.slider("Tasso Abbandono (%)", 0, 20, 5)

# --- MOTORE AI ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT = ETTARI_FILIERA * 4.5 

# 1. Impatto Reale Scontato
df_p['Imp_Netto'] = (-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100) * (1 - churn_rate/100)
df_p['Costo_Azienda'] = df_p['costo'] * (incentivo_percent / 100)

# 2. Score di Merito IA (Efficienza * Stabilità / Difficoltà)
df_p['AI_Score'] = (df_p['Imp_Netto'] / (df_p['Costo_Azienda'] * df_p['diff'])) * df_p['res']
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

# 3. Allocazione Ettari
target_ton_anno = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {}
abbattimento_ottenuto = 0

for nome, row in df_sorted.iterrows():
    if budget_residuo <= 0: break
    ha_necessari = (target_ton_anno - abbattimento_ottenuto) / row['Imp_Netto']
    ha_finanziabili = budget_residuo / row['Costo_Azienda']
    ha_finali = max(0, min(ha_necessari, ha_finanziabili, ETTARI_FILIERA - sum(ettari_allocati.values())))
    
    if ha_finali > 0.1:
        ettari_allocati[nome] = ha_finali
        budget_residuo -= ha_finali * row['Costo_Azienda']
        abbattimento_ottenuto += ha_finali * row['Imp_Netto']

# --- KPI ---
n_anni = orizzonte_anno - 2025
inv_tot = (budget_max_annuo - budget_residuo) * n_anni

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_ottenuto)/VOL_TOT_TON)*1000:.1f} kg/t")
c2.metric("Ettari Incentivati", f"{int(sum(ettari_allocati.values()))} ha", f"{int(sum(ettari_allocati.values())/ETTARI_FILIERA*100)}% Filiera")
c3.metric("Costo Abbattimento", f"{(budget_max_annuo-budget_residuo)/max(1, abbattimento_ottenuto):.2f} €/t")
c4.metric("Investimento Totale", f"€ {int(inv_tot):,}")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])
with col_l:
    st.subheader("📅 Proiezione Traiettoria")
    anni = np.arange(2025, orizzonte_anno + 1)
    nette = [BASELINE_TOT - (abbattimento_ottenuto * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni, y=nette, name='Nette', line=dict(color='black', width=4)))
    fig.add_hline(y=BASELINE_TOT*(1-target_decarb/100), line_dash="dash", line_color="blue")
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("🥧 Mix Ottimizzato IA")
    if ettari_allocati:
        fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_allocati.keys()), values=list(ettari_allocati.values()), hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)

st.write("### 🔬 Dettaglio Strategia AI")
st.table(df_sorted[['Imp_Netto', 'Costo_Azienda', 'AI_Score']])
