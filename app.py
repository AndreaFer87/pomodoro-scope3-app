import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia Decarbonizzazione con Dinamica di Decadimento SOC")
st.markdown("---")

# --- SIDEBAR: PARAMETRI GENERALI ---
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
inc_configs = {p: st.sidebar.number_input(p, 0, 1500, defaults[p]['c'], key=f"inc_{p}", step=1) for p in nomi_pratiche}

st.sidebar.header("⚙️ Sezione Difficoltà (1-5)")
diff_configs = {p: st.sidebar.number_input(f"Diff. {p}", 1, 5, defaults[p]['d'], key=f"diff_{p}", step=1) for p in nomi_pratiche}

# --- DATI FISSI E DATABASE ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EF_BASE_KG_TON = 50.0  
BASELINE_TOT = (EF_BASE_KG_TON * VOL_TOT_TON) / 1000 
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
    df_p.at[p, 'Imp_Netto_Ha'] = (-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5)

# --- OTTIMIZZAZIONE AI ---
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo_incentivo'] * df_p['diff'])) * df_p['res']
target_ton_tot = BASELINE_TOT * (target_decarb / 100)
budget_residuo = budget_max_annuo
ettari_allocati = {p: 0.0 for p in nomi_pratiche}

# Quota 5% spot
est_ettari_tot = target_ton_tot / df_p['Imp_Netto_Ha'].max()
for p in ['Cover Crops', 'Interramento']:
    ha = min(est_ettari_tot * 0.05, ETTARI_FILIERA * 0.5)
    if budget_residuo >= ha * df_p.at[p, 'costo_incentivo']:
        ettari_allocati[p] = ha
        budget_residuo -= ha * df_p.at[p, 'costo_incentivo']

# Resto
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)
for nome, row in df_sorted.iterrows():
    curr_abb = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Netto_Ha'] for p in nomi_pratiche)
    if curr_abb >= target_ton_tot or budget_residuo <= 0: break
    ha_liberi = ETTARI_FILIERA - sum(ettari_allocati.values())
    ha_finali = min((target_ton_tot - curr_abb)/row['Imp_Netto_Ha'], budget_residuo/row['costo_incentivo'], ha_liberi)
    ettari_allocati[nome] += ha_finali
    budget_residuo -= ha_finali * row['costo_incentivo']

# --- SIMULAZIONE TRAIETTORIA (Carryover Logic) ---
history_abbattimento = [0]
soc_residuo_accumulato = 0

for anno in anni_simulazione[1:]:
    attivi_pct = (1 - churn_rate_val/100)
    
    # Impatto attivo
    evitate_anno = sum(ettari_allocati[p] * -df_p.at[p, 'd_emiss'] for p in nomi_pratiche) * attivi_pct
    sequestro_nuovo = sum(ettari_allocati[p] * (df_p.at[p, 'd_carb'] + 0.5) for p in nomi_pratiche) * attivi_pct
    
    # Decadimento del carbonio di chi ha abbandonato (30% resta)
    soc_residuo_accumulato = (soc_residuo_accumulato * 0.3) + (sum(ettari_allocati[p] * (df_p.at[p, 'd_carb'] + 0.5) for p in nomi_pratiche) * (1 - attivi_pct))
    
    abb_anno = (evitate_anno + sequestro_nuovo + soc_residuo_accumulato) * (1 - safety_buffer/100)
    history_abbattimento.append(abb_anno)

# --- UI ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Target", f"{((BASELINE_TOT - history_abbattimento[-1])/VOL_TOT_TON)*1000:.1f} kg/t")
c2.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha")
c3.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
gap = max(0, target_ton_tot - history_abbattimento[-1])
c4.metric("Status Target", "RAGGIUNTO" if gap <= 0 else f"GAP: {int(gap)} t", delta="OK" if gap <=0 else "MISS", delta_color="inverse")

st.markdown("---")
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Emissions Trajectory (Real Carryover)")
    nette = [BASELINE_TOT - h for h in history_abbattimento]
    fig_traj = go.Figure()
    fig_traj.add_trace(go.Scatter(x=anni_simulazione, y=nette, name='Emissioni Nette', line=dict(color='black', width=4), mode='lines+markers'))
    fig_traj.add_trace(go.Scatter(x=anni_simulazione, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni_simulazione), name='Target', line=dict(color='blue', dash='dash')))
    st.plotly_chart(fig_traj, use_container_width=True)

with col_right:
    st.subheader(f"📉 Breakdown {orizzonte_anno}")
    
    fig_wf = go.Figure(go.Waterfall(
        x = ["Baseline 2025", "Emissioni Evitate", "Sequestro SOC", f"Emissioni {orizzonte_anno}"],
        y = [BASELINE_TOT, -evitate_anno*(1-safety_buffer/100), -(sequestro_nuovo+soc_residuo_accumulato)*(1-safety_buffer/100), 0],
        measure = ["absolute", "relative", "relative", "total"]
    ))
    st.plotly_chart(fig_wf, use_container_width=True)
