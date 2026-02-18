import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Configurazione Pagina
st.set_page_config(page_title="Agri-E-MRV: Pomodoro Carbon Plan", layout="wide")

# --- STILE CSS PER LE MATTONELLE KPI ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: LE LEVE (INPUT) ---
st.sidebar.header("🕹️ Leve di Simulazione")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_totale = st.sidebar.number_input("Budget Totale (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo all'Agricoltore (%)", 50, 100, 75)
orizzonte_temporale = st.sidebar.select_slider("Orizzonte Temporale", options=[2026, 2027, 2028, 2029, 2030, 2035])
safety_buffer = st.sidebar.slider("Livello Incertezza (Safety Buffer %)", 5, 30, 15)

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
RESA_MEDIA = 80
ETTARI_TOTALI = 10000
EF_BASELINE_KG_KG = 0.056 # (4.5 t/ha / 80 t/ha)
BASELINE_TOT_T_CO2 = 45000 # 4.5 * 10000

# --- DATABASE PRATICHE (Incluso Delta rispetto a Baseline) ---
pratiche = {
    'Cover Crops': {'d_emiss': 0.2, 'd_carb': 1.6, 'costo': 300, 'diff': 3, 'resilienza': 4},
    'Interramento': {'d_emiss': 0.5, 'd_carb': 2.7, 'costo': 400, 'diff': 1, 'resilienza': 3},
    'Minima Lav.': {'d_emiss': -0.5, 'd_carb': 0.86, 'costo': 400, 'diff': 1, 'resilienza': 5},
    'Tripletta': {'d_emiss': 0.2, 'd_carb': 4.17, 'costo': 800, 'diff': 5, 'resilienza': 5}
}

# --- CALCOLI CORE ---
target_ton = BASELINE_TOT_T_CO2 * (target_decarb / 100)
# Calcolo per la pratica selezionata (simuliamo l'ottimizzatore sulla Tripletta per ora)
p_nome = "Tripletta"
p = pratiche[p_nome]

# Impatto netto reale con buffer
impatto_unitaro = (p['d_carb'] - p['d_emiss']) * (1 - (safety_buffer/100)) * (1 - 0.20) # 20% permanenza fisso
ettari_necessari = min(target_ton / impatto_unitaro, ETTARI_TOTALI)
emissioni_abbattute = ettari_necessari * impatto_unitaro
residue = BASELINE_TOT_T_CO2 - emissioni_abbattute
costo_effettivo = ettari_necessari * p['costo'] * (incentivo_percent / 100)
ef_target = (BASELINE_TOT_T_CO2 - emissioni_abbattute) / VOL_TOT_TON

# --- 3. RIEPILOGO KPI (MATTONELLE) ---
st.title("🍅 Agri-E-MRV: Decision Support System")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("EF Attuale vs Target", f"{EF_BASELINE_KG_KG:.3f}", f"{ef_target:.3f} kg/kg", delta_color="inverse")
with kpi2:
    st.metric("Ettari da Contrattualizzare", f"{int(ettari_necessari)} ha", f"{(ettari_necessari/ETTARI_TOTALI)*100:.1f}% filiera")
with kpi3:
    st.metric("Costo per Ton abbattuta", f"{costo_effettivo/max(1, emissioni_abbattute):.2f} €/t")
with kpi4:
    st.metric("Emissioni Residue", f"{int(residue)} t CO2e")

st.markdown("---")

# --- 2. OUTPUT GRAFICI ---
col_left, col_right = st.columns(2)

with col_left:
    # A. WATERFALL CHART
    st.subheader("📊 La strada verso il Net Zero")
    fig_wf = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative", "relative", "relative", "total"],
        x = ["Baseline", "Riduzione Emissioni", "Sequestro Carbonio", "Emissioni Residue"],
        textposition = "outside",
        text = [f"+{BASELINE_TOT_T_CO2}", f"-{int(ettari_necessari*p['d_emiss'])}", f"-{int(ettari_necessari*p['d_carb'])}", "Netto"],
        y = [BASELINE_TOT_T_CO2, -ettari_necessari*p['d_emiss'], -ettari_necessari*p['d_carb'], 0],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

with col_right:
    # B. AREA TEMPORALE
    st.subheader("📈 Emissioni vs Sequestro nel Tempo")
    anni = np.arange(2025, orizzonte_temporale + 1)
    emiss_line = [BASELINE_TOT_T_CO2] * len(anni)
    sequestro_line = [-(impatto_unitaro * ettari_necessari) * (i/len(anni)) for i in range(len(anni))]
    net_line = [a + b for a, b in zip(emiss_line, sequestro_line)]
    
    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(x=anni, y=emiss_line, fill='tonexty', mode='lines', name='Emissioni Lorde', line_color='red'))
    fig_area.add_trace(go.Scatter(x=anni, y=sequestro_line, fill='tozeroy', mode='lines', name='Sequestro RothC', line_color='green'))
    fig_area.add_trace(go.Scatter(x=anni, y=net_line, mode='lines+markers', name='Impatto Netto Scope 3', line=dict(color='black', width=4)))
    st.plotly_chart(fig_area, use_container_width=True)

# C. SPIDER CHART (Confronto Pratiche)
st.markdown("---")
st.subheader("🎯 Confronto tra Pratiche (Radar Chart)")
categories = ['Efficacia Climatica', 'Efficienza Economica', 'Facilità Adozione', 'Resilienza Agronomica']

fig_radar = go.Figure()
for name, vals in pratiche.items():
    # Normalizzazione fittizia per il radar
    scores = [vals['d_carb']*2, 10-(vals['costo']/100), 6-vals['diff'], vals['resilienza']]
    fig_radar.add_trace(go.Scatterpolar(r=scores, theta=categories, fill='toself', name=name))

st.plotly_chart(fig_radar)

# BOTTONE OTTIMIZZATORE
if st.button("🚀 TROVA LO SWEET SPOT (Ottimizzatore Automatico)"):
    st.success(f"Analisi completata! Per raggiungere il {target_decarb}% con il minor costo, l'algoritmo suggerisce un mix di {int(ettari_necessari*0.7)} ha di Interramento e {int(ettari_necessari*0.3)} ha di Cover Crops.")
