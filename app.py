import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Decision Support System: Ottimizzazione MCDA & Traiettoria SOC")
st.markdown("---")

# --- SIDEBAR: PARAMETRI GENERALI ---
st.sidebar.header("🕹️ Parametri Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Massimo (€)", value=600000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 12)
churn_rate_val = st.sidebar.slider("Churn Annuo (%)", 0, 20, 12)

# --- SIDEBAR: LOGICA MCDA (Il cuore della tua strategia) ---
st.sidebar.header("⚖️ Strategia Operativa (MCDA)")
alpha = st.sidebar.slider(
    "α - Avversione alla Complessità", 
    0.5, 3.0, 1.5, 0.1,
    help="ALTO: favorisce pratiche semplici (scalabilità) ma richiede più ettari. BASSO: favorisce pratiche complesse (densità) su pochi ettari."
)

if alpha > 2.2:
    st.sidebar.warning("🚀 Strategia: Massima Scalabilità (Pratiche facili, superfici ampie)")
elif alpha < 0.8:
    st.sidebar.error("🔬 Strategia: High-Tech (Pochi ettari, alta complessità)")

# --- SIDEBAR: INPUT PRATICHE ---
nomi_pratiche = ['Cover Crops', 'Interramento', 'Minima Lav.', 'C.C. + Interramento', 'C.C. + Minima Lav.', 'Int. + Minima Lav.', 'Tripletta']
defaults = {
    'Cover Crops': {'c': 250, 'd': 2}, 'Interramento': {'c': 200, 'd': 1},
    'Minima Lav.': {'c': 250, 'd': 1}, 'C.C. + Interramento': {'c': 450, 'd': 4},
    'C.C. + Minima Lav.': {'c': 350, 'd': 3}, 'Int. + Minima Lav.': {'c': 450, 'd': 3},
    'Tripletta': {'c': 800, 'd': 5}
}

st.sidebar.header("💰 Sezione Incentivi (€/ha)")
inc_configs = {p: st.sidebar.number_input(p, 0, 1500, defaults[p]['c'], key=f"inc_{p}") for p in nomi_pratiche}

st.sidebar.header("⚙️ Sezione Difficoltà (1-5)")
diff_configs = {p: st.sidebar.number_input(f"Diff. {p}", 1, 5, defaults[p]['d'], key=f"diff_{p}") for p in nomi_pratiche}

# --- DATI E DATABASE ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_TOT = (50.0 * VOL_TOT_TON) / 1000 
anni_sim = list(range(2025, orizzonte_anno + 1))
n_step = len(anni_sim) - 1

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
    df_p.at[p, 'Imp_Netto_Ha'] = (-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5) * (1 - safety_buffer/100)

# --- MOTORE DI OTTIMIZZAZIONE MCDA ---
# Lo score ora è influenzato da alpha: (Impatto / (Costo * Difficoltà^alpha))
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo'] * (df_p['diff']**alpha))) * df_p['res']

target_ton_regime = BASELINE_TOT * (target_decarb / 100)
budget_restante = budget_max_annuo
ettari_regime = {p: 0.0 for p in nomi_pratiche}

# 1. Fondamenta (5% target su pratiche semplici)
for p in ['Cover Crops', 'Interramento']:
    ha_fissi = (target_ton_regime * 0.05) / df_p.at[p, 'Imp_Netto_Ha']
    ettari_regime[p] = min(ha_fissi, ETTARI_FILIERA*0.2)
    budget_restante -= ettari_regime[p] * df_p.at[p, 'costo']

# 2. Allocazione ROI-Driven con Cap Operativo dinamico
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[pr] * df_p.at[pr, 'Imp_Netto_Ha'] for pr in nomi_pratiche)
    if abb_attuale >= target_ton_regime or budget_restante <= 0: break
    
    # Cap basato sulla difficoltà: se alpha è alto, le pratiche difficili saturano subito
    cap_operativo = ETTARI_FILIERA / (row['diff']**(alpha/2)) 
    ha_disponibili = max(0, cap_operativo - ettari_regime[nome])
    
    ha_mancanti = (target_ton_regime - abb_attuale) / row['Imp_Netto_Ha']
    ha_finanziabili = budget_restante / row['costo']
    
    ha_da_aggiungere = min(ha_mancanti, ha_finanziabili, ha_disponibili, ETTARI_FILIERA - sum(ettari_regime.values()))
    ettari_regime[nome] += ha_da_aggiungere
    budget_restante -= ha_da_aggiungere * row['costo']

# --- SIMULAZIONE TRAIETTORIA ---
history_abb = [0]
soc_residuo = 0
abb_regime_reale = sum(ettari_regime[p] * df_p.at[p, 'Imp_Netto_Ha'] for p in nomi_pratiche)

for i in range(1, len(anni_sim)):
    prog = i / n_step
    attivi = 1 - (churn_rate_val / 100)
    abb_attivi = abb_regime_reale * prog * attivi
    # SOC decadimento 70% di chi ha abbandonato l'anno precedente
    soc_perso = (abb_regime_reale * ((i-1)/n_step)) * (1 - attivi)
    soc_residuo = (soc_residuo * 0.3) + soc_perso
    history_abb.append(abb_attivi + soc_residuo)

# --- INTERFACCIA KPI ---
abb_f = history_abb[-1]
gap_f = max(0, target_ton_regime - abb_f)

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale 2030", f"{((BASELINE_TOT - abb_f)/VOL_TOT_TON)*1000:.1f} kg/t", f"Target: {(BASELINE_TOT*(1-target_decarb/100)/VOL_TOT_TON)*1000:.1f}")
c2.metric("Superficie Totale", f"{int(sum(ettari_regime.values()))} ha", f"Saturazione: {(sum(ettari_regime.values())/ETTARI_FILIERA)*100:.1f}%")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}")
c4.metric("Gap al Target", f"{int(gap_f)} tCO2", delta="OK" if gap_f <= 10 else "MISS", delta_color="inverse")

st.markdown("---")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📅 Analisi della Traiettoria (Baseline vs Target)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni_sim, y=[BASELINE_TOT - h for h in history_abb], name="Emissioni Nette", line=dict(color='black', width=4), mode='lines+markers'))
    fig.add_trace(go.Scatter(x=anni_sim, y=[BASELINE_TOT*(1-target_decarb/100)]*len(anni_sim), name="Soglia Target", line=dict(dash='dash', color='blue')))
    fig.update_layout(yaxis_title="tCO2e", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("📊 Portfolio Mix (MCDA)")
    labels_p = [k for k,v in ettari_regime.items() if v > 0]
    values_p = [v for v in ettari_regime.values() if v > 0]
    fig_pie = go.Figure(data=[go.Pie(labels=labels_p, values=values_p, hole=.5)])
    fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

# --- DETTAGLIO OPERATIVO ---
st.subheader("🚀 Piano di Ingaggio Agricoltori")
cols = st.columns(len(labels_p))
for idx, p in enumerate(labels_p):
    with cols[idx]:
        st.info(f"**{p}**\n\n{int(ettari_regime[p])} ha\n\n*Difficoltà: {int(diff_configs[p])}/5*")

if gap_f > 10 and budget_restante > 1000:
    st.error(f"⚠️ **Attenzione**: Nonostante il budget residuo, non raggiungiamo il target perché l'avversione alla complessità (α={alpha}) impedisce di usare pratiche più potenti o perché abbiamo esaurito i 10.000 ettari. Prova a diminuire α o aumentare gli ettari totali.")
