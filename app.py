import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Executive Dashboard", layout="wide")

st.title("🌱 Plan & Govern yout Scope 3 Journey")
st.subheader("Ottimizzazione degl investimenti")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("⚖️ Pesi Strategici (WHM)")
w_imp = st.sidebar.slider("Peso Riduzione CO2", 0.01, 1.0, 0.4)
w_cost = st.sidebar.slider("Peso Efficienza Costo", 0.01, 1.0, 0.4)
w_diff = st.sidebar.slider("Peso Facilità Tecnica", 0.01, 1.0, 0.2)

st.sidebar.header("🎯 Obiettivi e Budget")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_annuo = st.sidebar.number_input("Budget Annuo (€)", value=1000000, step=50000)
anno_target = st.sidebar.select_slider("Orizzonte Temporale Target", options=[2026, 2027, 2028, 2029, 2030, 2035], value=2030)

st.sidebar.header("⏳ Dinamiche Temporali")
churn_rate = st.sidebar.slider("Tasso abbandono (%)", 0, 50, 10)
perdita_carb = st.sidebar.slider("Decadimento SOC-Stock (%)", 0, 100, 40) 
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
    res = (series.max() - series)/(series.max() - series.min()) if invert else (series - series.min())/(series.max() - series.min())
    return res.clip(lower=0.01) 

df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))
df_p['S_Imp'] = safe_norm(df_p['Imp_Val'])
df_p['S_Cost'] = safe_norm(df_p['costo'], invert=True)
df_p['S_Diff'] = safe_norm(df_p['diff'], invert=True)

# --- LOGICA WHM ---
sum_w = w_imp + w_cost + w_diff
df_p['Score'] = sum_w / ( (w_imp / df_p['S_Imp']) + (w_cost / df_p['S_Cost']) + (w_diff / df_p['S_Diff']) )

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

# --- TRAIETTORIA ---
anni = list(range(2025, anno_target + 1))
rit_c, rit_h = (100 - perdita_carb)/100, (100 - churn_rate)/100
traiettoria = []
stock = 0
beneficio_nuovo = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())

for anno in anni:
    if anno == 2025:
        traiettoria.append(BASELINE_TOT_ANNUA)
    else:
        stock = (stock * rit_c * rit_h) + beneficio_nuovo
        traiettoria.append(BASELINE_TOT_ANNUA - stock)

# --- LOGICA KPI GAP (ROSSO/VERDE) ---
emissione_finale = traiettoria[-1]
soglia_limite_target = BASELINE_TOT_ANNUA - target_ton_annuo
gap_residuo = emissione_finale - soglia_limite_target

# Invertiamo la logica: gap positivo (male) -> rosso | gap negativo (bene) -> verde
# Streamlit metric con delta_color='inverse':
# Se delta è POSITIVO (+) -> Rosso
# Se delta è NEGATIVO (-) -> Verde
color_mode = "inverse" 

# --- BOX KPI ---
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ettari Programma", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric(f"CO2 Abbattuta {anno_target}", f"{int(stock)} t")
c3.metric("€/t Medio Pesato", f"{( (budget_annuo-budget_residuo)/beneficio_nuovo if beneficio_nuovo>0 else 0):.2f} €")
c4.metric("Budget Residuo", f"€ {int(budget_residuo):,}")

# Box 5: Gap al Target
c5.metric(
    label="Gap al Target (tCO2)", 
    value=f"{int(gap_residuo)} t", 
    delta="SOPRA TARGET" if gap_residuo > 0 else "SOTTO TARGET",
    delta_color=color_mode
)

st.markdown("---")
l, r = st.columns([1.5, 1])

with l:
    st.subheader(f"📅 Traiettoria Emissioni Scope 3 FLAG")
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria, mode='lines+markers', line=dict(color='green', width=4), name="Emissione Netta"))
    fig_line.add_trace(go.Scatter(x=anni, y=[soglia_limite_target]*len(anni), line=dict(dash='dot', color='red'), name="Soglia Target"))
    st.plotly_chart(fig_line, use_container_width=True)

with r:
    st.subheader("📊 Mix Pratiche Ottimizzato")
    labels = [p for p, ha in ettari_allocati.items() if ha > 0.1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0.1]
    st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)

st.write("### 🚜 Piano Operativo Suggerito (ha/anno)")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ettari_allocati.items() if ha > 0}, orient='index', columns=['Ettari']))
