import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# --- DATABASE PRATICHE ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.20, 'd_carb': 1.10, 'costo': 300, 'diff': 3, 'res': 3},
    'Interramento':         {'d_emiss': 0.50, 'd_carb': 2.20, 'costo': 200, 'diff': 1, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.50, 'd_carb': 0.36, 'costo': 250, 'diff': 1, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.50, 'd_carb': 3.30, 'costo': 500, 'diff': 4, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 1.46, 'costo': 550, 'diff': 5, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 2.90, 'costo': 450, 'diff': 5, 'res': 4},
    'Tripletta':            {'d_emiss': 0.20, 'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T

# --- SIDEBAR ---
st.sidebar.header("🕹️ Pannello di Controllo")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000, step=50000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 10, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5)

# --- MOTORE DI OTTIMIZZAZIONE AI ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_NETTA_2025 = ETTARI_FILIERA * 4.5 
target_ton_tot = BASELINE_NETTA_2025 * (target_decarb / 100)

# 1. Calcolo Impatto Netto e Costo/Ton Reale
df_p['Imp_Netto'] = (df_p['d_carb'] - df_p['d_emiss']) * (1 - safety_buffer/100) * (1 - churn_rate/100)
# Il costo per l'azienda dipende dalla % di incentivo scelta dallo slider
df_p['Costo_Azienda_Ha'] = df_p['costo'] * (incentivo_percent / 100)
df_p['Eur_Ton'] = df_p['Costo_Azienda_Ha'] / df_p['Imp_Netto']

# 2. Logica AI: Ranking per Efficienza e Stabilità Rese
df_p['AI_Score'] = (1 / df_p['Eur_Ton']) * (df_p['res'] / 5)
df_p = df_p.sort_values(by='AI_Score', ascending=False)

# 3. Allocazione Ettari vincolata al BUDGET
budget_residuo = budget_max
ettari_allocati = {}
abbattimento_ottenuto = 0

for nome, row in df_p.iterrows():
    if budget_residuo <= 0: break
    
    ha_possibili_budget = budget_residuo / row['Costo_Azienda_Ha']
    # Applichiamo un tetto logico per pratica per simulare la realtà di filiera
    ha_assegnati = min(ha_possibili_budget, 4000, ETTARI_FILIERA - sum(ettari_allocati.values()))
    
    if ha_assegnati > 0:
        ettari_allocati[nome] = ha_assegnati
        budget_residuo -= ha_assegnati * row['Costo_Azienda_Ha']
        abbattimento_ottenuto += ha_assegnati * row['Imp_Netto']

ettari_tot_inc = sum(ettari_allocati.values())
percent_ettari = (ettari_tot_inc / ETTARI_FILIERA) * 100

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
costo_totale_effettivo = budget_max - budget_residuo
eur_ton_medio = costo_totale_effettivo / max(1, abbattimento_ottenuto)
roi_climatico = abbattimento_ottenuto / (max(1, costo_totale_effettivo) / 1000)

c1.metric("EF Target (kg/t)", f"{(BASELINE_NETTA_2025 - abbattimento_ottenuto)/VOL_TOT_TON*1000:.1f}", f"Base: {BASELINE_NETTA_2025/VOL_TOT_TON*1000:.1f}")
c2.metric("Ettari da Incentivare", f"{int(ettari_tot_inc)} ha", f"{percent_ettari:.1f}% della Filiera")
c3.metric("Eur/Ton Abbattimento", f"{eur_ton_medio:.2f} €/t")
c4.metric("ROI Climatico", f"{roi_climatico:.2f} ton/k€")

# Mostra Budget residuo in un piccolo alert se presente
if budget_residuo > 0:
    st.info(f"💰 Budget Residuo: €{int(budget_residuo):,} (Risorse non utilizzate)")

st.markdown("---")

# --- GRAFICI ---
col_traj, col_water = st.columns([1.5, 1])

with col_traj:
    st.subheader("📅 Emissions Trajectory (Budget-Constrained)")
    anni = np.arange(2025, orizzonte_anno + 1)
    lorde = [BASELINE_NETTA_2025] * len(anni)
    assorbimenti = [-(abbattimento_ottenuto * (i/max(1, (len(anni)-1)))) for i in range(len(anni))]
    nette = [l + a for l, a in zip(lorde, assorbimenti)]

    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=lorde, name='Emissioni Lorde', line=dict(color='red', width=2)))
    fig_traj.add_trace(go.Scatter(x=anni, y=assorbimenti, name='Assorbimenti (C-Removal)', fill='tozeroy', line_color='green'))
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_hline(y=BASELINE_NETTA_2025*(1-target_decarb/100), line_dash="dash", line_color="blue", annotation_text="TARGET")
    st.plotly_chart(fig_traj, use_container_width=True)

with col_water:
    st.subheader("📉 Abatement Breakdown")
    fig_wf = go.Figure(go.Waterfall(
        measure = ["absolute", "relative", "total"],
        x = ["Baseline 2025", "Assorbimenti", f"Netto {orizzonte_anno}"],
        y = [BASELINE_NETTA_2025, -abbattimento_ottenuto, 0],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

# --- OTTIMIZZATORE ---
st.markdown("---")
st.subheader("🚀 AI Strategy Optimizer: Mix di Pratiche")

if ettari_allocati:
    col_mix_text, col_mix_chart = st.columns([1, 1])
    with col_mix_text:
        st.write("L'AI ha ottimizzato il portfolio basandosi sui costi e sulla **Stabilità Rese**.")
        st.write("**Dettaglio Ettari:**")
        for p, h in ettari_allocati.items():
            st.write(f"* {p}: {int(h)} ha")
    with col_mix_chart:
        fig_donut = go.Figure(data=[go.Pie(labels=list(ettari_allocati.keys()), values=list(ettari_allocati.values()), hole=.5)])
        st.plotly_chart(fig_donut, use_container_width=True)
else:
    st.warning("Budget insufficiente per incentivare le pratiche selezionate.")
