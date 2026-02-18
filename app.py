import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Strategy 2030", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Modello Strategico: Default 40% Decay & Full KPI Dashboard")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Strategici (MCDA)")
w_imp = st.sidebar.slider("Peso Impatto CO2", 0.0, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.0, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.0, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)

st.sidebar.header("⏳ Dinamiche Temporali")
churn_rate = st.sidebar.slider("Churn Rate (%)", 0, 50, 10)
# SET DEFAULT A 40% COME RICHIESTO
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 40) 
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 30, 15)

# --- DATABASE FISSO ---
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.1,  'd_carb': 1.5, 'costo': 250, 'diff': 3},
    'Interramento':         {'d_emiss': 0.3,  'd_carb': 2.2, 'costo': 200, 'diff': 1},
    'Minima Lav.':          {'d_emiss': -0.7, 'd_carb': 0.36, 'costo': 250, 'diff': 2},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3, 'costo': 700, 'diff': 3},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.9, 'costo': 500, 'diff': 4},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.6, 'costo': 450, 'diff': 3},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5}
}

df_p = pd.DataFrame(pratiche_base).T
LOSS_SOC_BASE_HA = 0.5
ETTARI_FILIERA = 10000
BASELINE_TOT_ANNUA = ETTARI_FILIERA * (4.0 + LOSS_SOC_BASE_HA)

# --- STANDARDIZZAZIONE ---
def safe_norm(series, invert=False):
    if series.max() == series.min(): return series * 0.0 + 0.5
    return (series.max() - series)/(series.max() - series.min()) if invert else (series - series.min())/(series.max() - series.min())

df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
df_p['S_Imp'] = safe_norm(df_p['Imp_Val'])
df_p['S_Cost'] = safe_norm(df_p['costo'], invert=True)
df_p['S_Diff'] = safe_norm(df_p['diff'], invert=True)
df_p['Score'] = (df_p['S_Imp'] * w_imp) + (df_p['S_Cost'] * w_cost) + (df_p['S_Diff'] * w_diff)

# --- ALLOCAZIONE ---
ettari_allocati = {p: 0.0 for p in df_p.index}
pratiche_spontanee = df_p[df_p['diff'] <= 3].index
if not pratiche_spontanee.empty:
    ha_base = (ETTARI_FILIERA * (prob_minima/100)) / len(pratiche_spontanee)
    for p in pratiche_spontanee: ettari_allocati[p] = ha_base

target_ton_annuo = BASELINE_TOT_ANNUA * (target_decarb/100)
budget_residuo = budget_annuo - sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())

for nome, row in df_p.sort_values(by='Score', ascending=False).iterrows():
    abb_attuale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    if abb_attuale >= target_ton_annuo or budget_residuo <= 0: break
    da_agg = min((target_ton_annuo - abb_attuale) / row['Imp_Val'], budget_residuo / row['costo'], ETTARI_FILIERA - sum(ettari_allocati.values()))
    if da_agg > 0:
        ettari_allocati[nome] += da_agg
        budget_residuo -= da_agg * row['costo']

# --- TRAIETTORIA 2030 ---
anni = [2026, 2027, 2028, 2029, 2030]
rit_c, rit_h = (100 - perdita_carb)/100, (100 - churn_rate)/100
traiettoria = []
stock = 0
beneficio_nuovo = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())

for anno in anni:
    stock = (stock * rit_c * rit_h) + beneficio_nuovo
    traiettoria.append(BASELINE_TOT_ANNUA - stock)

# --- BOX KPI (5 BOX RICHIESTI) ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ettari Programma", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("CO2 Abbattuta 2030", f"{int(stock)} t")
c3.metric("€/t Medio Pesato", f"{( (budget_annuo-budget_residuo)/beneficio_nuovo if beneficio_nuovo>0 else 0):.2f} €")
c4.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
c5.metric("Gap al Target (2030)", f"{int(max(0, (BASELINE_TOT_ANNUA - target_ton_annuo) - traiettoria[-1]))} t")

st.markdown("---")
l, r = st.columns([1.5, 1])

with l:
    st.subheader("📅 Traiettoria Emissioni")
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria, mode='lines+markers', line=dict(color='green', width=4), name="Emissione Netta"))
    fig_line.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT_ANNUA - target_ton_annuo]*5, line=dict(dash='dot', color='red'), name="Target"))
    st.plotly_chart(fig_line, use_container_width=True)

with r:
    st.subheader("📊 Mix Pratiche")
    labels = [p for p, ha in ettari_allocati.items() if ha > 0.1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0.1]
    st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)

# --- WATERFALL ---
st.subheader("📉 Analisi Variazione Emissioni (Waterfall)")
v_input = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
v_soc = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    orientation = "v",
    x = ["Baseline 2025", "Input (Emissioni)", "SOC (Sequestro)", "Emissione Netta"],
    y = [BASELINE_TOT_ANNUA, v_input, -v_soc, 0],
    measure = ["absolute", "relative", "relative", "total"]
))
st.plotly_chart(fig_wf, use_container_width=True)

# --- TABELLA SCORE (VERSIONE CORRETTA SENZA MATPLOTLIB) ---
st.subheader("⚖️ Matrice Decisionale MCDA")
st.dataframe(df_p[['S_Imp', 'S_Cost', 'S_Diff', 'Score']].sort_values(by='Score', ascending=False).format("{:.2f}"))

st.write("### 🚜 Piano Operativo Suggerito (ha/anno)")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ettari_allocati.items() if ha > 0}, orient='index', columns=['Ettari']))
