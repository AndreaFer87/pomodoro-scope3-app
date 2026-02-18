import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia di Decarbonizzazione Dinamica per la Filiera Pomodoro")
st.markdown("---")

# --- SIDEBAR: CONTROLLI GENERALI E RISCHIO ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=500000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5)

# --- SIDEBAR: SLIDER PRATICHE (SEZIONI SEPARATE) ---
nomi_pratiche = ['Cover Crops', 'Interramento', 'Minima Lav.', 'C.C. + Interramento', 'C.C. + Minima Lav.', 'Int. + Minima Lav.', 'Tripletta']
defaults = {
    'Cover Crops': {'c': 300, 'd': 2}, 'Interramento': {'c': 200, 'd': 1},
    'Minima Lav.': {'c': 250, 'd': 1}, 'C.C. + Interramento': {'c': 500, 'd': 4},
    'C.C. + Minima Lav.': {'c': 300, 'd': 3}, 'Int. + Minima Lav.': {'c': 450, 'd': 3},
    'Tripletta': {'c': 800, 'd': 5}
}

st.sidebar.header("💰 Sezione Incentivi (€/ha)")
inc_configs = {}
for p in nomi_pratiche:
    inc_configs[p] = st.sidebar.number_input(f"Incentivo {p}", 50, 1200, defaults[p]['c'])

st.sidebar.header("⚙️ Sezione Difficoltà Tecnica (1-5)")
diff_configs = {}
for p in nomi_pratiche:
    diff_configs[p] = st.sidebar.slider(f"Difficoltà {p}", 1, 5, defaults[p]['d'])

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
LOSS_SOC_BASE_HA = 0.5    
n_anni = orizzonte_anno - 2025

# --- DATABASE PRATICHE ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'res': 4},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.5, 'd_carb': 1.46, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.4, 'd_carb': 2.9, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T
for p in nomi_pratiche:
    df_p.at[p, 'costo_incentivo'] = inc_configs[p]
    df_p.at[p, 'diff'] = diff_configs[p]

# --- MOTORE DI OTTIMIZZAZIONE AI ---
df_p['Imp_Evitate_Ha'] = -df_p['d_emiss'] 
df_p['Imp_Sequestro_Ha'] = df_p['d_carb'] + LOSS_SOC_BASE_HA
df_p['Impatto_Netto_Ha'] = (df_p['Imp_Evitate_Ha'] + df_p['Imp_Sequestro_Ha']) * (1 - safety_buffer/100) * (1 - churn_rate/100)
df_p['AI_Score'] = (df_p['Impatto_Netto_Ha'] / (df_p['costo_incentivo'] * df_p['diff'])) * df_p['res']

target_ton_tot = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {p: 0.0 for p in nomi_pratiche}

# 1. Stima ettari totali necessari per quota 5%
best_p = df_p['AI_Score'].idxmax()
est_ettari_tot = target_ton_tot / df_p.at[best_p, 'Impatto_Netto_Ha']

# 2. Quota fissa 5% (spot)
for p_spot in ['Cover Crops', 'Interramento']:
    ha_fissi = min(est_ettari_tot * 0.05, ETTARI_FILIERA * 0.5)
    costo = ha_fissi * df_p.at[p_spot, 'costo_incentivo']
    if budget_residuo >= costo:
        ettari_allocati[p_spot] = ha_fissi
        budget_residuo -= costo

# 3. Ottimizzazione
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    curr_abb = sum(ettari_allocati[p] * df_p.at[p, 'Impatto_Netto_Ha'] for p in nomi_pratiche)
    mancante = target_ton_tot - curr_abb
    if mancante <= 0 or budget_residuo <= 0: break
    
    ha_liberi = ETTARI_FILIERA - sum(ettari_allocati.values())
    ha_finali = min(mancante / row['Impatto_Netto_Ha'], budget_residuo / row['costo_incentivo'], ha_liberi)
    
    if ha_finali > 0:
        ettari_allocati[nome] += ha_finali
        budget_residuo -= ha_finali * row['costo_incentivo']

# Risultati Finali
evitate_tot = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Evitate_Ha'] for p in nomi_pratiche) * (1-safety_buffer/100)*(1-churn_rate/100)
sequestro_tot = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Sequestro_Ha'] for p in nomi_pratiche) * (1-safety_buffer/100)*(1-churn_rate/100)
abbattimento_effettivo = evitate_tot + sequestro_tot
mancante_finale = max(0, target_ton_tot - abbattimento_effettivo)

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_effettivo)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.0f}")
c2.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha", f"Target: {target_decarb}%")
c3.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
if mancante_finale > 0:
    c4.metric("Gap Target (da abbattere)", f"{int(mancante_finale)} tCO2", delta=f"{int(mancante_finale)} t", delta_color="inverse")
else:
    c4.metric("Status Target", "RAGGIUNTO", delta="OK")

st.markdown("---")

# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory")
    anni = np.arange(2025, orizzonte_anno + 1)
    nette = [BASELINE_TOT - (abbattimento_effettivo * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_TOT * (1 - target_decarb/100)] * len(anni)
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni, y=target_line, name='Target', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Abatement Breakdown ({orizzonte_anno})")
    # CORREZIONE WATERFALL: Emissioni Evitate partono dalla Baseline
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Emissioni Evitate", "Sequestro SOC", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -evitate_tot, -sequestro_tot, 0],
        measure = ["absolute", "relative", "relative", "total"],
        base = 0,
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.subheader("🚀 Mix Allocato (Garanzia 5% spot)")
cm1, cm2 = st.columns([1, 2])
with cm1:
    for p, h in ettari_allocati.items():
        if h > 0: st.write(f"**{p}**: {int(h)} ha")
with cm2:
    fig_pie = go.Figure(data=[go.Pie(labels=[k for k,v in ettari_allocati.items() if v>0], 
                                   values=[v for v in ettari_allocati.values() if v>0], hole=.5)])
    st.plotly_chart(fig_pie, use_container_width=True)
