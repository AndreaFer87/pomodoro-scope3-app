import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Dashboard Strategica", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Simulatore di Decarbonizzazione con Ottimizzazione MCDA")
st.markdown("---")

# --- SIDEBAR: TUTTI GLI SLIDER E BOX ---
st.sidebar.header("🎯 Target e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Massimo (€)", value=1000000, step=50000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Temporale", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.header("⚖️ Strategia Operativa")
alpha = st.sidebar.slider(
    "α - Avversione alla Complessità", 
    0.5, 4.0, 1.5, 0.1,
    help="Basso: punta alla densità di CO2 (pratiche difficili). Alto: punta alla facilità d'uso (grandi superfici)."
)

st.sidebar.header("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 12)
churn_rate = st.sidebar.slider("Tasso di Abbandono Annuo (Churn %)", 0, 20, 8)

# --- DATI E LOGICA DI CALCOLO ---
pratiche_data = {
    'Cover Crops':          {'costo': 250, 'diff': 2.0, 'd_emiss': 0.2,  'd_carb': 1.1},
    'Interramento':         {'costo': 200, 'diff': 1.5, 'd_emiss': 0.3,  'd_carb': 2.0},
    'Minima Lav.':          {'costo': 250, 'diff': 1.0, 'd_emiss': -0.7, 'd_carb': 0.36},
    'C.C. + Interramento':  {'costo': 450, 'diff': 4.0, 'd_emiss': 0.5,  'd_carb': 3.0},
    'C.C. + Minima Lav.':   {'costo': 350, 'diff': 3.0, 'd_emiss': -0.5, 'd_carb': 1.46},
    'Int. + Minima Lav.':   {'costo': 450, 'diff': 3.5, 'd_emiss': -0.4, 'd_carb': 2.7},
    'Tripletta':            {'costo': 800, 'diff': 5.0, 'd_emiss': 0.2,  'd_carb': 3.5}
}

df_p = pd.DataFrame(pratiche_data).T
# Calcolo Impatto Netto (Premio CO2)
df_p['Imp_Netto'] = ((-df_p['d_emiss'] + df_p['d_carb'] + 0.5) * (1 - safety_buffer/100))
# Calcolo Score MCDA (Ranking)
df_p['Score'] = df_p['Imp_Netto'] / (df_p['costo'] * (df_p['diff']**alpha))

# --- MOTORE DI ALLOCAZIONE ---
ETTARI_FILIERA = 10000
BASELINE_TOT = 40000 
target_ton = BASELINE_TOT * (target_decarb / 100)
budget_restante = budget_max
ettari_allocati = {p: 0.0 for p in df_p.index}

df_sorted = df_p.sort_values(by='Score', ascending=False)

for nome, row in df_sorted.iterrows():
    attuale = sum(ettari_allocati[pr] * df_p.at[pr, 'Imp_Netto'] for pr in df_p.index)
    if attuale >= target_ton or budget_restante <= 0: break
    
    cap_operativo = ETTARI_FILIERA / (row['diff']**(alpha/2))
    ha_mancanti = (target_ton - attuale) / row['Imp_Netto']
    ha_finanziabili = budget_restante / row['costo']
    ha_fisici = ETTARI_FILIERA - sum(ettari_allocati.values())
    
    da_aggiungere = max(0, min(ha_mancanti, ha_finanziabili, cap_operativo, ha_fisici))
    ettari_allocati[nome] += da_aggiungere
    budget_restante -= da_aggiungere * row['costo']

# --- SIMULAZIONE TRAIETTORIA ---
anni = list(range(2025, orizzonte_anno + 1))
n_step = len(anni) - 1
history = [0]
abb_regime = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Netto'] for p in df_p.index)

for i in range(1, len(anni)):
    prog = i / n_step
    attivi = 1 - (churn_rate / 100)
    abb = abb_regime * prog * attivi
    history.append(abb)

# --- LAYOUT DASHBOARD ---
# Box KPI superiori
c1, c2, c3, c4 = st.columns(4)
abb_finale = history[-1]
gap = max(0, target_ton - abb_finale)

c1.metric("Superficie Totale", f"{int(sum(ettari_allocati.values()))} ha", "Copertura Filiera")
c2.metric("CO2 Abbattuta", f"{int(abb_finale)} t", f"Target: {int(target_ton)}")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}", delta=f"-€{int(budget_max - budget_restante)} spesi", delta_color="inverse")
if gap <= 10:
    c4.metric("Stato Target", "RAGGIUNTO", delta="✅ OK")
else:
    c4.metric("Gap al Target", f"{int(gap)} tCO2", delta="❌ MISS", delta_color="inverse")

st.markdown("---")

# Area Grafici
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Traiettoria delle Emissioni Nette")
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT - h for h in history], 
                                 name="Emissioni Nette", line=dict(color='#1f77b4', width=4), mode='lines+markers'))
    fig_traj.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni), 
                                 name="Soglia Target", line=dict(dash='dash', color='red')))
    fig_traj.update_layout(margin=dict(l=0,r=0,b=0,t=30), height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader("📊 Portfolio Mix (Ettari)")
    labels = [k for k,v in ettari_allocati.items() if v > 0]
    values = [v for v in ettari_allocati.values() if v > 0]
    if values:
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, textinfo='label+percent')])
        fig_pie.update_layout(margin=dict(l=0,r=0,b=0,t=30), height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aumenta il budget o abbassa il target per vedere il mix.")

# Box informativo finale
st.markdown("---")
st.write("### 🚀 Strategia Operativa Consigliata")
active_p = [(p, h) for p, h in ettari_allocati.items() if h > 0]
if active_p:
    cols = st.columns(len(active_p))
    for i, (p, h) in enumerate(active_p):
        cols[i].success(f"**{p}**\n\n{int(h)} ettari")
