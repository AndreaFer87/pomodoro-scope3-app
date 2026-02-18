import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia di Decarbonizzazione Dinamica per la Filiera Pomodoro")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("🕹️ Pannello di Controllo")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=500000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 10, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5)

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EMISSIONI_BASE_HA = 4.0   
LOSS_SOC_BASE_HA = 0.5    
BASELINE_TOT = ETTARI_FILIERA * (EMISSIONI_BASE_HA + LOSS_SOC_BASE_HA)
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000
n_anni = orizzonte_anno - 2025

# --- DATABASE PRATICHE (Ultimi dati input forniti) ---
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

# --- MODELLO DI OTTIMIZZAZIONE AI ---
# 1. Calcolo Impatto Reale depurato dai rischi
df_p['Impatto_Ha'] = (-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100) * (1 - churn_rate/100)
df_p['Costo_Azienda_Ha'] = df_p['costo'] * (incentivo_percent / 100)

# 2. Algoritmo di Ranking (Score di Merito AI)
# Lo score premia l'efficienza (Imp/Costo) e la stabilità (res), penalizzando la difficoltà (diff)
df_p['AI_Score'] = (df_p['Impatto_Ha'] / (df_p['Costo_Azienda_Ha'] * df_p['diff'])) * df_p['res']
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

# 3. Allocazione Ettari
target_ton_anno = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {}
abbattimento_ottenuto = 0

for nome, row in df_sorted.iterrows():
    if budget_residuo <= 0: break
    ha_necessari = (target_ton_anno - abbattimento_ottenuto) / row['Impatto_Ha']
    ha_finanziabili = budget_residuo / row['Costo_Azienda_Ha']
    ha_finali = max(0, min(ha_necessari, ha_finanziabili, ETTARI_FILIERA - sum(ettari_allocati.values())))
    
    if ha_finali > 0.1:
        ettari_allocati[nome] = ha_finali
        budget_residuo -= ha_finali * row['Costo_Azienda_Ha']
        abbattimento_ottenuto += ha_finali * row['Impatto_Ha']

ettari_tot = sum(ettari_allocati.values())

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_ottenuto)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Ettari da Incentivare", f"{int(ettari_tot)} ha", f"{(ettari_tot/ETTARI_FILIERA)*100:.1f}% Filiera")
c3.metric("Eur/Ton Abbattimento", f"{(budget_max_annuo - budget_residuo)/max(1, abbattimento_ottenuto):.2f} €/t")
c4.metric("Investimento Totale", f"€ {int((budget_max_annuo - budget_residuo) * n_anni):,}", f"{n_anni} anni")

st.markdown("---")
# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])
with col_left:
    st.subheader("📅 Emissions Trajectory")
    anni = np.arange(2025, orizzonte_anno + 1)
    nette = [BASELINE_TOT - (abbattimento_ottenuto * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_TOT * (1 - target_decarb/100)] * len(anni)
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni, y=target_line, name='Target CSRD', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader("📉 Abatement Breakdown")
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Assorbimenti Totali", "Emissioni Nette"],
        y = [BASELINE_TOT, -abbattimento_ottenuto, 0],
        measure = ["absolute", "relative", "total"],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.subheader("🚀 Mix di Pratiche Allocato (Ottimizzazione AI)")
if ettari_allocati:
    cm1, cm2 = st.columns([1, 2])
    with cm1:
        for p, h in ettari_allocati.items():
            st.write(f"**{p}**: {int(h)} ha")
        st.write(f"**Budget Residuo**: €{int(budget_residuo)}")
    with cm2:
        fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_allocati.keys()), values=list(ettari_allocati.values()), hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)
