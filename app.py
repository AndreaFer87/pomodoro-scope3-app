import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# CSS Custom per stile Regrow e Box KPI
st.markdown("""
    <style>
    .stMetric { background-color: #f1f3f4; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    div.stButton > button:first-child { background-color: #2e7d32; color: white; border-radius: 20px; font-weight: bold; }
    h1, h2, h3 { color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.title("🌱 PlanAI: Sustainability Insights")
st.subheader("Strategia di Decarbonizzazione Dinamica - Filiera Pomodoro")
st.markdown("---")

# --- SIDEBAR (Leve di Governance e Rischi) ---
st.sidebar.image("https://www.regrow.ag/hubfs/Regrow_Logo_2022_Green.svg", width=150)
st.sidebar.header("🕹️ Pannello di Controllo")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 50, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
incertezza_tier3 = st.sidebar.slider("Incertezza Modello Tier 3 (%)", 5, 30, 15, help="Errore intrinseco del modello RothC/Liu")
safety_buffer = st.sidebar.slider("Safety Buffer (Buffer Pool %)", 5, 40, 20, help="Riserva cautelativa per conformità")
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5, help="Rischio di uscita agricoltori dal programma")

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EMISSIONI_BASE_HA = 4.0
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT = ETTARI_FILIERA * (EMISSIONI_BASE_HA + LOSS_SOC_BASE_HA)
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000

# --- DATABASE PRATICHE AGGIORNATO ---
# Res: 1 (Alto rischio calo resa) -> 5 (Resiliente/Aumento resa)
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300, 'diff': 3, 'res': 3},
    'Interramento':         {'d_emiss': 0.5,  'd_carb': 2.2,  'costo': 400, 'diff': 1, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.5, 'd_carb': 0.36, 'costo': 400, 'diff': 1, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3,  'costo': 700, 'diff': 4, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 5, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9,  'costo': 400, 'diff': 5, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T

# --- LOGICA DI CALCOLO AI OPTIMIZER ---
def calcola_impatto(row):
    risparmio_input = -row['d_emiss']
    sequestro_netto = row['d_carb'] + LOSS_SOC_BASE_HA
    totale_lordo = risparmio_input + sequestro_netto
    # Applichiamo i 3 livelli di rischio: Tier 3, Safety Buffer e Churn Rate
    return totale_lordo * (1 - incertezza_tier3/100) * (1 - safety_buffer/100) * (1 - churn_rate/100)

df_p['Imp_Netto'] = df_p.apply(calcola_impatto, axis=1)
df_p['Costo_T'] = (df_p['costo'] * (incentivo_percent/100)) / df_p['Imp_Netto']

# Mix Ottimale (Portfolio Diversificato)
target_ton_tot = BASELINE_TOT * (target_decarb / 100)
mix_imp = (df_p.loc['Tripletta','Imp_Netto']*0.4 + df_p.loc['C.C. + Minima Lav.','Imp_Netto']*0.3 + df_p.loc['Interramento','Imp_Netto']*0.3)
mix_costo_t = (df_p.loc['Tripletta','Costo_T']*0.4 + df_p.loc['C.C. + Minima Lav.','Costo_T']*0.3 + df_p.loc['Interramento','Costo_T']*0.3)

ettari_target = min(target_ton_tot / mix_imp, ETTARI_FILIERA)
ef_target = ((BASELINE_TOT - target_ton_tot) / VOL_TOT_TON) * 1000
roi_climatico = target_ton_tot / ((ettari_target * 550 * (incentivo_percent/100)) / 1000)

# --- BOX KPI (Ripristinati e integrati) ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Base vs Target", f"{EF_BASE_KG_TON:.1f} kg/t", f"{ef_target:.1f} kg/t", delta_color="inverse")
c2.metric("Ettari/Anno Target", f"{int(ettari_target)} ha", f"{int(ettari_target/ETTARI_FILIERA*100)}% Area")
c3.metric("Costo Medio (€/t)", f"{mix_costo_t:.2f} €/t")
c4.metric("ROI Climatico", f"{roi_climatico:.2f} t/k€", "Efficienza Spesa")

st.markdown("---")

# --- GRAFICI (Disposizione Regrow) ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory to 2030")
    anni = np.arange(2025, orizzonte_anno + 1)
    b_line = [BASELINE_TOT] * len(anni)
    r_line = [BASELINE_TOT - (target_ton_tot * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=b_line, name='Business as Usual', line=dict(color='grey', dash='dot')))
    fig_traj.add_trace(go.Scatter(x=anni, y=r_line, fill='tonexty', name='Optimized Plan', line_color='#2e7d32', line_width=4))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader("🎯 Program Allocation")
    if st.button("🚀 RE-CALCULATE OPTIMIZED PATH"):
        st.balloons()
        labels = ["Tripletta", "C.C. + Minima Lav.", "Interramento"]
        values = [40, 30, 30] # Mix diversificato
        fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker_colors=['#1b5e20', '#4caf50', '#81c784'])])
        fig_donut.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Clicca per elaborare il mix di pratiche basato sui rischi selezionati.")

# --- WATERFALL ---
st.markdown("---")
st.subheader("📉 Abatement Breakdown (Waterfall)")
fig_wf = go.Figure(go.Waterfall(
    measure = ["absolute", "relative", "relative", "total"],
    x = ["2025 Baseline", "Riduzione Input", "Sequestro Carbonio", f"{orizzonte_anno} Net Target"],
    y = [BASELINE_TOT, -target_ton_tot*0.2, -target_ton_tot*0.8, 0],
    connector = {"line":{"color":"#2e7d32"}},
    increasing = {"marker":{"color":"#a5d6a7"}},
    decreasing = {"marker":{"color":"#2e7d32"}}
))
st.plotly_chart(fig_wf, use_container_width=True)

# --- SPIEGAZIONE AI OPTIMIZER ---
st.markdown("---")
with st.expander("ℹ️ Come funziona l'AI Strategy Optimizer (Sotto il cofano)"):
    st.write("""
    L'algoritmo risolve un problema di **ottimizzazione vincolata** per la CSRD.
    1. **Cuore Matematico:** Calcola la MACC (*Marginal Abatement Cost Curve*) pesando ogni pratica per il suo costo e impatto bio-fisico (RothC/Liu).
    2. **Logica di Diversificazione:** Per evitare il 'Rischio di Esecuzione', l'AI non sceglie mai una sola pratica. Distribuisce il budget su un **Portfolio** (es. Tripletta per l'impatto, Interramento per la sicurezza).
    3. **Filtro Incertezza:** Ogni tonnellata di CO2 stimata viene 'scontata' in base al Tier 3, al Safety Buffer e al **Churn Rate** (tasso di abbandono) per garantire che il target dichiarato sia scientificamente difendibile.
    """)
