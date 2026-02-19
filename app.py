import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Scope 3 Journey", layout="wide")

# CSS BLINDATO: Forziamo i font e i colori per evitare ridimensionamenti
st.markdown("""
    <style>
    .main-title {
        font-size: 48px !important;
        font-weight: bold !important;
        color: #2E7D32 !important;
        margin-bottom: 0px !important;
        display: block;
    }
    .sub-title {
        font-size: 22px !important;
        color: #555555 !important;
        margin-bottom: 30px !important;
        display: block;
    }
    [data-testid="stMetricLabel"] {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #1E1E1E !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 40px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TITOLI ---
st.markdown('<p class="main-title">🌱 Plan & Govern your Scope 3 journey</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Executive Strategy Tool - optimize your Reg Ag investment by maximizing climatic ROI</p>', unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Strategici (WHM)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.01, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.01, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.01, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)
anno_target = st.sidebar.select_slider("Orizzonte Temporale Target", options=[2026, 2027, 2028, 2029, 2030, 2035], value=2030)

st.sidebar.header("⏳ Dinamiche Temporali")
churn_rate = st.sidebar.slider("Tasso abbandono incentivi annuo (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 40) 
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 15)

# --- DATA E LOGICA MCDA ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 250, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 200, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 70
