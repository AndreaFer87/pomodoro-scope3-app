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
budget_max_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 10, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5)

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EMISSIONI_BASE_HA = 4.0   
LOSS_SOC_BASE_HA = 0.5    
BASELINE_TOT = ETTARI_FILIERA * (EMISSIONI_BASE_HA + LOSS_SOC_BASE_HA)
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000
n_anni = orizzonte_anno - 2025

# --- DATABASE PRATICHE (Aggiornato con i tuoi valori) ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300, 'res': 3},
    'Interramento':         {'d_emiss': 0.5,  'd_carb': 2.2,  'costo': 200, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.5, 'd_carb': 0.36, 'costo': 250, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3,  'costo': 500, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 550, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9,  'costo': 450, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T

# --- MODELLO DI CALCOLO ---
# 1. Impatto Netto per ettaro (depurato dai rischi)
df_p['Impatto_Ha'] = (df_p['d_carb'] - df_p['d_emiss'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100) * (1 - churn_rate/100)
# 2. Costo per l'azienda
df_p['Costo_Azienda_Ha'] = df_p['costo'] * (incentivo_percent / 100)
# 3. Efficienza
df_p['Eur_Ton'] = df_p['Costo_Azienda_Ha'] / df_p['Impatto_Ha']

# 4. Allocazione (Simulazione Mix Ottimale)
# Ordiniamo per efficienza e stabilità rese
df_p = df_p.sort_values(by=['Eur_Ton']) 

target_ton_anno = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {}
abbattimento_effettivo = 0

for nome, row in df_p.iterrows():
    if budget_residuo <= 0: break
    # Calcolo quanti ettari servirebbero di questa pratica per fare il target
    ha_necessari = (target_ton_anno - abbattimento_effettivo) / row['Impatto_Ha']
    # Vincolo budget e vincolo superficie totale
    ha_finanziabili = budget_residuo / row['Costo_Azienda_Ha']
    ha_finali = max(0, min(ha_necessari, ha_finanziabili, ETTARI_FILIERA - sum(ettari_allocati.values())))
    
    if ha_finali > 0.1:
        ettari_allocati[nome] = ha_finali
        budget_residuo -= ha_finali * row['Costo_Azienda_Ha']
        abbattimento_effettivo += ha_finali * row['Impatto_Ha']

ettari_tot = sum(ettari_allocati.values())
investimento_totale = (budget_max_annuo - budget_residuo) * n_anni

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_effettivo)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Ettari da Incentivare", f"{int(ettari_tot)} ha", f"{(ettari_tot/ETTARI_FILIERA)*100:.1f}% Filiera")
c3.metric("Eur/Ton Abbattimento", f"{(budget_max_annuo - budget_residuo)/max(1, abbattimento_effettivo):.2f} €/t")
c4.metric("Investimento Totale", f"€ {int(investimento_totale):,}", f"{n_anni} anni")

st.markdown("---")

# --- GRAFICI (STRUTTURA FISSA) ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory")
    anni = np.arange(2025, orizzonte_anno + 1)
    # Proiezione lineare dell'abbattimento
    nette = [BASELINE_TOT - (abbattimento_effettivo * (i/(len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_TOT * (1 - target_decarb/100)] * len(anni)
    
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni, y=target_line, name='Target CSRD', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader("📉 Abatement Breakdown")
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Assorbimenti Totali", "Emissioni Nette"],
        y = [BASELINE_TOT, -abbattimento_effettivo, 0],
        measure = ["absolute", "relative", "total"],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

# --- DETTAGLIO MIX ---
st.markdown("---")
st.subheader("🚀 Mix di Pratiche Allocato")
if ettari_allocati:
    cm1, cm2 = st.columns([1, 2])
    with cm1:
        for p, h in ettari_allocati.items():
            st.write(f"**{p}**: {int(h)} ha")
        if budget_residuo > 10:
            st.success(f"Budget residuo: €{int(budget_residuo)}")
        else:
            st.error("Budget Esaurito!")
    with cm2:
        fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_allocati.keys()), values=list(ettari_allocati.values()), hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)
