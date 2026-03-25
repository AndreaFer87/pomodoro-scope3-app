import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Scope 3 FLAG dashboard", layout="wide")

# Font size per i grafici
CHART_FONT_SIZE = 18

st.markdown("""
    <style>
    .main-title { font-size: 48px !important; font-weight: bold !important; color: #2E7D32 !important; margin-bottom: 5px !important; }
    .main-subtitle { font-size: 22px !important; color: #444 !important; margin-top: -15px !important; margin-bottom: 30px !important; font-style: italic; }
    .kpi-box { text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 12px; border: 1px solid #ddd; height: 180px; display: flex; flex-direction: column; justify-content: center; }
    .kpi-label { margin:0; font-size: 20px !important; font-weight: bold; color: #1E1E1E; }
    .kpi-value { margin:0; font-size: 32px !important; font-weight: bold; }
    .kpi-sub { margin:0; font-size: 16px; color: #555; font-style: italic; }

    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {
        font-size: 22px !important; 
        font-weight: bold !important;
        color: #000000 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 28px !important;
        color: #000000 !important;
        border-bottom: 2px solid #2E7D32;
        margin-top: 20px !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] span {
        font-size: 18px !important;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌱 Piano di Decarbonizzazione Scope 3 FLAG</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Modello di adozione Rigenerativa: analisi degli Incentivi e proiezione Ettari al 2030</p>', unsafe_allow_html=True)

# --- SESSION STATE ---
if 'cover' not in st.session_state: st.session_state.cover = 33.3
if 'inter' not in st.session_state: st.session_state.inter = 33.3
if 'comb' not in st.session_state: st.session_state.comb = 33.4

def update_sliders(key):
    total_others = 100 - st.session_state[key]
    other_keys = [k for k in ['cover', 'inter', 'comb'] if k != key]
    current_sum_others = sum(st.session_state[k] for k in other_keys)
    if current_sum_others == 0:
        for k in other_keys: st.session_state[k] = total_others / 2
    else:
        for k in other_keys: st.session_state[k] = (st.session_state[k] / current_sum_others) * total_others

# --- SIDEBAR ---
st.sidebar.header("🚜 Strategia di Adozione")
ado_piacenza = st.sidebar.slider("Adozione Piacenza (%)", 0, 100, 40)
ado_cremona = st.sidebar.slider("Adozione Cremona (%)", 0, 100, 30)
ado_mantova = st.sidebar.slider("Adozione Mantova (%)", 0, 100, 30)
ado_altre = st.sidebar.slider("Adozione Altre Prov. (%)", 0, 100, 20)

st.sidebar.header("🌾 Mix Pratiche Strategico (%)")
st.sidebar.slider("Cover Crops (%)", 0.0, 100.0, key='cover', on_change=update_sliders, args=('cover',))
st.sidebar.slider("Interramento (%)", 0.0, 100.0, key='inter', on_change=update_sliders, args=('inter',))
st.sidebar.slider("C.C. + Interramento (%)", 0.0, 100.0, key='comb', on_change=update_sliders, args=('comb',))

st.sidebar.header("Euro Valore Incentivi (€/ha)")
c_cover = st.sidebar.slider("Incentivo Cover Crops", 200, 500, 400, step=10)
c_inter = st.sidebar.slider("Incentivo Interramento", 100, 400, 300, step=10)
c_comb = st.sidebar.slider("Incentivo Combinata", 300, 800, 600, step=10)

st.sidebar.header("💰 Investimento Totale")
budget_iniziale = st.sidebar.number_input("Budget Anno 1 (€)", value=500000, step=50000)
crescita_budget_pct = st.sidebar.slider("Aumento % Annuo Budget", 0, 100, 20)

st.sidebar.header("🎯 Obiettivo Climatico")
target_decarb_req = st.sidebar.slider("Target riduzione 2030 (%)", 10, 50, 27)

st.sidebar.header("⏳ Parametri di Tenuta")
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 3) 
churn_rate = st.sidebar.slider("Tasso abbandono annuo (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento C con abbandono (%)", 0, 100, 25)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 10)

# --- DATABASE PRATICHE PER PROVINCIA ---
DB_GEO = {
    'Piacenza': {
        'ettari': 4000, 'soc_loss_base': 0.7,
        'Cover Crops': {'d_emiss': 0.1, 'd_carb': 1.8},
        'Interramento': {'d_emiss': 0.3, 'd_carb': 2.5},
        'C.C. + Interramento': {'d_emiss': 0.5, 'd_carb': 3.8}
    },
    'Cremona': {
        'ettari': 3500, 'soc_loss_base': 0.5,
        'Cover Crops': {'d_emiss': 0.1, 'd_carb': 1.5},
        'Interramento': {'d_emiss': 0.3, 'd_carb': 2.2},
        'C.C. + Interramento': {'d_emiss': 0.5, 'd_carb': 3.3}
    },
    'Mantova': {
        'ettari': 2500, 'soc_loss_base': 0.4,
        'Cover Crops': {'d_emiss': 0.1, 'd_carb': 1.4},
        'Interramento': {'d_emiss': 0.3, 'd_carb': 2.0},
        'C.C. + Interramento': {'d_emiss': 0.5, 'd_carb': 3.0}
    },
    'Altre': {
        'ettari': 2000, 'soc_loss_base': 0.5,
        'Cover Crops': {'d_emiss': 0.1, 'd_carb': 1.3},
        'Interramento': {'d_emiss': 0.3, 'd_carb': 1.8},
        'C.C. + Interramento': {'d_emiss': 0.5, 'd_carb': 2.8}
    }
}

ETTARI_FILIERA = 12000
BASELINE_TOT_ANNUA = sum(d['ettari'] * (4.5 + d['soc_loss_base']) for d in DB_GEO.values())

# --- MOTORE DI SIMULAZIONE ---
def run_scaling_sim():
    anni = [2026, 2027, 2028, 2029, 2030]
    results_ha, budget_per_anno, traiettoria = [], [], [BASELINE_TOT_ANNUA]
    stock_acc, total_co2_saved_cum = 0, 0
    riparto_previsto = {'Piacenza': ado_piacenza, 'Cremona': ado_cremona, 'Mantova': ado_mantova, 'Altre': ado_altre}

    for i, anno in enumerate(anni):
        bt = budget_iniziale * ((1 + crescita_budget_pct/100) ** i)
        budget_per_anno.append(bt)
        
        c_medio = (st.session_state.cover/100 * c_cover) + (st.session_state.inter/100 * c_inter) + (st.session_state.comb/100 * c_comb)
        tot_ha_incentivabili = bt / c_medio if c_medio > 0 else 0
        
        beneficio_anno = 0
        ha_pratiche_anno = {'Cover Crops': 0, 'Interramento': 0, 'C.C. + Interramento': 0}

        for prov, data in DB_GEO.items():
            ha_target_prov = data['ettari'] * (riparto_previsto[prov]/100)
            ha_limit_budget = tot_ha_incentivabili * (data['ettari'] / ETTARI_FILIERA)
            ha_effettivi = min(ha_target_prov, ha_limit_budget)
            
            mix = {'Cover Crops': st.session_state.cover/100, 'Interramento': st.session_state.inter/100, 'C.C. + Interramento': st.session_state.comb/100}
            for pratica, pct in mix.items():
                p_data = data[pratica]
                ha_pratica = ha_effettivi * pct
                ha_pratiche_anno[pratica] += ha_pratica
                beneficio_anno += (ha_pratica * (p_data['d_carb'] + data['soc_loss_base'] - p_data['d_emiss']))

        stock_acc = (stock_acc * (1 - churn_rate/100) * (1 - perdita_carb/100)) + (beneficio_anno * (1 - safety_buffer/100))
        traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)
        total_co2_saved_cum += stock_acc
        results_ha.append(ha_pratiche_anno.copy())

    return anni, traiettoria, results_ha, budget_per_anno, total_co2_saved_cum

anni_sim, emissioni_sim, ettari_per_anno, budgets, co2_totale = run_scaling_sim()

# --- KPI CALCOLI ---
investimento_totale = sum(budgets)
roi_climatico = investimento_totale / co2_totale if co2_totale > 0 else 0
riduzione_pct = (1 - (emissioni_sim[-1] / BASELINE_TOT_ANNUA)) * 100
target_val = BASELINE_TOT_ANNUA * (1 - target_decarb_req/100)
gap_2030 = emissioni_sim[-1] - target_val

# --- LAYOUT KPI ---
st.markdown("---")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.markdown(f'<div class="kpi-box"><p class="kpi-label">Riduzione %</p><p class="kpi-value" style="color:green;">-{riduzione_pct:.1f}%</p><p class="kpi-sub">Target {target_decarb_req}%</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-box"><p class="kpi-label">ROI Climatico</p><p class="kpi-value" style="color:#1a73e8;">{roi_climatico:.2f} €/t</p><p class="kpi-sub">Costo medio CO2</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-box"><p class="kpi-label">Investimento 5Y</p><p class="kpi-value">€ {int(investimento_totale):,}</p><p class="kpi-sub">Budget totale</p></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-box"><p class="kpi-label">CO2 Salvata</p><p class="kpi-value">{int(co2_totale):,} t</p><p class="kpi-sub">Sequestro totale</p></div>', unsafe_allow_html=True)
col_gap = "green" if gap_2030 <= 0 else "red"
c5.markdown(f'<div class="kpi-box" style="border: 2px solid {col_gap};"><p class="kpi-label">Gap al Target</p><p class="kpi-value" style="color:{col_gap};">{int(gap_2030)} t</p><p class="kpi-sub">CO2 mancante</p></div>', unsafe_allow_html=True)
c6.markdown(f'<div class="kpi-box"><p class="kpi-label">Ettari 2030</p><p class="kpi-value">{int(sum(ettari_per_anno[-1].values()))}</p><p class="kpi-sub">Superficie in Reg Ag</p></div>', unsafe_allow_html=True)

# --- GRAFICI ---
st.markdown("---")
l, r = st.columns([1.2, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni Scope 3")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[2025]+anni_sim, y=emissioni_sim, name="Emissione Netta", marker_color='#808080'))
    fig.add_shape(type="line", x0=2024.5, x1=2030.5, y0=target_val, y1=target_val, line=dict(color="red", width=3, dash="dash"))
    fig.update_layout(height=550, yaxis=dict(range=[20000, 65000], tickformat=",.0f"), legend=dict(orientation="h", y=1.15))
    st.plotly_chart(fig, use_container_width=True)
    
with r:
    st.subheader("🚜 Evoluzione Mix Pratiche (ha)")
    df_bar = pd.DataFrame(ettari_per_anno, index=anni_sim)
    fig_bar = go.Figure()
    for col in df_bar.columns: fig_bar.add_trace(go.Bar(x=df_bar.index, y=df_bar[col], name=col))
    fig_bar.update_layout(barmode='stack', height=500, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
l2, r2 = st.columns([1, 1])
with l2:
    st.subheader("💰 Budget Annuo vs Cumulativo")
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(x=anni_sim, y=budgets, name="Annuo (€)", marker_color='#81C784'))
    fig_fin.add_trace(go.Scatter(x=anni_sim, y=np.cumsum(budgets), name="Cumulativo (€)", line=dict(color='#1a73e8', width=3), yaxis="y2"))
    fig_fin.update_layout(height=400, yaxis2=dict(overlaying="y", side="right"), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_fin, use_container_width=True)
with r2:
    st.subheader("📊 Ripartizione Ettari Finale (2030)")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_per_anno[-1].keys()), values=list(ettari_per_anno[-1].values()), hole=.4)])
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)
