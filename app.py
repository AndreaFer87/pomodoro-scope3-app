import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Agri-E-MRV | Reactive MCDA", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Decision Support System: Analisi MCDA Dinamica")
st.markdown("---")

# --- SIDEBAR: STRATEGIA ---
st.sidebar.header("⚖️ Strategia Operativa (MCDA)")
alpha = st.sidebar.slider(
    "α - Avversione alla Complessità", 
    0.5, 5.0, 1.5, 0.1,
    help="Determina quanto la difficoltà tecnica penalizza lo score. Più è alto, più l'AI scappa dalle pratiche difficili."
)

st.sidebar.header("🕹️ Obiettivi e Rischio")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Massimo (€)", value=1000000)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 15)

# --- DATABASE PRATICHE AGGIORNATO ---
pratiche = {
    'Cover Crops':          {'costo': 250, 'diff': 2.0, 'd_emiss': 0.2,  'd_carb': 1.1},
    'Interramento':         {'costo': 200, 'diff': 1.5, 'd_emiss': 0.3,  'd_carb': 2.0},
    'Minima Lav.':          {'costo': 250, 'diff': 1.0, 'd_emiss': -0.7, 'd_carb': 0.36},
    'C.C. + Interramento':  {'costo': 450, 'diff': 4.0, 'd_emiss': 0.5,  'd_carb': 3.0},
    'C.C. + Minima Lav.':   {'costo': 350, 'diff': 3.0, 'd_emiss': -0.5, 'd_carb': 1.46},
    'Int. + Minima Lav.':   {'costo': 450, 'diff': 3.5, 'd_emiss': -0.4, 'd_carb': 2.7},
    'Tripletta':            {'costo': 800, 'diff': 5.0, 'd_emiss': 0.2,  'd_carb': 3.5}
}

df_p = pd.DataFrame(pratiche).T

# --- CALCOLO INDICATORI ---
# Imp_Netto_Ha: Quanta CO2 togliamo davvero per ettaro
df_p['Imp_Netto_Ha'] = ((-df_p['d_emiss'] + df_p['d_carb'] + 0.5) * (1 - safety_buffer/100)).round(2)

# AI_Score: Il ranking MCDA influenzato da alpha
# Più Alpha è alto, più il denominatore (difficoltà^alpha) diventa enorme, affossando le pratiche difficili.
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo'] * (df_p['diff']**alpha))) * 1000

# --- MOTORE DI OTTIMIZZAZIONE ---
ETTARI_FILIERA = 10000
BASELINE_TOT = 40000 # (50kg/t * 800k ton / 1000)
target_ton = BASELINE_TOT * (target_decarb / 100)

budget_restante = budget_max_annuo
ettari_regime = {p: 0.0 for p in df_p.index}

# Ordiniamo per il nuovo score dinamico
df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[pr] * df_p.at[pr, 'Imp_Netto_Ha'] for pr in df_p.index)
    if abb_attuale >= target_ton or budget_restante <= 0: break
    
    # Cap dinamico: se la pratica è difficile e alpha è alto, troviamo pochissimi ettari disponibili
    cap_operativo = ETTARI_FILIERA / (row['diff']**(alpha/1.5))
    
    ha_mancanti = (target_ton - abb_attuale) / row['Imp_Netto_Ha']
    ha_finanziabili = budget_restante / row['costo']
    ha_fisici_rimanenti = ETTARI_FILIERA - sum(ettari_regime.values())
    
    ha_da_aggiungere = max(0, min(ha_mancanti, ha_finanziabili, cap_operativo, ha_fisici_rimanenti))
    
    ettari_regime[nome] += ha_da_aggiungere
    budget_restante -= ha_da_aggiungere * row['costo']

# --- INTERFACCIA ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Superficie Totale", f"{int(sum(ettari_regime.values()))} ha")
c2.metric("Abbattimento", f"{int(sum(ettari_regime[p]*df_p.at[p, 'Imp_Netto_Ha'] for p in df_p.index))} tCO2")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}")
c4.metric("Alpha Attuale", f"{alpha:.1f}")

st.markdown("---")
col_l, col_r = st.columns([1, 1])

with col_l:
    st.subheader("📊 Portfolio Mix Dinamico")
    labels = [k for k,v in ettari_regime.items() if v > 0]
    values = [v for v in ettari_regime.values() if v > 0]
    if values:
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nessuna pratica selezionata con questi parametri.")

with col_r:
    st.subheader("📑 Tabella Analisi MCDA")
    # Mostriamo come cambia lo Score
    st.dataframe(df_p[['AI_Score', 'Imp_Netto_Ha', 'costo', 'diff']].sort_values(by='AI_Score', ascending=False))

st.info("💡 **Consiglio per vedere il grafico muoversi:** Imposta Alpha a 0.5 e guarda come entrano le pratiche complesse. Poi portalo a 4.0 e vedrai il mix spostarsi drasticamente verso la 'Minima Lavorazione' (la più facile).")
