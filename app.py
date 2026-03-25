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

    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p { font-size: 22px !important; font-weight: bold !important; color: #000000 !important; line-height: 1.2 !important; }
    section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 28px !important; color: #000000 !important; border-bottom: 2px solid #2E7D32; margin-top: 20px !important; }
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] span { font-size: 18px !important; color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🌱 Piano di Decarbonizzazione Scope 3 FLAG</p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Modello di adozione Rigenerativa: analisi degli Incentivi e proiezione Ettari al 2030</p>', unsafe_allow_html=True)

# --- LOGICA RESET 25% ---
def reset_to_equidistribution():
    for p in ['pc', 'cr', 'mn', 'al']:
        for treat in ['cover', 'inter', 'comb']:
            st.session_state[f"ado_{p}_{treat}"] = 25.0

if "ado_pc_cover" not in st.session_state:
    reset_to_equidistribution()

# --- SIDEBAR ---
st.sidebar.header("🚜 Tassi Adozione per Pratica")
if st.sidebar.button("🔄 Reset al 25% per Provincia"):
    reset_to_equidistribution()

with st.sidebar.expander("📍 Piacenza", expanded=True):
    ado_pc_cover = st.slider("PC - Cover Crops (%)", 0.0, 100.0, key="ado_pc_cover")
    ado_pc_inter = st.slider("PC - Interramento (%)", 0.0, 100.0, key="ado_pc_inter")
    ado_pc_comb  = st.slider("PC - Combinata (%)", 0.0, 100.0, key="ado_pc_comb")

with st.sidebar.expander("📍 Cremona"):
    ado_cr_cover = st.slider("CR - Cover Crops (%)", 0.0, 100.0, key="ado_cr_cover")
    ado_cr_inter = st.slider("CR - Interramento (%)", 0.0, 100.0, key="ado_cr_inter")
    ado_cr_comb  = st.slider("CR - Combinata (%)", 0.0, 100.0, key="ado_cr_comb")

with st.sidebar.expander("📍 Mantova"):
    ado_mn_cover = st.slider("MN - Cover Crops (%)", 0.0, 100.0, key="ado_mn_cover")
    ado_mn_inter = st.slider("MN - Interramento (%)", 0.0, 100.0, key="ado_mn_inter")
    ado_mn_comb  = st.slider("MN - Combinata (%)", 0.0, 100.0, key="ado_mn_comb")

with st.sidebar.expander("📍 Altre Province"):
    ado_al_cover = st.slider("AL - Cover Crops (%)", 0.0, 100.0, key="ado_al_cover")
    ado_al_inter = st.slider("AL - Interramento (%)", 0.0, 100.0, key="ado_al_inter")
    ado_al_comb  = st.slider("AL - Combinata (%)", 0.0, 100.0, key="ado_al_comb")

st.sidebar.header("💶 Valore Incentivi (€/ha)")
c_cover = st.sidebar.slider("Incentivo Cover Crops", 200, 500, 400, step=10)
c_inter = st.sidebar.slider("Incentivo Interramento", 100, 400, 300, step=10)
c_comb  = st.sidebar.slider("Incentivo Combinata", 300, 800, 600, step=10)

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

# --- VISUALIZZAZIONE LIVE: DONUT CHARTS ---
st.subheader("📊 Bilanciamento Adozione per Pratica (Ripartizione Province)")
cp1, cp2, cp3 = st.columns(3)

def make_donut(vals, title):
    fig = go.Figure(data=[go.Pie(labels=['PC', 'CR', 'MN', 'AL'], values=vals, hole=.5)])
    fig.update_layout(title_text=title, title_x=0.5, height=250, margin=dict(t=50, b=0, l=0, r=0), showlegend=False)
    fig.update_traces(textinfo='label+percent', marker=dict(colors=['#2E7D32', '#43A047', '#66BB6A', '#A5D6A7']))
    return fig

with cp1: st.plotly_chart(make_donut([ado_pc_cover, ado_cr_cover, ado_mn_cover, ado_al_cover], "Cover Crops"), use_container_width=True)
with cp2: st.plotly_chart(make_donut([ado_pc_inter, ado_cr_inter, ado_mn_inter, ado_al_inter], "Interramento"), use_container_width=True)
with cp3: st.plotly_chart(make_donut([ado_pc_comb, ado_cr_comb, ado_mn_comb, ado_al_comb], "Combinata"), use_container_width=True)

# --- DATABASE E CALCOLO ---
DB_GEO = {
    'Piacenza': {
        'ettari': 4200, 'loss_soc': 1.8, 
        'ado': {'Cover Crops': ado_pc_cover/100, 'Interramento': ado_pc_inter/100, 'C.C. + Interramento': ado_pc_comb/100},
        'perf': {'Cover Crops': [-0.1, 1.8], 'Interramento': [0.3, 2.5], 'C.C. + Interramento': [0.3, 3.8]}
    },
    'Cremona': {
        'ettari': 2800, 'loss_soc': 0.05,
        'ado': {'Cover Crops': ado_cr_cover/100, 'Interramento': ado_cr_inter/100, 'C.C. + Interramento': ado_cr_comb/100},
        'perf': {'Cover Crops': [0.1, 1.5], 'Interramento': [0.3, 2.2], 'C.C. + Interramento': [0.3, 3.5]}
    },
    'Mantova': {
        'ettari': 1300, 'loss_soc': 0.1,
        'ado': {'Cover Crops': ado_mn_cover/100, 'Interramento': ado_mn_inter/100, 'C.C. + Interramento': ado_mn_comb/100},
        'perf': {'Cover Crops': [0.1, 1.5], 'Interramento': [0.3, 2.2], 'C.C. + Interramento': [0.3, 3.5]}
    },
    'Altre': {
        'ettari': 3700, 'loss_soc': 0.3,
        'ado': {'Cover Crops': ado_al_cover/100, 'Interramento': ado_al_inter/100, 'C.C. + Interramento': ado_al_comb/100},
        'perf': {'Cover Crops': [-0.1, 1.4], 'Interramento': [0.3, 2.2], 'C.C. + Interramento': [0.3, 3.5]}
    }
}

BASELINE_TOT_ANNUA = sum(d['ettari'] * (4.5 + d['loss_soc']) for d in DB_GEO.values())
COSTI = {'Cover Crops': c_cover, 'Interramento': c_inter, 'C.C. + Interramento': c_comb}

# --- MOTORE DI SIMULAZIONE ---
def run_matrix_sim():
    anni = [2026, 2027, 2028, 2029, 2030]
    results_ha, budget_per_anno, traiettoria = [], [], [BASELINE_TOT_ANNUA]
    stock_acc, co2_cum = 0, 0

    for i, anno in enumerate(anni):
        bt = budget_iniziale * ((1 + crescita_budget_pct/100) ** i)
        budget_per_anno.append(bt)
        ben_anno = 0
        ha_ripartiti = {p: 0.0 for p in COSTI.keys()}
        
        fabbisogno = sum(d['ettari'] * (t + prob_minima/100) * COSTI[pr] for d in DB_GEO.values() for pr, t in d['ado'].items())
        scaler = min(1.0, bt / fabbisogno) if fabbisogno > 0 else 0
        
        for prov, data in DB_GEO.items():
            for pratica, tasso in data['ado'].items():
                ha_p = (data['ettari'] * (tasso + prob_minima/100)) * scaler
                ha_ripartiti[pratica] += ha_p
                
                # --- BLOCCO RICHIESTO ---
                d_emiss, d_carb = data['perf'][pratica]
                imp_val = (d_carb + data['loss_soc'] - d_emiss) * (1 - safety_buffer/100)
                # ------------------------
                ben_anno += (ha_p * imp_val)

        stock_acc = (stock_acc * (1 - churn_rate/100) * (1 - perdita_carb/100)) + ben_anno
        traiettoria.append(BASELINE_TOT_ANNUA - stock_acc)
        co2_cum += stock_acc
        results_ha.append(ha_ripartiti.copy())

    return anni, traiettoria, results_ha, budget_per_anno, co2_cum

anni_sim, emissioni_sim, ettari_per_anno, budgets, co2_totale = run_matrix_sim()

# --- KPI LAYOUT ---
st.markdown("---")
c1, c2, c3, c4, c5, c6 = st.columns(6)
riduzione_pct = (1 - (emissioni_sim[-1] / BASELINE_TOT_ANNUA)) * 100
target_val = BASELINE_TOT_ANNUA * (1 - target_decarb_req/100)
gap_2030 = emissioni_sim[-1] - target_val

c1.markdown(f'<div class="kpi-box"><p class="kpi-label">Riduzione %</p><p class="kpi-value" style="color:green;">-{riduzione_pct:.1f}%</p><p class="kpi-sub">Target {target_decarb_req}%</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-box"><p class="kpi-label">ROI Climatico</p><p class="kpi-value" style="color:#1a73e8;">{sum(budgets)/co2_totale if co2_totale > 0 else 0:.2f} €/t</p><p class="kpi-sub">Costo medio CO2</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-box"><p class="kpi-label">Investimento 5Y</p><p class="kpi-value">€ {int(sum(budgets)):,}</p><p class="kpi-sub">Budget totale</p></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-box"><p class="kpi-label">CO2 Salvata</p><p class="kpi-value">{int(co2_totale):,} t</p><p class="kpi-sub">Sequestro totale</p></div>', unsafe_allow_html=True)
col_gap = "green" if gap_2030 <= 0 else "red"
c5.markdown(f'<div class="kpi-box" style="border: 2px solid {col_gap};"><p class="kpi-label">Gap al Target</p><p class="kpi-value" style="color:{col_gap};">{int(gap_2030)} t</p><p class="kpi-sub">CO2 mancante</p></div>', unsafe_allow_html=True)
c6.markdown(f'<div class="kpi-box"><p class="kpi-label">Ettari 2030</p><p class="kpi-value">{int(sum(ettari_per_anno[-1].values()))}</p><p class="kpi-sub">Superficie in Reg Ag</p></div>', unsafe_allow_html=True)

# --- PRIMA FILA GRAFICI ---
st.markdown("---")
l, r = st.columns([1.2, 1])
with l:
    st.subheader("📅 Traiettoria Emissioni Scope 3")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[2025]+anni_sim, y=emissioni_sim, name="Emissione Netta", marker_color='#808080'))
    fig.add_shape(type="line", x0=2024.5, x1=2030.5, y0=target_val, y1=target_val, line=dict(color="red", width=3, dash="dash"))
    fig.update_layout(height=450, yaxis=dict(tickformat=",.0f", range=[20000, 65000]), legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE-4))
    st.plotly_chart(fig, use_container_width=True)
with r:
    st.subheader("🚜 Evoluzione Mix Pratiche (ha)")
    df_bar = pd.DataFrame(ettari_per_anno, index=anni_sim)
    fig_bar = go.Figure()
    for col in df_bar.columns: fig_bar.add_trace(go.Bar(x=df_bar.index, y=df_bar[col], name=col))
    fig_bar.update_layout(barmode='stack', height=450, legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE-2))
    st.plotly_chart(fig_bar, use_container_width=True)

# --- SECONDA FILA GRAFICI (GLI ULTIMI DUE MANCANTI) ---
st.markdown("---")
l2, r2 = st.columns([1, 1])
with l2:
    st.subheader("💰 Budget Annuo vs Cumulativo")
    fig_fin = go.Figure()
    fig_fin.add_trace(go.Bar(x=anni_sim, y=budgets, name="Annuo (€)", marker_color='#81C784'))
    fig_fin.add_trace(go.Scatter(x=anni_sim, y=np.cumsum(budgets), name="Cumulativo (€)", line=dict(color='#1a73e8', width=3), yaxis="y2"))
    fig_fin.update_layout(height=400, yaxis2=dict(overlaying="y", side="right", tickfont_size=CHART_FONT_SIZE-4), 
                          legend=dict(orientation="h", y=1.1, font_size=CHART_FONT_SIZE-4))
    st.plotly_chart(fig_fin, use_container_width=True)
with r2:
    st.subheader("📊 Ripartizione Ettari Finale (2030)")
    fig_pie = go.Figure(data=[go.Pie(labels=list(ettari_per_anno[-1].keys()), values=list(ettari_per_anno[-1].values()), hole=.4)])
    fig_pie.update_traces(textfont_size=CHART_FONT_SIZE)
    fig_pie.update_layout(height=400, legend=dict(font_size=CHART_FONT_SIZE-4))
    st.plotly_chart(fig_pie, use_container_width=True)
