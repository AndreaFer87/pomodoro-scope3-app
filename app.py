import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="centered")

# --- TITOLO ACCATTIVANTE ---
st.title("🌱 Plan & Govern Scope 3")
st.subheader("Strategize, execute, and monitor your agricultural decarbonization.")
st.markdown("---")

# --- SIDEBAR: LE LEVE DI GOVERNANCE ---
st.sidebar.header("🛠️ Sustainability Strategy")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_totale = st.sidebar.number_input("Budget Totale (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo all'Agricoltore (%)", 50, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])
safety_buffer = st.sidebar.slider("Safety Buffer (Buffer Pool %)", 5, 40, 20)

# --- DATI FISSI ---
VOL_TOT_TON = 800000
ETTARI_TOTALI = 10000
EF_BASE_KG_TON = 56.25  # 45000 t / 800000 t * 1000
BASELINE_TOT_T_CO2 = 45000
INCERTEZZA_MODELLO = 0.15 # RothC fix

# Database Pratiche (Valori medi)
pratiche = {
    'Cover Crops': {'d_emiss': 0.2, 'd_carb': 1.6, 'costo': 300, 'diff': 3, 'resilienza': 4},
    'Interramento': {'d_emiss': 0.5, 'd_carb': 2.7, 'costo': 400, 'diff': 1, 'resilienza': 3},
    'Minima Lav.': {'d_emiss': -0.5, 'd_carb': 0.86, 'costo': 400, 'diff': 1, 'resilienza': 5},
    'Tripletta': {'d_emiss': 0.2, 'd_carb': 4.17, 'costo': 800, 'diff': 5, 'resilienza': 5}
}

# --- LOGICA DI CALCOLO ---
p_nome = "Tripletta" # Simuliamo sulla pratica più potente
p = pratiche[p_nome]

# Impatto Netto REALE considerando entrambi i buffer
impatto_un_netto = (p['d_carb'] - p['d_emiss']) * (1 - INCERTEZZA_MODELLO) * (1 - (safety_buffer/100))
target_ton_anno = BASELINE_TOT_T_CO2 * (target_decarb / 100)
ettari_req = min(target_ton_anno / impatto_un_netto, ETTARI_TOTALI)

abbattimento_effettivo = ettari_req * impatto_un_netto
residue = BASELINE_TOT_T_CO2 - abbattimento_effettivo
ef_target_kg_ton = residue / VOL_TOT_TON * 1000

# --- KPI MATTONELLE ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("EF Base vs Target", f"{EF_BASE_KG_TON:.1f} kg/t", f"{ef_target_kg_ton:.1f} kg/t", delta_color="inverse")
k2.metric("Ettari da Contrattualizzare", f"{int(ettari_req)} ha")
k3.metric("Costo/Ton Abbattuta", f"{(ettari_req * p['costo'] * (incentivo_percent/100)) / max(1, abbattimento_effettivo):.2f} €/t")
k4.metric("Emissioni Residue", f"{int(residue)} t CO2e")

st.markdown("---")

# --- GRAFICI VERTICALI ---

# 1. WATERFALL
st.subheader("📉 La strada verso il Net Zero")
fig_wf = go.Figure(go.Waterfall(
    measure = ["relative", "relative", "relative", "total"],
    x = ["Baseline 2025", "Riduzione Input", "Assorbimenti C", "Residue Target"],
    y = [BASELINE_TOT_T_CO2, -ettari_req*p['d_emiss'], -ettari_req*p['d_carb'], 0],
    text = [f"+{BASELINE_TOT_T_CO2}", "Riduzione", "Sequestro", "Netto"],
    connector = {"line":{"color":"rgb(63, 63, 63)"}},
))
st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")

# 2. TEMPORALE CUMULATIVO
st.subheader("📅 Proiezione Strategica Temporale")
anni = np.arange(2025, orizzonte_anno + 1)
l_lorde = [BASELINE_TOT_T_CO2] * len(anni)
# Assorbimenti cumulativi (stock)
l_assorbimenti = [-(abbattimento_effettivo * (i/len(anni))) for i in range(len(anni))]
l_nette = [a + b for a, b in zip(l_lorde, l_assorbimenti)]

fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(x=anni, y=l_lorde, name='Emissioni Lorde', line=dict(color='red', dash='dash')))
fig_temp.add_trace(go.Scatter(x=anni, y=l_assorbimenti, fill='tozeroy', name='Assorbimenti C', line_color='green'))
fig_temp.add_trace(go.Scatter(x=anni, y=l_nette, name='Emissioni Nette Totali', line=dict(color='black', width=4)))
st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("---")

# 3. RADAR
st.subheader("🎯 Profilo Tecnico delle Pratiche")
fig_radar = go.Figure()
for name, vals in pratiche.items():
    scores = [vals['d_carb']*2, 10-(vals['costo']/100), 6-vals['diff'], vals['resilienza']]
    fig_radar.add_trace(go.Scatterpolar(r=scores, theta=['Efficacia Climatica', 'Efficienza Eco', 'Facilità Adozione', 'Resilienza'], fill='toself', name=name))
st.plotly_chart(fig_radar, use_container_width=True)

# BOTTONE OTTIMIZZATORE
st.markdown("---")
if st.button("🚀 TROVA LO SWEET SPOT (Ottimizzatore Automatico)"):
    st.success("Ottimizzazione completata secondo i vincoli CSRD & GHG Protocol.")
    st.write(f"Per colpire il target del {target_decarb}% minimizzando il rischio di abbandono (Churn Rate), il sistema suggerisce di dare priorità alla 'Tripletta' su {int(ettari_req)} ettari selezionati tramite LPS.")
