import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Agri-E-MRV | Real-World Mix", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Simulazione Realistica: Distribuzione Adattiva e Attrattività Resa")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("🕹️ Governance")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Churn Rate (%)", 0, 20, 10)

# --- DATABASE PRATICHE CON NUOVI RES ---
# Aggiornati come da tua richiesta
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'costo': 250, 'diff': 2, 'res': 2},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.0, 'costo': 200, 'diff': 1, 'res': 3},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 1, 'res': 4}, # Res di default
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 4, 'res': 5},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 5, 'res': 2},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9, 'costo': 450, 'diff': 5, 'res': 4},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 5}
}

df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
VOL_TOT_TON = 800000
BASELINE_TOT = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- CALCOLO SCORE MCDA ---
df_p['Imp_Netto'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
# Score: premia impatto e resa, penalizza costo e difficoltà
df_p['Score'] = (df_p['Imp_Netto'] * df_p['res']) / (df_p['costo'] * df_p['diff'])

# --- MOTORE DI ALLOCAZIONE PROBABILISTICA (Non-Saturante) ---
# Invece di riempire una alla volta, dividiamo il budget in base al peso dello score
# Le pratiche con diff < 3 hanno un "pavimento" di adozione del 5% della superficie
ettari_allocati = {p: 0.0 for p in df_p.index}

# 1. Assegnazione basale per pratiche "semplici" (diff < 3)
superficie_test = ETTARI_FILIERA * 0.15 # Il 15% della filiera prova pratiche facili a prescindere
pratiche_facili = df_p[df_p['diff'] < 3].index
for p in pratiche_facili:
    ettari_allocati[p] = superficie_test / len(pratiche_facili)

# 2. Distribuzione del budget rimanente in base allo score
budget_speso_test = sum(ettari_allocati[p] * df_p.at[p, 'costo'] for p in df_p.index)
budget_rimanente = budget_max - budget_speso_test

if budget_rimanente > 0:
    # Calcoliamo i pesi (normalizziamo gli score)
    total_score = df_p['Score'].sum()
    df_p['Peso_Budget'] = df_p['Score'] / total_score
    
    for p, row in df_p.iterrows():
        budget_per_pratica = budget_rimanente * row['Peso_Budget']
        ha_aggiuntivi = budget_per_pratica / row['costo']
        ettari_allocati[p] += ha_aggiuntivi

# Limite fisico degli ettari
tot_ha = sum(ettari_allocati.values())
if tot_ha > ETTARI_FILIERA:
    ratio = ETTARI_FILIERA / tot_ha
    for p in ettari_allocati:
        ettari_allocati[p] *= ratio

# --- VISUALIZZAZIONE ---
abb_effettivo = sum(ha * df_p.at[p, 'Imp_Netto'] for p, ha in ettari_allocati.items())
target_ton_tot = BASELINE_TOT * (target_decarb / 100)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Superficie", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("Abbattimento", f"{int(abb_effettivo)} tCO2")
c3.metric("Budget Speso", f"€ {int(sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())):,}")
c4.metric("Gap Target", f"{int(max(0, target_ton_tot - abb_effettivo))} t")

st.markdown("---")
l, r = st.columns([1.5, 1])

with l:
    st.subheader("📊 Portfolio Mix Realistico")
    # Mostra tutte le pratiche, anche quelle con pochi ettari
    labels = [p for p, ha in ettari_allocati.items() if ha > 0.1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0.1]
    st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)

with r:
    st.subheader("🎯 Analisi di Attrattività (MCDA)")
    # Tabella semplificata per mostrare perché il mix è così
    st.dataframe(df_p[['Imp_Netto', 'res', 'diff', 'Score']].sort_values(by='Score', ascending=False))

st.info("💡 **Cosa è cambiato:** Ora anche la Tripletta e le altre pratiche difficili compaiono nel mix perché hanno 'Res 5', che compensa la difficoltà. Le pratiche facili (Cover/Interramento) sono sempre presenti come base di adozione 'naturale'.")
