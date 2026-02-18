import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Standardized MCDA", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione Multicriterio Bilanciata (Standardizzata 0-1)")
st.markdown("---")

# --- SIDEBAR: PESI STRATEGICI ---
st.sidebar.header("⚖️ Pesi Decisionali (Tot: 1.0)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.0, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Costo (€/ha)", 0.0, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità (Difficoltà)", 0.0, 1.0, 0.1)
# Calcolo peso residuo per coerenza o avviso
st.sidebar.caption(f"Somma pesi attuale: {round(w_imp + w_cost + w_diff, 2)}")

st.sidebar.header("🎯 Target & Rischio")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo (€)", value=1000000)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Probabilistica Minima (%)", 0, 20, 10, help="Quota di ettari comunque assegnata alle pratiche facili")

# --- DATABASE FISSO ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'costo': 250, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.0, 'costo': 200, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 4},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9, 'costo': 450, 'diff': 3},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5}
}

df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
BASELINE_TOT = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- STANDARDIZZAZIONE 0-1 ---
# Impatto: Più alto meglio è
df_p['Imp_Val'] = (-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100)
df_p['S_Imp'] = (df_p['Imp_Val'] - df_p['Imp_Val'].min()) / (df_p['Imp_Val'].max() - df_p['Imp_Val'].min())

# Costo: Più basso meglio è (invertiamo: 1 è economico, 0 è costoso)
df_p['S_Cost'] = (df_p['costo'].max() - df_p['costo']) / (df_p['costo'].max() - df_p['costo'].min())

# Difficoltà: Più bassa meglio è (invertiamo: 1 è facile, 0 è difficile)
df_p['S_Diff'] = (df_p['diff'].max() - df_p['diff']) / (df_p['diff'].max() - df_p['diff'].min())

# --- CALCOLO SCORE FINALE ---
df_p['Score'] = (df_p['S_Imp'] * w_imp) + (df_p['S_Cost'] * w_cost) + (df_p['S_Diff'] * w_diff)

# --- ALLOCAZIONE ---
ettari_allocati = {p: 0.0 for p in df_p.index}

# 1. Quota Probabilistica Minima (per pratiche con diff < 3)
pratiche_facili = df_p[df_p['diff'] < 3].index
ha_min_base = (ETTARI_FILIERA * (prob_minima/100)) / len(pratiche_facili)
for p in pratiche_facili:
    ettari_allocati[p] = ha_min_base

# 2. Allocazione Budget su Score
target_ton = BASELINE_TOT * (target_decarb/100)
budget_residuo = budget_max - sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())
df_sorted = df_p.sort_values(by='Score', ascending=False)

for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    if abb_attuale >= target_ton or budget_residuo <= 0: break
    
    ha_mancanti = (target_ton - abb_attuale) / row['Imp_Val']
    ha_finanziabili = budget_residuo / row['costo']
    ha_fisici_liberi = ETTARI_FILIERA - sum(ettari_allocati.values())
    
    da_aggiungere = max(0, min(ha_mancanti, ha_finanziabili, ha_fisici_liberi))
    ettari_allocati[nome] += da_aggiungere
    budget_residuo -= da_aggiungere * row['costo']

# --- VISUALIZZAZIONE KPI ---
c1, c2, c3, c4 = st.columns(4)
abb_tot = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
c1.metric("Superficie", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("CO2 Abbattuta", f"{int(abb_tot)} t")
c3.metric("Budget Utilizzato", f"€ {int(budget_max - budget_residuo):,}")
c4.metric("Gap al Target", f"{int(max(0, target_ton - abb_tot))} t")

st.markdown("---")

# --- GRAFICI ---
col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("📊 Mix Portafoglio (Ettari)")
    labels = [p for p, ha in ettari_allocati.items() if ha > 1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 1]
    st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)

with col_r:
    st.subheader("📈 Ranking Standardizzato (0-1)")
    # Grafico a barre orizzontali per vedere come i pesi influenzano lo score
    fig_bar = go.Figure(go.Bar(x=df_p['Score'], y=df_p.index, orientation='h', marker_color='lightseagreen'))
    fig_bar.update_layout(xaxis=dict(range=[0, 1]))
    st.plotly_chart(fig_bar, use_container_width=True)

st.write("### 📋 Analisi dei Punteggi Standardizzati")
st.dataframe(df_p[['Imp_Val', 'S_Imp', 'S_Cost', 'S_Diff', 'Score']].sort_values(by='Score', ascending=False).style.background_gradient(cmap='Greens'))
