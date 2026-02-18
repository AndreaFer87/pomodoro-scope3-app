import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")
st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia di Decarbonizzazione Progressiva (2025-2030)")

# --- SIDEBAR: PARAMETRI ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo a Regime (€)", value=500000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Rischio e Churn")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate_val = st.sidebar.slider("Churn Annuo (%)", 0, 20, 5)

# --- SIDEBAR: INPUT PRATICHE PULITI ---
nomi_pratiche = ['Cover Crops', 'Interramento', 'Minima Lav.', 'C.C. + Interramento', 'C.C. + Minima Lav.', 'Int. + Minima Lav.', 'Tripletta']
defaults = {'Cover Crops': {'c': 300, 'd': 2}, 'Interramento': {'c': 200, 'd': 1}, 'Minima Lav.': {'c': 250, 'd': 1}, 'C.C. + Interramento': {'c': 500, 'd': 4}, 'C.C. + Minima Lav.': {'c': 300, 'd': 3}, 'Int. + Minima Lav.': {'c': 450, 'd': 3}, 'Tripletta': {'c': 800, 'd': 5}}

st.sidebar.header("💰 Sezione Incentivi (€/ha)")
inc_configs = {p: st.sidebar.number_input(p, 0, 1500, defaults[p]['c'], key=f"inc_{p}", step=1) for p in nomi_pratiche}

st.sidebar.header("⚙️ Sezione Difficoltà (1-5)")
diff_configs = {p: st.sidebar.number_input(f"Diff. {p}", 1, 5, defaults[p]['d'], key=f"diff_{p}", step=1) for p in nomi_pratiche}

# --- DATI E DATABASE ---
VOL_TOT_TON = 800000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
anni = list(range(2025, orizzonte_anno + 1))
n_step = len(anni) - 1

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
    df_p.at[p, 'Imp_Netto'] = (-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5)

# --- MOTORE DI OTTIMIZZAZIONE (REGIME) ---
df_p['AI_Score'] = (df_p['Imp_Netto'] / (df_p['costo'] * df_p['diff'])) * df_p['res']
target_ton_regime = BASELINE_TOT * (target_decarb / 100)
ettari_regime = {p: 0.0 for p in nomi_pratiche}
temp_budget = budget_max_annuo

# Quota 5% Spot
for p in ['Cover Crops', 'Interramento']:
    ha = (target_ton_regime / df_p['Imp_Netto'].max()) * 0.05
    ettari_regime[p] = ha
    temp_budget -= ha * df_p.at[p, 'costo']

# Ottimizzazione Resto
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[p] * df_p.at[p, 'Imp_Netto'] for p in nomi_pratiche)
    if abb_attuale >= target_ton_regime or temp_budget <= 0: break
    ha_agg = min((target_ton_regime - abb_attuale)/row['Imp_Netto'], temp_budget/row['costo'])
    ettari_regime[nome] += ha_agg
    temp_budget -= ha_agg * row['costo']

# --- SIMULAZIONE TRAIETTORIA PROGRESSIVA ---
history_nette = [BASELINE_TOT]
soc_residuo = 0
# Calcoliamo l'abbattimento potenziale a regime (con safety buffer)
abb_potenziale_regime = sum(ettari_regime[p] * df_p.at[p, 'Imp_Netto'] for p in nomi_pratiche) * (1 - safety_buffer/100)

for i in range(1, len(anni)):
    # Rampa di adozione: cresce ogni anno fino al 100% nel 2030
    progressione = i / n_step 
    attivi_pct = (1 - churn_rate_val/100)
    
    # 1. Emissioni Nette degli agricoltori attivi quest'anno
    # (Usiamo la quota progressiva degli ettari a regime)
    abb_attivi = abb_potenziale_regime * progressione * attivi_pct
    
    # 2. SOC Residuo (Chi ha abbandonato negli anni passati)
    # Decade del 70%, ma si accumula dal churn della quota dell'anno precedente
    soc_chi_ha_mollato_quest_anno = (abb_potenziale_regime * (i-1)/n_step) * (1 - attivi_pct)
    soc_residuo = (soc_residuo * 0.3) + soc_chi_ha_mollato_quest_anno
    
    abb_totale = abb_attivi + soc_residuo
    history_nette.append(BASELINE_TOT - abb_totale)

# --- VISUALIZZAZIONE ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale", f"{(history_nette[-1]/VOL_TOT_TON)*1000:.1f} kg/t")
c2.metric("Ettari a Regime", f"{int(sum(ettari_regime.values()))} ha")
c3.metric("Budget 2026", f"€ {int(sum(ettari_regime.values())*df_p['costo'].mean()*(1/n_step)):,}")
c4.metric("Status 2030", "TARGET RAGGIUNTO" if history_nette[-1] <= BASELINE_TOT*(1-target_decarb/100) else "GAP PRESENTE")

st.plotly_chart(go.Figure([
    go.Scatter(x=anni, y=history_nette, name="Emissioni Nette", line=dict(color='black', width=4)),
    go.Scatter(x=anni, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni), name="Target", line=dict(dash='dash', color='blue'))
]).update_layout(title="Traiettoria di Decarbonizzazione Progressiva"), use_container_width=True)
