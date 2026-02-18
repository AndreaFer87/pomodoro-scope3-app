import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Agri-E-MRV | Plan & Govern", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione AI e Strategia di Decarbonizzazione Progressiva")
st.markdown("---")

# --- SIDEBAR: PARAMETRI GENERALI ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo a Regime (€)", value=500000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate_val = st.sidebar.slider("Tasso di Abbandono Annuo (Churn %)", 0, 20, 5)

# --- SIDEBAR: INPUT PRATICHE (Digitazione diretta, no ripetizioni) ---
nomi_pratiche = ['Cover Crops', 'Interramento', 'Minima Lav.', 'C.C. + Interramento', 'C.C. + Minima Lav.', 'Int. + Minima Lav.', 'Tripletta']
defaults = {
    'Cover Crops': {'c': 300, 'd': 2}, 'Interramento': {'c': 200, 'd': 1},
    'Minima Lav.': {'c': 250, 'd': 1}, 'C.C. + Interramento': {'c': 500, 'd': 4},
    'C.C. + Minima Lav.': {'c': 300, 'd': 3}, 'Int. + Minima Lav.': {'c': 450, 'd': 3},
    'Tripletta': {'c': 800, 'd': 5}
}

st.sidebar.header("💰 Sezione Incentivi (€/ha)")
inc_configs = {p: st.sidebar.number_input(p, 0, 1500, defaults[p]['c'], key=f"inc_{p}", step=1) for p in nomi_pratiche}

st.sidebar.header("⚙️ Sezione Difficoltà (1-5)")
diff_configs = {p: st.sidebar.number_input(f"Diff. {p}", 1, 5, defaults[p]['d'], key=f"diff_{p}", step=1) for p in nomi_pratiche}

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
anni_sim = list(range(2025, orizzonte_anno + 1))
n_step = len(anni_sim) - 1

# --- DATABASE PRATICHE AGGIORNATO ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'res': 4},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.0, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.0, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.5, 'd_carb': 1.46, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.4, 'd_carb': 2.7, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.5, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T
for p in nomi_pratiche:
    df_p.at[p, 'costo'] = inc_configs[p]
    df_p.at[p, 'diff'] = diff_configs[p]
    df_p.at[p, 'Imp_Netto_Ha'] = (-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5)

# --- MOTORE DI OTTIMIZZAZIONE AI (Calcolo Target a Regime) ---
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo'] * df_p['diff'])) * df_p['res']
target_ton_regime = BASELINE_TOT * (target_decarb / 100)
budget_residuo_regime = budget_max_annuo
ettari_regime = {p: 0.0 for p in nomi_pratiche}

# 1. Vincolo 5% Pratiche Spot
for p in ['Cover Crops', 'Interramento']:
    ha_spot = (target_ton_regime / df_p['Imp_Netto_Ha'].max()) * 0.05
    if budget_residuo_regime >= ha_spot * df_p.at[p, 'costo']:
        ettari_regime[p] = ha_spot
        budget_residuo_regime -= ha_spot * df_p.at[p, 'costo']

# 2. Ottimizzazione AI per il resto del target
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[pr] * df_p.at[pr, 'Imp_Netto_Ha'] for pr in nomi_pratiche)
    if abb_attuale >= target_ton_regime or budget_residuo_regime <= 0: break
    
    ha_mancanti_target = (target_ton_regime - abb_attuale) / row['Imp_Netto_Ha']
    ha_finanziabili = budget_residuo_regime / row['costo']
    ha_liberi = ETTARI_FILIERA - sum(ettari_regime.values())
    
    ha_finali = max(0, min(ha_mancanti_target, ha_finanziabili, ha_liberi))
    ettari_regime[nome] += ha_finali
    budget_residuo_regime -= ha_finali * row['costo']

# --- SIMULAZIONE TRAIETTORIA PROGRESSIVA ---
history_abbattimento = [0]
soc_residuo_churn = 0
abb_potenziale_regime = sum(ettari_regime[p] * df_p.at[p, 'Imp_Netto_Ha'] for p in nomi_pratiche) * (1 - safety_buffer/100)

for i in range(1, len(anni_sim)):
    quota_progressione = i / n_step
    attivi = 1 - (churn_rate_val / 100)
    
    # Abbattimento attivi (rampa progressiva)
    abb_attivi = abb_potenziale_regime * quota_progressione * attivi
    
    # Carryover SOC (Decadimento 70% di chi ha mollato rispetto alla quota dell'anno precedente)
    soc_perso_anno = (abb_potenziale_regime * (i-1)/n_step) * (1 - attivi)
    soc_residuo_churn = (soc_residuo_churn * 0.3) + soc_perso_anno
    
    history_abbattimento.append(abb_attivi + soc_residuo_churn)

# --- KPI BOX IN ALTO ---
abb_finale = history_abbattimento[-1]
gap_finale = max(0, target_ton_regime - abb_finale)

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale 2030", f"{((BASELINE_TOT - abb_finale)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: 50")
c2.metric("Ettari a Regime", f"{int(sum(ettari_regime.values()))} ha", f"{(sum(ettari_regime.values())/ETTARI_FILIERA)*100:.1f}% Filiera")
c3.metric("Budget Residuo", f"€ {int(budget_residuo_regime):,}")
if gap_finale > 0:
    c4.metric("Gap al Target", f"{int(gap_finale)} tCO2", delta="NON RAGGIUNTO", delta_color="inverse")
else:
    c4.metric("Status Target", "RAGGIUNTO", delta="OK")

if budget_residuo_regime > 0:
    st.success(f"💰 Budget Residuo a regime: €{int(budget_residuo_regime):,} (Obiettivo raggiunto con efficienza)")

st.markdown("---")

# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory (Adozione Progressiva)")
    nette = [BASELINE_TOT - h for h in history_abbattimento]
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni_sim, y=nette, name='Emissioni Nette', line=dict(color='black', width=4), mode='lines+markers'))
    fig_traj.add_trace(go.Scatter(x=anni_sim, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni_sim), name='Target', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Abatement Breakdown ({orizzonte_anno})")
    evitate_f = sum(ettari_regime[p] * -df_p.at[p, 'd_emiss'] for p in nomi_pratiche) * (i/n_step) * (1-safety_buffer/100)
    sequestro_f = abb_finale - evitate_f
    
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Emissioni Evitate", "Sequestro SOC (incl. Carryover)", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -evitate_f, -sequestro_f, 0],
        measure = ["absolute", "relative", "relative", "total"],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.subheader("🚀 Mix Pratiche Ottimizzato (Allocazione a Regime)")
cm1, cm2 = st.columns([1, 2])
with cm1:
    for p, h in ettari_regime.items():
        if h > 0: st.write(f"**{p}**: {int(h)} ha")
with cm2:
    fig_pie = go.Figure(data=[go.Pie(labels=[k for k,v in ettari_regime.items() if v>0], 
                                   values=[v for v in ettari_regime.values() if v>0], hole=.5)])
    st.plotly_chart(fig_pie, use_container_width=True)
