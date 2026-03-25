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
    .main-title { font-size: 45px !important; font-weight: bold !important; color: #2E7D32 !important; }
    
    /* KPI BOX - TESTI PIÙ GRANDI */
    .kpi-box {
        text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 12px; 
        border: 1px solid #ddd; height: 180px; display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-label { margin:0; font-size: 20px !important; font-weight: bold; color: #1E1E1E; }
    .kpi-value { margin:0; font-size: 32px !important; font-weight: bold; }
    .kpi-sub { margin:0; font-size: 16px; color: #555; }

    /* SIDEBAR - TESTI SLIDER PIÙ GRANDI */
    section[data-testid="stSidebar"] .stSlider label { font-size: 20px !important; font-weight: bold !important; }
    section[data-testid="stSidebar"] .stNumberInput label { font-size: 20px !important; font-weight: bold !important; }
    section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 26px !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🚀 Scope 3 FLAG Scalability Plan</p>', unsafe_allow_html=True)

# --- SESSION STATE PER RESET SELETTIVO ---
if 'cover' not in st.session_state:
    st.session_state.cover = 33.3
if 'inter' not in st.session_state:
    st.session_state.inter = 33.3
if 'comb' not in st.session_state:
    st.session_state.comb = 33.4

def reset_mix_only():
    st.session_state.cover = 33.3
    st.session_state.inter = 33.3
    st.session_state.comb = 33.4

def update_sliders(key):
    total_others = 100 - st.session_state[key]
    other_keys = [k for k in ['cover', 'inter', 'comb'] if k != key]
    if total_others <= 0:
        for k in other_keys: st.session_state[k] = 0.0
    else:
        current_sum_others = sum(st.session_state[k] for k in other_keys)
        if current_sum_others == 0:
            for k in other_keys: st.session_state[k] = total_others / 2
        else:
            for k in other_keys:
                st.session_state[k] = (st.session_state[k] / current_sum_others) * total_others

# --- SIDEBAR ---
st.sidebar.header("🚜 Sentiment Filiera (Mix %)")
if st.sidebar.button("🔄 Reset Solo Mix"):
    reset_mix_only()

st.sidebar.slider("Cover Crops (%)", 0.0, 100.0, key='cover', on_change=update_sliders, args=('cover',))
st.sidebar.slider("Interramento (%)", 0.0, 100.0, key='inter', on_change=update_sliders, args=('inter',))
st.sidebar.slider("C.C. + Interramento (%)", 0.0, 100.0, key='comb', on_change=update_sliders, args=('comb',))

st.sidebar.header("💶 Valore Incentivi (€/ha)")
c_cover = st.sidebar.slider("Incentivo Cover Crops (€)", 200, 500, 400, step=10)
c_inter = st.sidebar.slider("Incentivo Interramento (€)", 100, 400, 300, step=10)
c_comb = st.sidebar.slider("Incentivo Combinata (€)", 300, 800, 600, step=10)

st.sidebar.header("💰 Investimento Totale")
budget_iniziale = st.sidebar.number_input("Budget Anno 1 (€)", value=500000, step=50000)
crescita_budget_pct = st.sidebar.slider("Aumento % Annuo Budget", 0, 100, 20)

st.sidebar.header("🎯 Obiettivi Climatici")
target_decarb_req = st.sidebar.slider("Target Richiesto 2030 (%)", 10, 50, 27)

st.sidebar.header("⏳ Parametri di Tenuta")
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 3) 
churn_rate = st.sidebar.slider("Tasso abbandono annuo (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 25)
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 10)

# --- DATABASE PRATICHE ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': c_cover},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': c_inter},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': c_comb}
}
df_p = pd.DataFrame(pratiche_base).T
ETTARI_FILIERA = 12000
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.5 + LOSS_SOC_BASE_HA)

# --- MOTORE DI SIMULAZIONE ---
def run_scaling_sim():
    anni = [2026, 2027, 2028, 2029, 2030]
    results_ha, budget_per_anno, traiettoria = [], [], [BASELINE_TOT_ANNUA]
    df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
    stock_acc = 0
    total_co2_saved_cum = 0
    for i, anno in enumerate(anni):
        bt = budget_iniziale * ((1 + crescita_budget_pct/100) ** i)
        budget_per_anno.append(bt)
        ha = {p: 0.0 for p in df_p.index}
        ha_spont = ETTARI_FILIERA * (prob_minima/100)
        ha['Cover Crops'] = ha_spont / 2
        ha['Interramento'] = ha_spont / 2
        costo_s = sum(ha[p] * df_p.at[p, 'costo'] for p in ha)
        b_extra = max(0, bt - costo_s)
        ha['Cover Crops'] += (b_extra * (st.session_state.cover/100)) / df_p.at['Cover Crops', 'costo']
        ha['Interramento'] += (b_extra * (st.session_state.inter/100)) / df_p.at['Interramento', 'costo']
        ha['C.C. + Interramento'] += (b_extra * (st.session_state.comb/100)) / df_p.at['C.C. + Interramento', 'costo']
        tot_ha = sum(ha.values())
        if tot_ha > ETTARI_FILIERA:
            ratio = ETTARI_FILIERA / tot_ha
            for p in ha: ha[p] *= ratio
        beneficio_t = sum(ha[p] * df_p.at[p, 'Imp_Val'] for p in ha)
        stock_acc = (stock_acc * (1 - churn_rate/100) * (1 - perdita_carb/100)) + beneficio_t
        traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)
        total_co2_saved_cum += stock_acc
        results_ha.append(ha.copy())
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
c1.markdown(f'<div class="kpi-box"><p class="kpi-label">Riduzione %</p><p class="kpi-value" style="color:green;">-{riduzione_pct:.1f}%</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-box"><p class="kpi-label">ROI Climatico</p><p class="kpi-value" style="color:#1a73e8;">{roi_climatico:.2f} €/t</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-box"><p class="kpi-label">Investimento 5Y</p><p class="kpi-value">€ {int(investimento_totale):,}</p></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-box"><p class="kpi-label">CO2 Salvata</p><p class="kpi-value">{int(co2_totale):,} t</p></div>', unsafe_allow_html=True)
col_gap = "green" if gap_2030 <= 0 else "red"
c5.markdown(f'<div class="kpi-box" style="border: 2px solid {col_gap};"><p class="kpi-label">Gap al Target</p><p class="kpi-value" style="color:{col_gap};">{int(gap_2030)} t</p></div>', unsafe_allow_html=True)
c6.markdown(f'<div class="kpi-box"><p class="kpi-label">Ettari 2030</p><p class="kpi-value">{int(sum(ettari_per_anno[-1].values()))}</p></div>', unsafe_allow_html=True)

# --- GRAFICI (FIXED) ---
st.markdown("---")
l, r = st.columns([1.2, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni Scope 3")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[2025]+anni_sim, y=emissioni_sim, mode='lines+markers', line=dict(color='#2E7D32', width=4), name="Emissione Netta"))
    fig.add_trace(go.Scatter(x=[2025, 2030], y=[target_val]*2, line=dict(dash='dash', color='red'), name="Target FLAG"))
    
    # FIX: Gestione legenda e font assi
    fig.update_layout(
        height=500, margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE),
        xaxis=dict(tickfont_size=CHART_FONT_SIZE, title_font_size=CHART_FONT_SIZE),
        yaxis=dict(tickfont_size=CHART_FONT_SIZE, title_font_size=CHART_FONT_SIZE, tickformat=",.0f")
    )
    st.plotly_chart(fig, use_container_width=True)

with r:
    st.subheader("🚜 Evoluzione Mix Pratiche (ha)")
    df_bar = pd.DataFrame(ettari_per_anno, index=anni_sim)
    fig_bar = go.Figure()
    for col in df_bar.columns:
        fig_bar.add_trace(go.Bar(x=df_bar.index, y=df_bar[col], name=col))
    fig_bar.update_layout(
        barmode='stack', height=500,
        legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE-2),
        xaxis=dict(tickfont_size=CHART_FONT_SIZE),
        yaxis=dict(tickfont_size=CHART_FONT_SIZE)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
l2, r2 = st.columns([1, 1])
with l2:
    st.subheader("💰 Budget Annuo vs Cumulativo")
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(x=anni_sim, y=budgets, name="Annuo (€)", marker_color='#81C784'))
    fig_fin.add_trace(go.Scatter(x=anni_sim, y=np.cumsum(budgets), name="Cumulativo (€)", line=dict(color='#1a73e8', width=3), yaxis="y2"))
    fig_fin.update_layout(
        height=400, 
        yaxis2=dict(overlaying="y", side="right", tickfont_size=CHART_FONT_SIZE),
        legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE),
        xaxis=dict(tickfont_size=CHART_FONT_SIZE),
        yaxis=dict(tickfont_size=CHART_FONT_SIZE)
    )
    st.plotly_chart(fig_fin, use_container_width=True)
with r2:
    st.subheader("📊 Ripartizione Ettari Finale (2030)")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_per_anno[-1].keys()), values=list(ettari_per_anno[-1].values()), hole=.4)])
    fig_pie.update_traces(textfont_size=CHART_FONT_SIZE)
    fig_pie.update_layout(height=400, legend=dict(font_size=CHART_FONT_SIZE))
    st.plotly_chart(fig_pie, use_container_width=True)
