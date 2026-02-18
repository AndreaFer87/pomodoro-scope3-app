import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia con Carryover del Carbonio e Input Ottimizzati")
st.markdown("---")

# --- SIDEBAR: CONTROLLI GENERALI ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=500000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 20)
churn_rate_val = st.sidebar.slider("Tasso di Abbandono Annuo (Churn %)", 0, 20, 5)

# --- SIDEBAR: INPUT PRATICHE (PULITI) ---
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
    # label_visibility="collapsed" rimuove l'etichetta ripetuta, step=0 rimuove + e -
    inc_configs[p] = st.sidebar.number_input(f"{p}", 0, 1500, defaults[p]['c'], step=1)

st.sidebar.header("⚙️ Sezione Difficoltà (1-5)")
diff_configs = {}
for p in nomi_pratiche:
    diff_configs[p] = st.sidebar.number_input(f"Diff. {p}", 1, 5, defaults[p]['d'], step=1)

# --- DATI FISSI E DATABASE ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
LOSS_SOC_BASE_HA = 0.5    
anni_simulazione = list(range(2025, orizzonte_anno + 1))

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
    df_p.at[p, 'costo_incentivo'] = inc_configs[p]
    df_p.at[p, 'diff'] = diff_configs[p]

# --- MOTORE DI OTTIMIZZAZIONE AI ---
df_p['Imp_Evitate_Ha'] = -df_p['d_emiss'] 
df_p['Imp_Sequestro_Ha'] = df_p['d_carb'] + LOSS_SOC_BASE_HA
# Impatto per allocazione (consideriamo il churn immediato come riduzione potenziale)
df_p['Impatto_Netto_Ha'] = (df_p['Imp_Evitate_Ha'] + df_p['Imp_Sequestro_Ha']) * (1 - safety_buffer/100)
df_p['AI_Score'] = (df_p['Impatto_Netto_Ha'] / (df_p['costo_incentivo'] * df_p['diff'])) * df_p['res']

target_ton_tot = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {p: 0.0 for p in nomi_pratiche}

# 1. Quota fissa 5% spot su ettari necessari stimati
best_p = df_p['AI_Score'].idxmax()
est_ettari_tot = target_ton_tot / df_p.at[best_p, 'Impatto_Netto_Ha']
for p_spot in ['Cover Crops', 'Interramento']:
    ha_fissi = min(est_ettari_tot * 0.05, ETTARI_FILIERA * 0.5)
    if budget_residuo >= ha_fissi * df_p.at[p_spot, 'costo_incentivo']:
        ettari_allocati[p_spot] = ha_fissi
        budget_residuo -= ha_fissi * df_p.at[p_spot, 'costo_incentivo']

# 2. Ottimizzazione restanti
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    curr_abb = sum(ettari_allocati[p] * row['Impatto_Netto_Ha'] for p in nomi_pratiche)
    if curr_abb >= target_ton_tot or budget_residuo <= 0: break
    ha_liberi = ETTARI_FILIERA - sum(ettari_allocati.values())
    ha_finali = min((target_ton_tot - curr_abb)/row['Impatto_Netto_Ha'], budget_residuo/row['costo_incentivo'], ha_liberi)
    if ha_finali > 0:
        ettari_allocati[nome] += ha_finali
        budget_residuo -= ha_finali * row['costo_incentivo']

# --- CALCOLO TRAIETTORIA CON CARRYOVER (CHURN LOGIC) ---
# Chi abbandona: d_emiss torna a baseline, d_carb decade del 70% annuo (ritenzione 30%)
history_abbattimento = []
soc_accumulato_churn = 0 # Carbonio "residuo" nel suolo da chi ha mollato negli anni passati

for i, anno in enumerate(anni_simulazione):
    if anno == 2025:
        history_abbattimento.append(0)
        continue
    
    # Utenti Attivi (1 - Churn cumulato o annuale)
    # Per semplicità calcoliamo l'impatto degli attivi
    attivi_factor = (1 - churn_rate_val/100)
    
    evitate_anno = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Evitate_Ha'] for p in nomi_pratiche) * attivi_factor * (1-safety_buffer/100)
    sequestro_attivi = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Sequestro_Ha'] for p in nomi_pratiche) * attivi_factor * (1-safety_buffer/100)
    
    # Carryover del Carbonio dagli anni precedenti (Decadimento 70%)
    # Ogni anno il carbonio "vecchio" di chi ha abbandonato si riduce
    soc_accumulato_churn = (soc_accumulato_churn * 0.3) + (sequestro_attivi * (churn_rate_val/100))
    
    abb_totale_anno = evitate_anno + sequestro_attivi + soc_accumulato_churn
    history_abbattimento.append(abb_totale_anno)

final_evitate = evitate_anno
final_sequestro = sequestro_attivi + soc_accumulato_churn
abbattimento_effettivo = history_abbattimento[-1]
mancante_finale = max(0, target_ton_tot - abbattimento_effettivo)

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - abbattimento_effettivo)/VOL_TOT_TON)*1000:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.0f}")
c2.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha", f"Target: {target_decarb}%")
c3.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
if mancante_finale > 0:
    c4.metric("Gap Target", f"{int(mancante_finale)} tCO2", delta=f"NON RAGGIUNTO", delta_color="inverse")
else:
    c4.metric("Status Target", "RAGGIUNTO", delta="OK")

st.markdown("---")

# --- GRAFICI ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory (con Carbon Carryover)")
    nette = [BASELINE_TOT - history_abbattimento[i] for i in range(len(anni_simulazione))]
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni_simulazione, y=nette, name='Emissioni Nette', line=dict(color='black', width=4)))
    fig_traj.add_trace(go.Scatter(x=anni_simulazione, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni_simulazione), name='Target', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Abatement Breakdown ({orizzonte_anno})")
    
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Emissioni Evitate", "Sequestro SOC (incl. Carryover)", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -final_evitate, -final_sequestro, 0],
        measure = ["absolute", "relative", "relative", "total"],
        decreasing = {"marker":{"color":"#2e7d32"}}
    ))
    st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.subheader("🚀 Mix Allocato (Dettaglio Pratiche)")
cm1, cm2 = st.columns([1, 2])
with cm1:
    for p, h in ettari_allocati.items():
        if h > 0: st.write(f"**{p}**: {int(h)} ha")
with cm2:
    fig_pie = go.Figure(data=[go.Pie(labels=[k for k,v in ettari_allocati.items() if v>0], 
                                   values=[v for v in ettari_allocati.values() if v>0], hole=.5)])
    st.plotly_chart(fig_pie, use_container_width=True)
