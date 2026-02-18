import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Dashboard 2030", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Modello Strategico: MCDA Standardizzato, Churn Rate e Carbon Decay")
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
churn_rate = st.sidebar.slider("Churn Rate (%)", 0, 50, 10, help="Ettari che abbandonano le pratiche ogni anno")
perdita_carb = st.sidebar.slider("Decadimento C-Stock (%)", 0, 100, 70, help="Perdita annua del carbonio sequestrato nel suolo")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 5, 40, 20)
prob_minima = st.sidebar.slider("Adozione Spontanea (%)", 0, 25, 10)

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

# --- STANDARDIZZAZIONE E SCORE ---
def safe_norm(series, invert=False):
    if series.max() == series.min(): return series * 0.0 + 0.5
    if invert:
        return (series.max() - series) / (series.max() - series.min())
    return (series - series.min()) / (series.max() - series.min())

# Impatto Netto depurato dal rischio
df_p['Imp_Val'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))

# Standardizzazione componenti per rendere i pesi efficaci
df_p['S_Imp'] = safe_norm(df_p['Imp_Val'])
df_p['S_Cost'] = safe_norm(df_p['costo'], invert=True)
df_p['S_Diff'] = safe_norm(df_p['diff'], invert=True)

# Calcolo Score Finale (MCDA) - Somma pesata
df_p['Score'] = (df_p['S_Imp'] * w_imp) + (df_p['S_Cost'] * w_cost) + (df_p['S_Diff'] * w_diff)

# --- ALLOCAZIONE ANNUALE ---
ettari_allocati = {p: 0.0 for p in df_p.index}
pratiche_facili = df_p[df_p['diff'] < 3].index
if not pratiche_facili.empty:
    ha_base = (ETTARI_FILIERA * (prob_minima/100)) / len(pratiche_facili)
    for p in pratiche_facili: ettari_allocati[p] = ha_base

target_ton_annuo = BASELINE_TOT_ANNUA * (target_decarb/100)
budget_residuo = budget_annuo - sum(ha * df_p.at[p, 'costo'] for p, ha in ettari_allocati.items())

# Allocazione basata su Score decrescente
for nome, row in df_p.sort_values(by='Score', ascending=False).iterrows():
    abb_attuale = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    if abb_attuale >= target_ton_annuo or budget_residuo <= 0: break
    da_agg = min((target_ton_annuo - abb_attuale) / row['Imp_Val'], budget_residuo / row['costo'], ETTARI_FILIERA - sum(ettari_allocati.values()))
    if da_agg > 0:
        ettari_allocati[nome] += da_agg
        budget_residuo -= da_agg * row['costo']

# --- MOTORE TEMPORALE 2026-2030 (COORTI, CHURN E DECADIMENTO) ---
anni = [2026, 2027, 2028, 2029, 2030]
ritenzione_carb = (100 - perdita_carb) / 100
ritenzione_ha = (100 - churn_rate) / 100

traiettoria_emissioni = []
stock_accumulato = 0
ettari_attivi = sum(ettari_allocati.values())

for i, anno in enumerate(anni):
    # 1. Il beneficio delle nuove pratiche dell'anno corrente
    beneficio_nuovo = sum(ha * df_p.at[p, 'Imp_Val'] for p, ha in ettari_allocati.items())
    
    # 2. Il beneficio degli anni passati decade (Carbon Decay) e diminuisce (Churn Rate)
    # Applichiamo entrambi i fattori allo stock accumulato
    stock_accumulato = (stock_accumulato * ritenzione_carb * ritenzione_ha) + beneficio_nuovo
    
    traiettoria_emissioni.append(BASELINE_TOT_ANNUA - stock_accumulato)

# --- KPI BOX ---
costo_tot = budget_annuo - budget_residuo
eur_ton_medio = costo_tot / beneficio_nuovo if beneficio_nuovo > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ettari Totali", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("Abbattimento 2030", f"{int(stock_accumulato)} t")
c3.metric("€/t Medio (Nuovo)", f"{eur_ton_medio:.2f} €")
c4.metric("Budget Residuo", f"€ {int(budget_residuo):,}")
c5.metric("Gap Target (2030)", f"{int(max(0, (BASELINE_TOT_ANNUA - target_ton_annuo) - traiettoria_emissioni[-1]))} t")

st.markdown("---")

# --- GRAFICI ---
l, r = st.columns([1.5, 1])

with l:
    st.subheader("📅 Traiettoria Emissioni con Churn e Decadimento")
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=anni, y=traiettoria_emissioni, mode='lines+markers+text', 
                                 text=[f"{int(v)}t" for v in traiettoria_emissioni], textposition="top center",
                                 line=dict(color='green', width=4), name="Emissione Netta"))
    fig_line.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT_ANNUA - target_ton_annuo]*5, 
                                 name="Target Decarb.", line=dict(dash='dot', color='red')))
    fig_line.update_layout(yaxis_title="t CO2e")
    st.plotly_chart(fig_line, use_container_width=True)

with r:
    st.subheader("📊 Portfolio Mix Ettari (Anno Corrente)")
    labels = [p for p, ha in ettari_allocati.items() if ha > 1]
    values = [ha for p, ha in ettari_allocati.items() if ha > 1]
    if values:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)]), use_container_width=True)
    else:
        st.warning("Nessuna pratica finanziata con questo budget.")

# --- WATERFALL ---
st.subheader("📉 Waterfall: Impatto Singola Annualità")
v_input = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
v_soc = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    orientation = "v",
    x = ["Baseline", "Input (Emissioni)", "SOC (Sequestro)", "Netto Anno"],
    y = [BASELINE_TOT_ANNUA, v_input, -v_soc, 0],
    measure = ["absolute", "relative", "relative", "total"]
))
st.plotly_chart(fig_wf, use_container_width=True)

st.write("### 🚜 Piano Operativo Suggerito (ha/anno)")
st.table(pd.DataFrame.from_dict({p: f"{int(ha)} ha" for p, ha in ettari_allocati.items() if ha > 0}, orient='index', columns=['Ettari']))
