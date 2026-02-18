import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Final Governance", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione Probabilistica e Surface Minimization")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("🕹️ Pannello di Controllo")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000, step=50000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.header("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (Permanenza %)", 5, 40, 20)
churn_rate = st.sidebar.slider("Churn Rate Annuo (%)", 0, 20, 10)

# --- DATABASE PRATICHE FISSO ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'costo': 250, 'diff': 3, 'res': 2},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.0, 'costo': 200, 'diff': 1, 'res': 3},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3, 'res': 5},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 4, 'res': 2},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9, 'costo': 450, 'diff': 3, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 5}
}

# --- SLIDER BOX PER MODIFICHE LAST-MINUTE ---
st.sidebar.header("⚙️ Regolazione Incentivi (€/ha)")
conf_pratiche = {}
for p, v in pratiche_base.items():
    with st.sidebar.expander(f"Parametri {p}"):
        costo_custom = st.number_input(f"Eur/ha {p}", 0, 1500, v['costo'], key=f"c_{p}")
        # Diff e Res restano visualizzati ma bloccati come da istruzioni
        st.caption(f"Difficoltà: {v['diff']} | Resa (Res): {v['res']}")
        conf_pratiche[p] = {**v, 'costo': costo_custom}

df_p = pd.DataFrame(conf_pratiche).T

# --- CALCOLI BASE ---
ETTARI_FILIERA = 10000
VOL_TOT_TON = 800000
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)
target_ton_tot = BASELINE_TOT * (target_decarb / 100)

# Impatto Netto depurato dal rischio
df_p['Imp_Netto'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
# Score MCDA: (Impatto * Res) / (Costo * Difficoltà)
df_p['Score'] = (df_p['Imp_Netto'] * df_p['res']) / (df_p['costo'] * df_p['diff'])

# --- MOTORE DI ALLOCAZIONE IBRIDO (PROBABILISTICO + ROI) ---
ettari_allocati = {p: 0.0 for p in df_p.index}

# 1. Adozione Basale Probabilistica (per pratiche con diff < 3)
# Simula il fatto che qualcuno le prova a prescindere
pratiche_facili = df_p[df_p['diff'] < 3].index
superficie_probabilistica = ETTARI_FILIERA * 0.10 # 10% della superficie totale è "naturalmente" incline
for p in pratiche_facili:
    ettari_allocati[p] = superficie_probabilistica / len(pratiche_facili)

# 2. Allocazione Budget Residuo basata sullo Score
budget_utilizzato = sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())
budget_rimanente = budget_max - budget_utilizzato

if budget_rimanente > 0:
    df_sorted = df_p.sort_values(by='Score', ascending=False)
    for nome, row in df_sorted.iterrows():
        abb_attuale = sum(ha * df_p.at[p, 'Imp_Netto'] for p, ha in ettari_allocati.items())
        if abb_attuale >= target_ton_tot or budget_rimanente <= 0:
            break
        
        ha_mancanti = (target_ton_tot - abb_attuale) / row['Imp_Netto']
        ha_finanziabili = budget_rimanente / row['costo']
        ha_fisici_liberi = ETTARI_FILIERA - sum(ettari_allocati.values())
        
        da_aggiungere = max(0, min(ha_mancanti, ha_finanziabili, ha_fisici_liberi))
        ettari_allocati[nome] += da_aggiungere
        budget_rimanente -= da_aggiungere * row['costo']

# --- KPI ---
abb_finale = sum(ha * df_p.at[p, 'Imp_Netto'] for p, ha in ettari_allocati.items())
ef_target = ((BASELINE_TOT - abb_finale) / VOL_TOT_TON) * 1000

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale Target", f"{ef_target:.1f} kg/t", f"Base: {(BASELINE_TOT/VOL_TOT_TON)*1000:.1f}")
c2.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha", f"{(sum(ettari_allocati.values())/ETTARI_FILIERA)*100:.1f}% filiera")
c3.metric("Budget Utilizzato", f"€ {int(budget_max - budget_rimanente):,}")
c4.metric("Gap CO2", f"{int(max(0, target_ton_tot - abb_finale))} t")

st.markdown("---")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📅 Proiezione Temporale (Carry-over & Churn)")
    anni = np.arange(2025, orizzonte_anno + 1)
    traiettoria = []
    for i, anno in enumerate(anni):
        progressione = min(1.0, (i + 1) / (len(anni)-1 if len(anni)>1 else 1))
        # Applichiamo il churn cumulativo
        efficacia = (abb_finale * progressione) * (1 - (churn_rate/100))**i
        traiettoria.append(BASELINE_TOT - efficacia)
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria, name="Emissioni Nette", line=dict(color='black', width=4)))
    fig_line.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT - target_ton_tot]*len(anni), name="Target", line=dict(dash='dot', color='red')))
    st.plotly_chart(fig_line, use_container_width=True)

with col_r:
    st.subheader("📊 Portfolio Mix (Ettari)")
    labels = [p for p, ha in ettari_allocati.items() if ha > 0.1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0.1]
    if values:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)
    else:
        st.warning("Nessun dato da visualizzare.")

# --- WATERFALL ---
st.subheader("📉 Analisi Variazione a Regime")
contributo_input = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
contributo_soil = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    x = ["Baseline", "Variazione Input", "Rimozione SOC", "Emissione Netta"],
    y = [BASELINE_TOT, contributo_input, -contributo_soil, 0],
    measure = ["absolute", "relative", "relative", "total"]
))
st.plotly_chart(fig_wf, use_container_width=True)

st.write("### 🚜 Dettaglio Operativo")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ettari_allocati.items() if ha > 0}, orient='index', columns=['Superficie']))
