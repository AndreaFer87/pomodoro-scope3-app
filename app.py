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

# --- SIDEBAR: SLIDER PER SINGOLA PRATICA ---
st.sidebar.header("🚜 Parametri per Pratica")
configs = {}
nomi_pratiche = ['Cover Crops', 'Interramento', 'Minima Lav.', 'C.C. + Interramento', 'C.C. + Minima Lav.', 'Int. + Minima Lav.', 'Tripletta']

for p in nomi_pratiche:
    with st.sidebar.expander(f"Impostazioni {p}"):
        default_inc = 250 if p in ['Cover Crops', 'Interramento', 'Minima Lav.'] else 500
        inc = st.slider(f"Incentivo (€/ha) - {p}", 50, 1000, default_inc)
        diff = st.slider(f"Difficoltà (1-5) - {p}", 1, 5, 2 if len(p) < 15 else 4)
        configs[p] = {'incentivo': inc, 'diff': diff}

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
    df_p.at[p, 'costo_incentivo'] = configs[p]['incentivo']
    df_p.at[p, 'diff'] = configs[p]['diff']

# --- MOTORE DI OTTIMIZZAZIONE AI ---
df_p['Imp_Evitate_Ha'] = -df_p['d_emiss'] 
df_p['Imp_Sequestro_Ha'] = df_p['d_carb'] + LOSS_SOC_BASE_HA
df_p['Impatto_Netto_Ha'] = (df_p['Imp_Evitate_Ha'] + df_p['Imp_Sequestro_Ha']) * (1 - safety_buffer/100) * (1 - churn_rate/100)

# ROI Climatico pesato su stabilità e accettabilità
df_p['AI_Score'] = (df_p['Impatto_Netto_Ha'] / (df_p['costo_incentivo'] * df_p['diff'])) * df_p['res']

target_ton_anno = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {p: 0.0 for p in nomi_pratiche}

# --- LOGICA DI OTTIMIZZAZIONE CON VINCOLO DI MIX ---
# 1. Calcoliamo prima quanti ettari totali servirebbero "idealmente" usando la pratica migliore
best_practice = df_p['AI_Score'].idxmax()
est_ettari_totali = target_ton_anno / df_p.at[best_practice, 'Impatto_Netto_Ha']

# 2. Applichiamo la quota minima del 10% (spot) sugli ettari stimati necessari
for p_spot in ['Cover Crops', 'Interramento']:
    quota_minima_ha = est_ettari_totali * 0.10
    costo_quota = quota_minima_ha * df_p.at[p_spot, 'costo_incentivo']
    
    if budget_residuo >= costo_quota:
        ettari_allocati[p_spot] = quota_minima_ha
        budget_residuo -= costo_quota

# 3. Completiamo il target con le restanti pratiche seguendo l'AI Score
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    evitate_curr = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Evitate_Ha'] for p in nomi_pratiche) * (1 - safety_buffer/100) * (1 - churn_rate/100)
    sequestro_curr = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Sequestro_Ha'] for p in nomi_pratiche) * (1 - safety_buffer/100) * (1 - churn_rate/100)
    
    abbattimento_mancante = target_ton_anno - (evitate_curr + sequestro_curr)
    if abbattimento_mancante <= 0 or budget_residuo <= 0: break
    
    ha_liberi_filiera = ETTARI_FILIERA - sum(ettari_allocati.values())
    ha_necessari = abbattimento_mancante / row['Impatto_Netto_Ha']
    ha_finanziabili = budget_residuo / row['costo_incentivo']
    ha_finali = max(0, min(ha_necessari, ha_finanziabili, ha_liberi_filiera))
    
    ettari_allocati[nome] += ha_finali
    budget_residuo -= ha_finali * row['costo_incentivo']

# Calcolo risultati finali depurati
final_evitate = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Evitate_Ha'] for p in nomi_pratiche) * (1 - safety_buffer/100) * (1 - churn_rate/100)
final_sequestro = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Sequestro_Ha'] for p in nomi_pratiche) * (1 - safety_buffer/100) * (1 - churn_rate/100)
abbattimento_totale = final_evitate + final_sequestro

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_totale)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha", f"{(sum(ettari_allocati.values())/ETTARI_FILIERA)*100:.1f}% Filiera")
c3.metric("Eur/Ton Abbattimento", f"{(budget_max_annuo - budget_residuo)/max(1, abbattimento_totale):.2f} €/t")
c4.metric("Investimento Totale", f"€ {int((budget_max_annuo - budget_residuo) * n_anni):,}", f"{n_anni} anni")

if budget_residuo > 0:
    st.info(f"💰 Budget Residuo: €{int(budget_residuo):,} (Risorse non utilizzate)")

st.markdown("---")

# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory")
    anni = np.arange(2025, orizzonte_anno + 1)
    nette = [BASELINE_TOT - (abbattimento_totale * (i/max(1, len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_TOT * (1 - target_decarb/100)] * len(anni)
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni, y=target_line, name='Target', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Abatement Breakdown (Target {orizzonte_anno})")
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Emissioni Evitate", "Sequestro SOC", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -final_evitate, -final_sequestro, 0],
        measure = ["absolute", "relative", "relative", "total"],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.subheader("🚀 Mix Ottimizzato (con garanzia 10% pratiche spot)")
if any(ettari_allocati.values()):
    cm1, cm2 = st.columns([1, 2])
    with cm1:
        for p, h in ettari_allocati.items():
            if h > 0: st.write(f"**{p}**: {int(h)} ha")
    with cm2:
        fig_pie = go.Figure(data=[go.Pie(labels=[k for k,v in ettari_allocati.items() if v>0], 
                                       values=[v for v in ettari_allocati.values() if v>0], hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)
