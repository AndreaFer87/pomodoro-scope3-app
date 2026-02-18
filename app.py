import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Agri-E-MRV | Balanced MCDA", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione Bilanciata: Impatto vs Difficoltà Operativa")
st.markdown("---")

# --- SIDEBAR ---
st.sidebar.header("⚖️ Strategia MCDA")
alpha = st.sidebar.slider(
    "α - Avversione alla Complessità", 
    0.5, 4.0, 1.5, 0.1,
    help="Bilancia l'impatto tecnico con la facilità di esecuzione."
)

st.sidebar.header("🕹️ Obiettivi")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max_annuo = st.sidebar.number_input("Budget Annuo Massimo (€)", value=1000000)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 12)

# --- DATABASE PRATICHE ---
# Nota: Imp_Netto_Ha è calcolato come (Sequestro + Emissioni Evitate + 0.5 bonus) * (1-Buffer)
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
df_p['Imp_Netto_Ha'] = ((-df_p['d_emiss'] + df_p['d_carb'] + 0.5) * (1 - safety_buffer/100)).round(2)

# Score MCDA: Impatto / (Costo * Difficoltà^Alpha)
# Moltiplichiamo per 1000 per leggibilità
df_p['AI_Score'] = (df_p['Imp_Netto_Ha'] / (df_p['costo'] * (df_p['diff']**alpha))) * 1000

# --- MOTORE DI OTTIMIZZAZIONE ---
ETTARI_FILIERA = 10000
BASELINE_TOT = 40000 
target_ton = BASELINE_TOT * (target_decarb / 100)
budget_restante = budget_max_annuo
ettari_regime = {p: 0.0 for p in df_p.index}

df_sorted = df_p.sort_values(by='AI_Score', ascending=False)

for nome, row in df_sorted.iterrows():
    abb_attuale = sum(ettari_regime[pr] * df_p.at[pr, 'Imp_Netto_Ha'] for pr in df_p.index)
    if abb_attuale >= target_ton or budget_restante <= 0: break
    
    # Cap Operativo: simuliamo che più la pratica è difficile, meno agricoltori 'pionieri' troviamo
    cap_operativo = ETTARI_FILIERA / (row['diff']**(alpha/2))
    
    ha_mancanti = (target_ton - abb_attuale) / row['Imp_Netto_Ha']
    ha_finanziabili = budget_restante / row['costo']
    ha_fisici_liberi = ETTARI_FILIERA - sum(ettari_regime.values())
    
    ha_da_aggiungere = max(0, min(ha_mancanti, ha_finanziabili, cap_operativo, ha_fisici_liberi))
    
    ettari_regime[nome] += ha_da_aggiungere
    budget_restante -= ha_da_aggiungere * row['costo']

# --- VISUALIZZAZIONE ---
st.write(f"### 📊 Risultato Ottimizzazione (Alpha = {alpha})")
c1, c2, c3 = st.columns(3)
c1.metric("Ettari Totali", f"{int(sum(ettari_regime.values()))} ha")
c2.metric("CO2 Abbattuta", f"{int(sum(ettari_regime[p]*df_p.at[p, 'Imp_Netto_Ha'] for p in df_p.index))} t")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}")

col_left, col_right = st.columns([1, 1])
with col_left:
    labels = [k for k,v in ettari_regime.items() if v > 0]
    values = [v for v in ettari_regime.values() if v > 0]
    if values:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)]), use_container_width=True)
with col_right:
    # Mostriamo la classifica dinamica
    st.write("**Ranking MCDA (Priorità AI)**")
    st.dataframe(df_p[['AI_Score', 'Imp_Netto_Ha', 'costo', 'diff']].sort_values(by='AI_Score', ascending=False))

st.success("💡 **Nota:** Se una pratica difficile ha un Imp_Netto_Ha molto alto, vedrai che resta alta in classifica anche con Alpha medio, perché il suo 'valore' compensa la 'fatica'.")
