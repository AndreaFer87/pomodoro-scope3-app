import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scope 3 FLAG dashboard", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 48px !important; font-weight: bold !important; color: #2E7D32 !important; }
    .sub-title { font-size: 20px !important; color: #555555 !important; margin-bottom: 20px !important; }
    .stSlider label, .stNumberInput label { font-size: 18px !important; font-weight: bold !important; }
    .kpi-box {
        text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 12px; 
        border: 1px solid #ddd; height: 160px; display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-label { margin:0; font-size: 18px !important; font-weight: bold; color: #1E1E1E; }
    .kpi-value { margin:0; font-size: 26px !important; font-weight: bold; }
    .kpi-sub { margin:0; font-size: 14px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🚀 Scope 3 FLAG Scalability Plan</p>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.01, 1.0, 0.5)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.01, 1.0, 0.5)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.01, 1.0, 0.5)

st.sidebar.header("💰 Strategia di Investimento")
budget_iniziale = st.sidebar.number_input("Budget Anno 1 (€)", value=150000, step=50000)
crescita_budget_pct = st.sidebar.slider("Aumento % Annuo Budget", 0, 100, 20)

st.sidebar.header("🎯 Obiettivi Climatici")
target_decarb_req = st.sidebar.slider("Target Richiesto 2030 (%)", 10, 50, 27)

st.sidebar.header("⏳ Parametri di Tenuta")
churn_rate = st.sidebar.slider("Tasso abbandono annuo (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 24)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 10)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 3) 

# --- DATABASE PRATICHE ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 225, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 300, 'diff': 1},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 525, 'diff': 3}
}
df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
RESA_TOM_HA = 80
PROD_TOT_TON = ETTARI_FILIERA * RESA_TOM_HA
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- MOTORE DI SIMULAZIONE ---
def run_scaling_sim(wi, wc, wd):
    anni = [2026, 2027, 2028, 2029, 2030]
    results_ha = []
    budget_per_anno = []
    traiettoria = [BASELINE_TOT_ANNUA]
    stock_acc = 0
    
    d = df_p.copy()
    d['Imp_Val'] = ((-d['d_emiss'] + d['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
    
    # Normalizzazione per MCDA (fondamentale per far cambiare il mix)
    d['S_Imp'] = (d['Imp_Val'] - d['Imp_Val'].min()) / (d['Imp_Val'].max() - d['Imp_Val'].min() + 0.01)
    d['S_Cost'] = (d['costo'].max() - d['costo']) / (d['costo'].max() - d['costo'].min() + 0.01)
    d['S_Diff'] = (5 - d['diff']) / (5 - 1 + 0.01)
    d['Score'] = (wi * d['S_Imp'] + wc * d['S_Cost'] + wd * d['S_Diff']) / (wi + wc + wd)
    
    for i, anno in enumerate(anni):
        budget_t = budget_iniziale * ((1 + crescita_budget_pct/100) ** i)
        budget_per_anno.append(budget_t)
        
        ha_alloc = {p: 0.0 for p in d.index}
        # Quota spontanea
        for p in d[d['diff'] <= 3].index:
            ha_alloc[p] = (ETTARI_FILIERA * (prob_minima/100)) / len(d[d['diff'] <= 3].index)
        
        costo_impegnato = sum(ha_alloc[p] * d.at[p, 'costo'] for p in ha_alloc)
        budget_extra = max(0, budget_t - costo_impegnato)
        
        # Allocazione basata sullo SCORE (qui i pesi cambiano tutto!)
        for nome, row in d.sort_values(by='Score', ascending=False).iterrows():
            if budget_extra <= 0: break
            ettari_liberi = (ETTARI_FILIERA / 1.2) - ha_alloc[nome] # limite tecnico per pratica
            da_agg = min(budget_extra / row['costo'], max(0, ettari_liberi))
            ha_alloc[nome] += da_agg
            budget_extra -= (da_agg * row['costo'])
            
        beneficio_t = sum(ha_alloc[p] * d.at[p, 'Imp_Val'] for p in ha_alloc)
        stock_acc = (stock_acc * (100-perdita_carb)/100 * (100-churn_rate)/100) + beneficio_t
        traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)
        results_ha.append(ha_alloc.copy())
        
    return anni, traiettoria, results_ha, budget_per_anno

anni_sim, emissioni_sim, ettari_per_anno, budgets = run_scaling_sim(w_imp, w_cost, w_diff)

# --- CALCOLI KPI ---
impronta_iniziale = BASELINE_TOT_ANNUA * 1000 / PROD_TOT_TON
impronta_finale = emissioni_sim[-1] * 1000 / PROD_TOT_TON
riduzione_effettiva = (1 - (emissioni_sim[-1] / BASELINE_TOT_ANNUA)) * 100
target_assoluto = BASELINE_TOT_ANNUA * (1 - target_decarb_req/100)
gap_2030 = emissioni_sim[-1] - target_assoluto

# --- KPI BOXES ---
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

c1.markdown(f'<div class="kpi-box"><p class="kpi-label">Impronta CO2 🍅</p><p class="kpi-value" style="color:#E64A19;">{impronta_iniziale:.2f} → {impronta_finale:.2f}</p><p class="kpi-sub">kg CO2/ton (2025 vs 2030)</p></div>', unsafe_allow_html=True)

c2.markdown(f'<div class="kpi-box"><p class="kpi-label">Riduzione Raggiunta</p><p class="kpi-value" style="color:#2E7D32;">- {riduzione_effettiva:.1f}%</p><p class="kpi-sub">su baseline totale</p></div>', unsafe_allow_html=True)

c3.markdown(f'<div class="kpi-box"><p class="kpi-label">Investimento (5Y)</p><p class="kpi-value" style="color:#1a73e8;">€ {int(sum(budgets)):,}</p><p class="kpi-sub">Budget totale cumulato</p></div>', unsafe_allow_html=True)

col_gap = "#2E7D32" if gap_2030 <= 0 else "#D32F2F"
c4.markdown(f'<div class="kpi-box" style="border: 2px solid {col_gap};"><p class="kpi-label">Gap al Target</p><p class="kpi-value" style="color:{col_gap};">{int(gap_2030)} tCO2</p><p class="kpi-sub">vs target {target_decarb_req}%</p></div>', unsafe_allow_html=True)

c5.markdown(f'<div class="kpi-box"><p class="kpi-label">Ettari 2030</p><p class="kpi-value">{int(sum(ettari_per_anno[-1].values()))}</p><p class="kpi-sub">superficie incentivata</p></div>', unsafe_allow_html=True)

# --- GRAFICI ---
st.markdown("---")
l, r = st.columns([1.2, 1])

with l:
    st.subheader("📅 Traiettoria Emissioni Scope 3")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[2025]+anni_sim, y=emissioni_sim, mode='lines+markers', line=dict(color='#2E7D32', width=4), name="Emissione Netta"))
    fig.add_trace(go.Scatter(x=[2025, 2030], y=[target_assoluto]*2, line=dict(dash='dash', color='#D32F2F'), name="Target Richiesto"))
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

with r:
    st.subheader("🚜 Evoluzione Mix Pratiche (ha)")
    df_bar = pd.DataFrame(ettari_per_anno, index=anni_sim)
    fig_bar = go.Figure()
    for col in df_bar.columns:
        fig_bar.add_trace(go.Bar(name=col, x=anni_sim, y=df_bar[col]))
    fig_bar.update_layout(barmode='stack', height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
l2, r2 = st.columns([1, 1])

with l2:
    st.subheader("💰 Analisi Finanziaria Scaling")
    budget_cumulativo = np.cumsum(budgets)
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(x=anni_sim, y=budgets, name="Budget Annuo (€)", marker_color='#81C784'))
    fig_fin.add_trace(go.Scatter(x=anni_sim, y=budget_cumulativo, name="Cumulativo (€)", line=dict(color='#1a73e8', width=4), yaxis="y2"))
    fig_fin.update_layout(height=400, yaxis=dict(title="€ Annuo"), yaxis2=dict(title="€ Cumulativo", overlaying="y", side="right"), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_fin, use_container_width=True)

with r2:
    st.subheader("📊 Ripartizione Mix Pratiche al 2030")
    labels = list(ettari_per_anno[-1].keys())
    values = list(ettari_per_anno[-1].values())
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)
