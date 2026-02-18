import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# --- DATABASE PRATICHE ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.20, 'd_carb': 1.10, 'costo': 300, 'res': 3},
    'Interramento':         {'d_emiss': 0.50, 'd_carb': 2.20, 'costo': 200, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.50, 'd_carb': 0.36, 'costo': 250, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.50, 'd_carb': 3.30, 'costo': 500, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 1.46, 'costo': 550, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 2.90, 'costo': 450, 'res': 4},
    'Tripletta':            {'d_emiss': 0.20, 'd_carb': 3.67, 'costo': 800, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T

# --- SIDEBAR ---
st.sidebar.header("🕹️ Pannello di Controllo")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000, step=50000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 10, 100, 75)
orizzonte_val = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030])
n_anni = orizzonte_val - 2025

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5)

# --- MOTORE DI OTTIMIZZAZIONE (Logica IA) ---
# Spiegazione: L'algoritmo non sceglie a caso, ma calcola l'efficienza marginale 
# di ogni pratica "scontata" per i rischi di Churn e Buffer.

VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_NETTA_2025 = ETTARI_FILIERA * 4.5 

# 1. Calcolo dell'Impatto Reale (Netto)
# Scontiamo l'efficacia della pratica per il Churn e il Buffer Pool richiesto
df_p['Imp_Netto'] = (df_p['d_carb'] - df_p['d_emiss']) * (1 - safety_buffer/100) * (1 - churn_rate/100)

# 2. Calcolo del Costo per l'Azienda (€/ha)
df_p['Costo_Azienda'] = df_p['costo'] * (incentivo_percent / 100)

# 3. Metrica di Efficienza (La bussola dell'IA)
# L'IA preferisce Eur/Ton bassi e Stabilità Rese (res) alta
df_p['Eur_Ton'] = df_p['Costo_Azienda'] / df_p['Imp_Netto']
df_p['Score_IA'] = df_p['Eur_Ton'] / (df_p['res'] / 5) # Più basso è, meglio è

# 4. ALGORITMO DI ALLOCAZIONE (Greedy Optimizer)
df_sorted = df_p.sort_values('Score_IA') # L'IA mette in fila le pratiche migliori
budget_restante = budget_annuo
ettari_assegnati = {}
abbattimento_totale = 0

for nome, row in df_sorted.iterrows():
    if budget_restante <= 0:
        break
    
    # Quanti ettari potrei comprare con il budget rimasto?
    max_ha_budget = budget_restante / row['Costo_Azienda']
    # Quanti ettari mancano per arrivare al limite della filiera?
    max_ha_filiera = ETTARI_FILIERA - sum(ettari_assegnati.values())
    
    # Scelta dell'IA: il minimo tra budget, disponibilità filiera e un limite di adozione (es. 40%)
    ha_finali = min(max_ha_budget, max_ha_filiera, ETTARI_FILIERA * 0.4)
    
    if ha_finali > 1:
        ettari_assegnati[nome] = ha_finali
        budget_restante -= ha_finali * row['Costo_Azienda']
        abbattimento_totale += ha_finali * row['Imp_Netto']

ettari_tot_prog = sum(ettari_assegnati.values())
investimento_5_anni = (budget_annuo - budget_restante) * n_anni

# --- KPI BOX ---
c1, c2, c3, c4 = st.columns(4)
eur_ton_final = (budget_annuo - budget_restante) / max(1, abbattimento_totale)
roi_climatico = abbattimento_totale / ((budget_annuo - budget_restante) / 1000)

c1.metric("Eur/Ton Abbattimento", f"{eur_ton_final:.2f} €/t")
c2.metric("Ettari Programma", f"{int(ettari_tot_prog)} ha", f"{int(ettari_tot_prog/ETTARI_FILIERA*100)}% Filiera")
c3.metric("ROI Climatico", f"{roi_climatico:.2f} t/k€")
c4.metric("Investimento Totale", f"€ {int(investimento_5_anni):,}", f"Orizzonte {n_anni} anni")

if budget_restante > 100:
    st.warning(f"⚠️ Budget non completamente utilizzato: €{int(budget_restante):,} residui. La filiera è satura o le pratiche sono troppo costose.")

st.markdown("---")

# --- GRAFICI ---
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("📅 Traiettoria Emissioni Nette")
    anni = np.arange(2025, orizzonte_val + 1)
    nette = [BASELINE_NETTA_2025 - (abbattimento_totale * (i/(len(anni)-1))) for i in range(len(anni))]
    target_line = [BASELINE_NETTA_2025 * (1 - target_decarb/100)] * len(anni)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anni, y=nette, name="Emissioni Nette (Simulate)", line=dict(color="black", width=4)))
    fig.add_trace(go.Scatter(x=anni, y=target_line, name="Target CSRD", line=dict(color="blue", dash="dash")))
    fig.update_layout(yaxis_title="tCO2e")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Portfolio Pratiche (Scelta IA)")
    if ettari_assegnati:
        fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_assegnati.keys()), values=list(ettari_assegnati.values()), hole=.5)])
        st.plotly_chart(fig_pie, use_container_width=True)

# --- SPIEGAZIONE MODELLO ---
with st.expander("🔬 Logica del Modello IA (Spiegazione per gli studenti)"):
    st.write(f"""
    L'algoritmo di ottimizzazione segue questi passaggi:
    1. **Preprocessing:** Calcola l'impatto netto di ogni pratica 'scontandolo' per il **Safety Buffer** e il **Churn Rate**. Se una pratica sequestra 3 tonnellate ma hai il 20% di Churn, l'IA ne calcola solo 2.4.
    2. **Ranking (Efficiency Scoring):** Calcola il rapporto €/Ton. Successivamente divide questo valore per il coefficiente di **Stabilità Rese**. Una pratica economica ma instabile riceve un punteggio peggiore di una pratica mediamente costosa ma molto stabile.
    3. **Allocazione Greedy:** Inizia ad allocare ettari partendo dalla pratica con lo 'Score IA' migliore.
    4. **Saturazione Vincoli:** Smette di allocare quando finisce il budget annuo o quando ha coperto tutti i 10.000 ettari della filiera.
    """)
