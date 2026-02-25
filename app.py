import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scope 3 FLAG dashboard", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 48px !important; font-weight: bold !important; color: #2E7D32 !important; }
    .kpi-box {
        text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 12px; 
        border: 1px solid #ddd; height: 160px; display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-value { margin:0; font-size: 24px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🚀 Scope 3 FLAG Scalability Plan</p>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
# Aumentato il range per rendere i pesi più "estremi"
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.0, 10.0, 3.3)
w_cost = st.sidebar.slider("Peso Efficienza Costo (Risparmio)", 0.0, 10.0, 3.3)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.0, 10.0, 3.3)

st.sidebar.header("💰 Strategia di Investimento")
budget_iniziale = st.sidebar.number_input("Budget Anno 1 (€)", value=0, step=50000)
crescita_budget_pct = st.sidebar.slider("Aumento % Annuo Budget", 0, 100, 20)

st.sidebar.header("🎯 Obiettivi Climatici")
target_decarb_req = st.sidebar.slider("Target Richiesto 2030 (%)", 10, 50, 27)

st.sidebar.header("⏳ Parametri di Tenuta")
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 3) 
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 10)

# --- DATABASE PRATICHE ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 225, 'diff': 2},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 300, 'diff': 1},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 525, 'diff': 3}
}
df_p = pd.DataFrame(pratiche_base).T
ETTARI_FILIERA = 10000
RESA_TOM_HA = 80
PROD_TOT_TON = ETTARI_FILIERA * RESA_TOM_HA
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.5 + LOSS_SOC_BASE_HA)

# --- MOTORE DI SIMULAZIONE REATTIVO ---
def run_scaling_sim(wi, wc, wd):
    anni = [2026, 2027, 2028, 2029, 2030]
    results_ha = []
    budget_per_anno = []
    traiettoria = [BASELINE_TOT_ANNUA]
    
    d = df_p.copy()
    # 1. Calcolo Impatto Netto (più alto è meglio)
    d['Imp_Val'] = ((-d['d_emiss'] + d['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
    
    # 2. Normalizzazione Pura (0-1) per rendere i pesi efficaci
    d['norm_Imp'] = (d['Imp_Val'] - d['Imp_Val'].min()) / (d['Imp_Val'].max() - d['Imp_Val'].min() + 0.001)
    d['norm_Cost'] = (d['costo'].max() - d['costo']) / (d['costo'].max() - d['costo'].min() + 0.001)
    d['norm_Diff'] = (d['diff'].max() - d['diff']) / (d['diff'].max() - d['diff'].min() + 0.001)
    
    # 3. Calcolo Score Finale Pesato
    d['Score'] = (d['norm_Imp'] * wi) + (d['norm_Cost'] * wc) + (d['norm_Diff'] * wd)
    
    # Ordine di priorità basato sullo score
    priority_list = d.sort_values(by='Score', ascending=False).index.tolist()
    
    stock_acc = 0
    for i, anno in enumerate(anni):
        budget_t = budget_iniziale * ((1 + crescita_budget_pct/100) ** i)
        budget_per_anno.append(budget_t)
        
        ha_alloc = {p: 0.0 for p in d.index}
        
        # Adozione Spontanea (solo diff <= 2)
        pratiche_spontanee = d[d['diff'] <= 2].index
        for p in pratiche_spontanee:
            ha_alloc[p] = (ETTARI_FILIERA * (prob_minima/100)) / len(pratiche_spontanee)
        
        costo_spontanea = sum(ha_alloc[p] * d.at[p, 'costo'] for p in ha_alloc)
        budget_residuo = max(0, budget_t - costo_spontanea)
        
        # Allocazione Budget Extra seguendo il ranking MCDA
        for p_nome in priority_list:
            if budget_residuo <= 0: break
            # Limite: non più dell'80% della filiera su una singola pratica per rotazione
            max_ha_pratica = ETTARI_FILIERA * 0.8 
            ha_possibili = max(0, max_ha_pratica - ha_alloc[p_nome])
            da_comprare = min(budget_residuo / d.at[p_nome, 'costo'], ha_possibili)
            
            ha_alloc[p_nome] += da_comprare
            budget_residuo -= (da_comprare * d.at[p_nome, 'costo'])
            
        beneficio_t = sum(ha_alloc[p] * d.at[p, 'Imp_Val'] for p in ha_alloc)
        stock_acc = (stock_acc * 0.8) + beneficio_t # Semplificato per reattività
        traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)
        results_ha.append(ha_alloc.copy())
        
    return anni, traiettoria, results_ha, budget_per_anno

anni_sim, emissioni_sim, ettari_per_anno, budgets = run_scaling_sim(w_imp, w_cost, w_diff)

# --- KPI E GRAFICI (Uguali a prima ma con dati reattivi) ---
impronta_iniziale = BASELINE_TOT_ANNUA * 1000 / PROD_TOT_TON
impronta_finale = emissioni_sim[-1] * 1000 / PROD_TOT_TON
riduzione_effettiva = (1 - (emissioni_sim[-1] / BASELINE_TOT_ANNUA)) * 100

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi-box"><p>Impronta CO2</p><p class="kpi-value">{impronta_iniziale:.2f}→{impronta_finale:.2f}</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-box"><p>Riduzione %</p><p class="kpi-value" style="color:green;">-{riduzione_effettiva:.1f}%</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-box"><p>Investimento 5Y</p><p class="kpi-value">€ {int(sum(budgets)):,}</p></div>', unsafe_allow_html=True)
gap = emissioni_sim[-1] - (BASELINE_TOT_ANNUA * (1 - target_decarb_req/100))
c4.markdown(f'<div class="kpi-box"><p>Gap Target</p><p class="kpi-value" style="color:red;">{int(gap)} t</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("🚜 Mix Pratiche (Ettari)")
    df_bar = pd.DataFrame(ettari_per_anno, index=anni_sim)
    st.bar_chart(df_bar)

with col2:
    st.subheader("📊 Ripartizione Finale (2030)")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_per_anno[-1].keys()), values=list(ettari_per_anno[-1].values()), hole=.4)])
    st.plotly_chart(fig_pie, use_container_width=True)
