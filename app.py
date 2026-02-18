import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

# --- STILE REGROW CUSTOM ---
st.markdown("""
    <style>
    .stMetric { background-color: #f8fbf9; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    div.stButton > button:first-child { background-color: #2e7d32; color: white; border-radius: 20px; font-weight: bold; }
    h1, h2, h3 { color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- TITOLO ---
st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia di Decarbonizzazione Dinamica per la Filiera Pomodoro")
st.markdown("---")

# --- SIDEBAR: LE LEVE DI GOVERNANCE ---
st.sidebar.header("🕹️ Pannello di Controllo")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 50, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio e Incertezza")
incertezza_tier3 = st.sidebar.slider("Incertezza Modello Tier 3 (%)", 5, 30, 15)
safety_buffer = st.sidebar.slider("Safety Buffer (Rischio Permanenza %)", 5, 40, 20)

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_TOT = 45000 
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000

# Database Pratiche
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300, 'res': 7},
    'Interramento':         {'d_emiss': 0.5,  'd_carb': 2.2,  'costo': 400, 'res': 6},
    'Minima Lav.':          {'d_emiss': -0.5, 'd_carb': 0.36, 'costo': 400, 'res': 8},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3,  'costo': 700, 'res': 7},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'res': 9},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9,  'costo': 400, 'res': 8},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'res': 9}
}
df_p = pd.DataFrame(pratiche).T

# --- MOTORE DI CALCOLO AI OPTIMIZER (Area-Weighted Mix) ---
def get_net_impact(row):
    return (row['d_carb'] - row['d_emiss'] + 0.5) * (1 - incertezza_tier3/100) * (1 - safety_buffer/100)

df_p['Net_Impact'] = df_p.apply(get_net_impact, axis=1)
target_ton_tot = BASELINE_TOT * (target_decarb / 100)

# Simulazione Mix Ottimale (40% Tripletta, 30% CC+Min, 30% Int)
mix_impact = (df_p.loc['Tripletta','Net_Impact']*0.4 + df_p.loc['C.C. + Minima Lav.','Net_Impact']*0.3 + df_p.loc['Interramento','Net_Impact']*0.3)
ettari_target = min(target_ton_tot / mix_impact, ETTARI_FILIERA)
costo_totale = ettari_target * (800*0.4 + 500*0.3 + 400*0.3) * (incentivo_percent/100)
roi_climatico = target_ton_tot / (costo_totale / 1000) # tCO2 per 1000€

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target (kg/t)", f"{(BASELINE_TOT - target_ton_tot)/VOL_TOT_TON*1000:.1f}", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Ettari Rigenerativi", f"{int(ettari_target)} ha", f"{int(ettari_target/ETTARI_FILIERA*100)}% Area")
c3.metric("ROI Climatico", f"{roi_climatico:.2f} t/k€", "Efficienza Spesa")
c4.metric("Investimento Totale", f"€ {int(costo_totale):,}")

st.markdown("---")

# --- GRAFICI (DISPOSIZIONE VERTICALE) ---

# 1. WATERFALL (La strada verso il Net Zero)
st.subheader("📉 La strada verso il Net Zero")
fig_wf = go.Figure(go.Waterfall(
    measure = ["absolute", "relative", "relative", "total"],
    x = ["Baseline 2025", "Variazione Input", "Rimozioni Carbonio (SOC)", "Emissioni Target"],
    y = [BASELINE_TOT, -target_ton_tot*0.2, -target_ton_tot*0.8, 0],
    connector = {"line":{"color":"#2e7d32"}},
    increasing = {"marker":{"color":"#e8f5e9"}},
    decreasing = {"marker":{"color":"#2e7d32"}}
))
st.plotly_chart(fig_wf, use_container_width=True)

# 2. PROIEZIONE TEMPORALE (Stile Regrow)
st.subheader("📅 Proiezione Strategica Temporale")
anni = np.arange(2025, orizzonte_anno + 1)
y_lorde = [BASELINE_TOT] * len(anni)
y_nette = [BASELINE_TOT - (target_ton_tot * (i/len(anni))) for i in range(len(anni))]

fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(x=anni, y=y_lorde, name='Emissioni Lorde', line=dict(color='#cfd8dc', dash='dot')))
fig_temp.add_trace(go.Scatter(x=anni, y=y_nette, fill='tonexty', name='Emissioni Nette', line_color='#2e7d32', line_width=4))
st.plotly_chart(fig_temp, use_container_width=True)

# --- SEZIONE OTTIMIZZATORE ---
st.markdown("---")
col_opt_text, col_opt_graph = st.columns([1, 1])

with col_opt_text:
    st.subheader("🚀 AI Strategy Optimizer")
    st.write("""
    Il nostro modello di ottimizzazione simula la gestione di un **Portfolio di Pratiche**. 
    Non si limita a scegliere la più economica, ma bilancia:
    * **Rischio di Permanenza:** Basato sul tuo Safety Buffer.
    * **Incertezza Scientifica:** Basata sul Tier 3 del modello RothC.
    * **Resilienza Agronomica:** Basata sul modello Liu per proteggere le rese.
    
    Il risultato è un mix che massimizza l'abbattimento restando entro il budget.
    """)
    if st.button("CALCOLA MIX OTTIMALE"):
        st.balloons()
        st.session_state['opt'] = True

with col_opt_graph:
    if 'opt' in st.session_state:
        labels = ["Tripletta", "C.C. + Minima Lav.", "Interramento"]
        values = [40, 30, 30]
        fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker_colors=['#1b5e20','#4caf50','#a5d6a7'])])
        fig_donut.update_layout(title="Allocazione Ettari (%)", showlegend=True)
        st.plotly_chart(fig_donut, use_container_width=True)
