import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# --- DATABASE PRATICHE AGGIORNATO (Costi e Combinazioni) ---
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
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte", options=[2026, 2027, 2028, 2029, 2030])

st.sidebar.subheader("🛡️ Gestione del Rischio")
incertezza_tier3 = st.sidebar.slider("Incertezza Modello (%)", 5, 30, 15)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (%)", 0, 20, 5)

# --- CALCOLI ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_LORDA = ETTARI_FILIERA * 4.5 
target_ton_tot = BASELINE_LORDA * (target_decarb / 100)

def get_net_impact(row):
    return (row['d_carb'] - row['d_emiss']) * (1 - incertezza_tier3/100) * (1 - safety_buffer/100) * (1 - churn_rate/100)

df_p['Imp_Netto'] = df_p.apply(get_net_impact, axis=1)
df_p['Costo_T'] = (df_p['costo'] * 0.75) / df_p['Imp_Netto']

# Mix Portfolio (Simulazione AI)
ettari_target = min(target_ton_tot / df_p['Imp_Netto'].mean(), ETTARI_FILIERA)
abbattimento_reale = ettari_target * df_p['Imp_Netto'].mean()
costo_totale = ettari_target * df_p['costo'].mean() * 0.75

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target (kg/t)", f"{(BASELINE_LORDA - abbattimento_reale)/VOL_TOT_TON*1000:.1f}", f"Base: {BASELINE_LORDA/VOL_TOT_TON*1000:.1f}")
c2.metric("Ettari Programma", f"{int(ettari_target)} ha")
c3.metric("Costo Medio (€/t)", f"{costo_totale/max(1, abbattimento_reale):.2f} €/t")
c4.metric("ROI Climatico", f"{abbattimento_reale/(costo_totale/1000):.2f} t/k€")

st.markdown("---")

# --- GRAFICO 1: TRAIETTORIA ---
st.subheader("📅 Emissions Trajectory: Lorde, Nette e Assorbimenti")
anni = np.arange(2025, orizzonte_anno + 1)
lorde = [BASELINE_LORDA] * len(anni)
assorbimenti = [-(abbattimento_reale * (i/(len(anni)-1))) for i in range(len(anni))]
nette = [l + a for l, a in zip(lorde, assorbimenti)]

fig_traj = go.Figure()
fig_traj.add_trace(go.Scatter(x=anni, y=lorde, name='Emissioni Lorde', line=dict(color='red', width=2)))
fig_traj.add_trace(go.Scatter(x=anni, y=assorbimenti, name='Assorbimenti (C-Removal)', fill='tozeroy', line_color='green'))
fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
fig_traj.add_hline(y=BASELINE_LORDA*(1-target_decarb/100), line_dash="dash", line_color="blue", annotation_text="TARGET")
st.plotly_chart(fig_traj, use_container_width=True)

# --- GRAFICO 2: WATERFALL ---
st.subheader("📉 Abatement Breakdown: Da Lorde a Nette")
fig_wf = go.Figure(go.Waterfall(
    measure = ["absolute", "relative", "total"],
    x = ["Emissioni Lorde Baseline", "Assorbimenti Totali (Net)", "Emissioni Nette"],
    y = [BASELINE_LORDA, -abbattimento_reale, 0],
    decreasing = {"marker":{"color":"#2e7d32"}}
))
st.plotly_chart(fig_wf, use_container_width=True)

# --- OTTIMIZZATORE ---
st.markdown("---")
if st.button("🚀 CALCOLA MIX OTTIMALE"):
    st.subheader("📊 Program Allocation (Mix Pratiche)")
    labels = ["Tripletta", "Int. + Minima Lav.", "Interramento"]
    values = [30, 40, 30] 
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, marker_colors=['#1b5e20','#4caf50','#81c784'])])
    st.plotly_chart(fig_donut)

# --- TABELLA TECNICA ---
st.markdown("---")
st.subheader("📊 Database Tecnico delle Pratiche")
st.dataframe(df_p[['d_emiss', 'd_carb', 'costo', 'res', 'Imp_Netto', 'Costo_T']].style.format("{:.2f}"))
