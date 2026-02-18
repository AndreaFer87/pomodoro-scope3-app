import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Configurazione stile "Regrow White/Green"
st.set_page_config(page_title="Regrow-style Plan & Govern | Agri-E-MRV", layout="wide")

# Custom CSS per rifinire l'estetica
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stMetric { background-color: #f1f3f4; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    div.stButton > button:first-child { background-color: #2e7d32; color: white; border-radius: 20px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER STILE PLAN AI ---
st.title("🌱 PlanAI: Sustainability Insights")
st.markdown("**Build your business case for regenerative agriculture and scale your Scope 3 programs.**")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.image("https://www.regrow.ag/hubfs/Regrow_Logo_2022_Green.svg", width=150) # Logo simulato
st.sidebar.header("Configuration")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
safety_buffer = st.sidebar.slider("Safety Buffer (Rischio Permanenza %)", 5, 40, 20)
incertezza_modello = st.sidebar.slider("Incertezza Tier 3 (%)", 5, 30, 15)

# --- LOGICA CALCOLO (DATI FISSI) ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_TOT = 45000 
target_ton_tot = BASELINE_TOT * (target_decarb / 100)

pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300},
    'Interramento':         {'d_emiss': 0.5,  'd_carb': 2.2,  'costo': 400},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500}
}

# Calcolo impatto netto reale medio per l'ottimizzatore
def get_net_impact(p):
    return (p['d_carb'] - p['d_emiss']) * (1 - incertezza_modello/100) * (1 - safety_buffer/100)

# --- KPI TOP BAR ---
# Calcoliamo gli ettari necessari usando un mix ipotetico (ottimizzato)
avg_impact = get_net_impact(pratiche['Tripletta'])
ettari_target = min(target_ton_tot / avg_impact, ETTARI_FILIERA)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Regenerative Acres", f"{int(ettari_target)} ha", f"Target: {target_decarb}%")
c2.metric("Incentives Payout", f"€ {int(ettari_target * 500):,}")
c3.metric("Abatement Potential", f"{int(target_ton_tot)} t CO2e")
c4.metric("ROI on Investment", "2.4x", "Scope 3 Efficiency")

st.markdown("---")

# --- GRAFICI PRINCIPALI ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory to 2030")
    anni = np.arange(2025, 2031)
    # Simulazione curva di adozione stile Regrow
    base_line = [BASELINE_TOT] * len(anni)
    reduction = [BASELINE_TOT - (target_ton_tot * (i/5)) for i in range(6)]
    
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=base_line, name='Business as Usual', line=dict(color='grey', dash='dot')))
    fig_traj.add_trace(go.Scatter(x=anni, y=reduction, fill='tonexty', name='Optimized Plan', line_color='#2e7d32'))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader("🎯 Program Allocation")
    # OTTIMIZZAZIONE GRAFICA (Donut Chart)
    labels = ["Tripletta", "C.C. + Minima Lav.", "Interramento"]
    values = [ettari_target * 0.4, ettari_target * 0.3, ettari_target * 0.3]
    colors = ['#1b5e20', '#4caf50', '#81c784']
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker_colors=colors)])
    fig_donut.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
    st.plotly_chart(fig_donut, use_container_width=True)

# --- WATERFALL (Sotto, come dettaglio) ---
st.markdown("---")
st.subheader("📉 Abatement Breakdown (Waterfall)")
fig_wf = go.Figure(go.Waterfall(
    measure = ["absolute", "relative", "relative", "total"],
    x = ["2025 Baseline", "Input Reduction", "Soil Carbon Removal", "2030 Net Emissions"],
    y = [BASELINE_TOT, -target_ton_tot*0.3, -target_ton_tot*0.7, 0],
    connector = {"line":{"color":"#2e7d32"}},
))
st.plotly_chart(fig_wf, use_container_width=True)

if st.button("🚀 Re-Calculate Optimized Path"):
    st.balloons()
    st.success("AI Optimizer has updated your sourcing strategy for 2030.")
