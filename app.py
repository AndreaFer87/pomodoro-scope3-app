import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Agri-E-MRV | Plan & Govern", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione AI: Massimizzazione Superficie su Budget")
st.markdown("---")

# --- SIDEBAR: PARAMETRI ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=500000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate_val = st.sidebar.slider("Churn Annuo (%)", 0, 20, 5)

# --- SIDEBAR: INPUT PRATICHE (Digitazione diretta) ---
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

# --- DATI FISSI ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
anni_sim = list(range(2025, orizzonte_anno + 1))
n_step = len(anni_sim) - 1

# --- DATABASE PRATICHE ---
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
    # L'impatto netto reale percepito dall'azienda (considerando il buffer)
    df_p.at[p, 'Imp_Netto_Ha'] = (-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5) * (1 - safety_buffer/100)

# --- MOTORE DI OTTIMIZZAZIONE "AGRESSIVA" ---
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo'] * df_p['diff'])) * df_p['res']
target_ton_regime = BASELINE_TOT * (target_decarb / 100)
budget_restante = budget_max_annuo
ettari_regime = {p: 0.0 for p in nomi_pratiche}

# 1. Quota 5% Spot (Sempre garantita se c'è budget)
for p in ['Cover Crops', 'Interramento']:
    # Calcolo ettari teorici per il 5% del target
    ha_teorici = (target_ton_regime * 0.05) / df_p.at[p, 'Imp_Netto_Ha']
    ha_effettivi = min(ha_teorici, budget_restante / df_p.at[p, 'costo'], ETTARI_FILIERA * 0.2)
    ettari_regime[p] = ha_effettivi
    budget_restante -= ha_effettivi * df_p.at[p, 'costo']

# 2. Riempimento fino al Target O fino a esaurimento Budget/Ettari
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[pr] * df_p.at[pr, 'Imp_Netto_Ha'] for pr in nomi_pratiche)
    
    if budget_restante <= 0: break
    
    # Se non abbiamo raggiunto il target, compriamo il più possibile
    ha_liberi = ETTARI_FILIERA - sum(ettari_regime.values())
    if ha_liberi <= 0: break
    
    # Quanti ne servirebbero per chiudere il gap?
    ha_per_target = max(0, (target_ton_regime - abb_attuale) / row['Imp_Netto_Ha'])
    # Quanti ne posso comprare con i soldi rimasti?
    ha_per_budget = budget_restante / row['costo']
    
    # Prendo il minimo tra necessità, portafoglio e terra libera
    # Se il target è già raggiunto, l'AI si ferma (risparmio budget)
    if abb_attuale < target_ton_regime:
        ha_da_aggiungere = min(ha_per_target, ha_per_budget, ha_liberi)
    else:
        ha_da_aggiungere = 0
        
    ettari_regime[nome] += ha_da_aggiungere
    budget_restante -= ha_da_aggiungere * row['costo']

# --- SIMULAZIONE TRAIETTORIA ---
history_abbattimento = [0]
soc_residuo = 0
abb_regime_reale = sum(ettari_regime[p] * df_p.at[p, 'Imp_Netto_Ha'] for p in nomi_pratiche)

for i in range(1, len(anni_sim)):
    quota_prog = i / n_step
    attivi = 1 - (churn_rate_val / 100)
    
    # Abbattimento attivo
    abb_attivi = abb_regime_reale * quota_prog * attivi
    # SOC Residuo (Decadimento 70%)
    soc_perso = (abb_regime_reale * ((i-1)/n_step)) * (1 - attivi)
    soc_residuo = (soc_residuo * 0.3) + soc_perso
    
    history_abbattimento.append(abb_attivi + soc_residuo)

# --- UI ---
abb_f = history_abbattimento[-1]
gap_f = max(0, target_ton_regime - abb_f)

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale 2030", f"{((BASELINE_TOT - abb_f)/VOL_TOT_TON)*1000:.1f} kg/t", f"Target: {(BASELINE_TOT*(1-target_decarb/100)/VOL_TOT_TON)*1000:.1f}")
c2.metric("Ettari a Regime", f"{int(sum(ettari_regime.values()))} ha", f"Tot Filiera: {ETTARI_FILIERA}")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}")
if gap_f > 1:
    c4.metric("Gap al Target", f"{int(gap_f)} tCO2", delta="NON RAGGIUNTO", delta_color="inverse")
else:
    c4.metric("Status Target", "RAGGIUNTO", delta="OK")

st.markdown("---")
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📅 Emissions Trajectory (Adozione Progressiva)")
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni_sim, y=[BASELINE_TOT - h for h in history_abbattimento], name="Nette", line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni_sim, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni_sim), name="Target", line=dict(dash='dash', color='blue')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_r:
    st.subheader(f"📉 Breakdown {orizzonte_anno}")
    ev_f = sum(ettari_regime[p] * -df_p.at[p, 'd_emiss'] for p in nomi_pratiche) * (1-safety_buffer/100)
    sq_f = abb_f - ev_f
    st.plotly_chart(go.Figure(go.Waterfall(
        x = ["Baseline", "Evitate", "Sequestro", "Finale"],
        y = [BASELINE_TOT, -ev_f, -sq_f, 0],
        measure = ["absolute", "relative", "relative", "total"]
    )), use_container_width=True)

st.subheader("🚀 Mix Pratiche Ottimizzato")
col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    for p, h in ettari_regime.items():
        if h > 0: st.write(f"**{p}**: {int(h)} ha")
with col_t2:
    st.plotly_chart(go.Figure(data=[go.Pie(labels=[k for k,v in ettari_regime.items() if v>0], values=[v for v in ettari_regime.values() if v>0], hole=.5)]), use_container_width=True)
