import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="PlanAI | Agri-E-MRV", layout="wide")

# --- DATABASE PRATICHE ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.20, 'd_carb': 1.10, 'costo': 300, 'diff': 3, 'res': 3},
    'Interramento':         {'d_emiss': 0.50, 'd_carb': 2.20, 'costo': 200, 'diff': 1, 'res': 5},
    'Minima Lav.':          {'d_emiss': -0.50, 'd_carb': 0.36, 'costo': 250, 'diff': 1, 'res': 4},
    'C.C. + Interramento':  {'d_emiss': 0.50, 'd_carb': 3.30, 'costo': 500, 'diff': 4, 'res': 4},
    'C.C. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 1.46, 'costo': 550, 'diff': 5, 'res': 5},
    'Int. + Minima Lav.':   {'d_emiss': -0.20, 'd_carb': 2.90, 'costo': 450, 'diff': 5, 'res': 4},
    'Tripletta':            {'d_emiss': 0.20, 'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 3}
}
df_p = pd.DataFrame(pratiche).T

# --- SIDEBAR ---
st.sidebar.header("🕹️ Pannello di Controllo")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000, step=50000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte", options=[2026, 2027, 2028, 2029, 2030])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20, help="Accantonamento cautelativo di crediti")
churn_rate = st.sidebar.slider("Tasso di Abbandono (Churn %)", 0, 20, 5, help="Rischio di uscita agricoltori dal programma")

# --- MOTORE DI OTTIMIZZAZIONE AI ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
BASELINE_NETTA_2025 = ETTARI_FILIERA * 4.5 
target_ton_tot = BASELINE_NETTA_2025 * (target_decarb / 100)

# 1. Calcolo Impatto Netto e Costo/Ton Reale (Scontato per Buffer e Churn)
df_p['Imp_Netto'] = (df_p['d_carb'] - df_p['d_emiss']) * (1 - safety_buffer/100) * (1 - churn_rate/100)
df_p['Costo_Effettivo_Ha'] = df_p['costo'] * 0.75 
df_p['Eur_Ton'] = df_p['Costo_Effettivo_Ha'] / df_p['Imp_Netto']

# 2. Logica AI: Ordine per efficienza economica e stabilità rese
df_p['AI_Score'] = (1 / df_p['Eur_Ton']) * (df_p['res'] / 5)
df_p = df_p.sort_values(by='AI_Score', ascending=False)

# 3. Allocazione Ettari vincolata al BUDGET
budget_residuo = budget_max
ett
