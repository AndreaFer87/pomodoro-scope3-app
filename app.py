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

# --- DATI FISSI FILIERA (Modifica Baseline 50 kg/ton) ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  # Richiesta: Baseline 50 kg/ton
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 # Risultato: 40,000 tCO2e
LOSS_SOC_BASE_HA = 0.5    
n_anni = orizzonte_anno - 2025

# --- DATABASE PRATICHE ---
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

# --- MOTORE DI OTTIMIZZAZIONE AI ---
df_p['Imp_Evitate_Ha'] = -df_p['d_emiss'] 
df_p['Imp_Sequestro_Ha'] = df_p['d_carb'] + LOSS_SOC_BASE_HA
df_p['Impatto_Netto_Ha'] = (df_p['Imp_Evitate_Ha'] + df_p['Imp_Sequestro_Ha']) * (1 - safety_buffer/100) * (1 - churn_rate/100)
df_p['Costo_Azienda_Ha'] = df_p['costo'] * (incentivo_percent / 100)

df_p['AI_Score'] = (df_p['Impatto_Netto_Ha'] / (df_p['Costo_Azienda_Ha'] * df_p['diff'])) * df_p['res']
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

target_ton_anno = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {}
evitate_tot = 0
sequestro_tot = 0

for nome, row in df_sorted.iterrows():
    if budget_residuo <= 0: break
    abbattimento_mancante = target_ton_anno - (evitate_tot + sequestro_tot)
    if abbattimento_mancante <= 0: break
    
    ha_necessari = abbattimento_mancante / row['Impatto_Netto_Ha']
    ha_finanziabili = budget_residuo / row['Costo_Azienda_Ha']
    ha_finali = max(0, min(ha_necessari, ha_finanziabili, ETTARI_FILIERA - sum(ettari_allocati.values())))
    
    if ha_finali > 0.1:
        ettari_allocati[nome] = ha_finali
        budget_residuo -= ha_finali * row['Costo_Azienda_Ha']
        evitate_tot += ha_finali * row['Imp_Evitate_Ha'] * (1 - safety_buffer/100) * (1 - churn_rate/100)
        sequestro_tot += ha_finali * row['Imp_Sequestro_Ha'] * (1 - safety_buffer/100) * (1 - churn_rate/100)

abbattimento_totale = evitate_tot + sequestro_tot
ettari_tot = sum(ettari_allocati.values())

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_totale)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Ettari da Incentivare", f"{int(ettari_tot)} ha", f"{(ettari_tot/ETTARI_FILIERA)*100:.1f}% Filiera")
c3.metric("Eur/Ton Abbattimento", f"{(budget_max_annuo - budget_residuo)/max(1, abbattimento_totale):.2f} €/t")
c4.metric("Investimento Totale", f"€ {int((budget_max_annuo - budget_residuo) * n_anni):,}", f"{n_anni} anni")

# Alert Budget Residuo (Verde se presente)
if budget_residuo > 0:
    st.success(f"💰 **Budget Residuo Ottimizzato**: €{int(budget_residuo):,} (L'obiettivo è stato raggiunto con meno risorse del previsto)")

st.markdown("---")

# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory")
    anni = np.arange(2025, orizzonte_anno + 1)
    nette = [BASELINE_TOT - (abbattimento_totale * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_TOT * (1 - target_decarb/100)] * len(anni)
    
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni, y=target_line, name='Target', line=dict(color='blue', dash='dash'))) # Solo "Target"
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Abatement Breakdown (Target {orizzonte_anno})")
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline", "Emissioni Evitate", "Sequestro SOC", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -evitate_tot, -sequestro_tot, 0],
        measure = ["absolute", "relative", "relative", "total"],
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
    with cm2:
        fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_allocati.keys()), values=list(ettari_allocati.values()), hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)
