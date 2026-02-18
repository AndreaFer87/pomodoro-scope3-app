import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Agri-E-MRV | Resa & Attrattività", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Ottimizzazione MCDA: Il peso della Resa (Res) sull'Adozione")
st.markdown("---")

# --- SIDEBAR: PARAMETRI DI STRATEGIA ---
st.sidebar.header("🎯 Obiettivi Generali")
target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Massimo (€)", value=1000000, step=50000)

st.sidebar.header("⚖️ Logica MCDA")
alpha = st.sidebar.slider(
    "α - Avversione alla Complessità", 
    0.5, 4.0, 1.5, 0.1,
    help="Peso della difficoltà tecnica nel calcolo della priorità."
)

# Questo slider decide quanto la RESA (Res) attenua la difficoltà
peso_resa = st.sidebar.slider(
    "Importanza Resa per Agricoltore", 
    1.0, 5.0, 3.0, 0.1,
    help="Se alto, le pratiche con Res 5 diventano molto più prioritarie anche se difficili."
)

st.sidebar.header("🛡️ Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (%)", 0, 40, 12)

# --- DATABASE PRATICHE (Valori originali ripristinati) ---
# Res = Resa/Mantenimento: più è alto, più l'agricoltore è invogliato
data = {
    'Cover Crops':          {'c': 250, 'd': 2, 'res': 4, 'd_emiss': 0.2,  'd_carb': 1.1},
    'Interramento':         {'c': 200, 'd': 1, 'res': 5, 'd_emiss': 0.3,  'd_carb': 2.0},
    'Minima Lav.':          {'c': 250, 'd': 1, 'res': 4, 'd_emiss': -0.7, 'd_carb': 0.36},
    'C.C. + Interramento':  {'c': 450, 'd': 4, 'res': 4, 'd_emiss': 0.5,  'd_carb': 3.0},
    'C.C. + Minima Lav.':   {'c': 350, 'd': 3, 'res': 5, 'd_emiss': -0.5, 'd_carb': 1.46},
    'Int. + Minima Lav.':   {'c': 450, 'd': 3, 'res': 4, 'd_emiss': -0.4, 'd_carb': 2.7},
    'Tripletta':            {'c': 800, 'd': 5, 'res': 3, 'd_emiss': 0.2,  'd_carb': 3.5}
}

# --- CONTROLLO SINGOLE PRATICHE (Slider Box) ---
st.sidebar.header("⚙️ Configurazione Pratiche")
conf = {}
for p, v in data.items():
    with st.sidebar.expander(f"Parametri {p}"):
        conf[p] = {
            'costo': st.number_input(f"Incentivo €/ha ({p})", 0, 1500, v['c']),
            'diff': st.slider(f"Difficoltà ({p})", 1.0, 5.0, float(v['d'])),
            'res': st.slider(f"Fattore Resa/Res ({p})", 1, 5, v['res'])
        }

# --- CALCOLO INDICATORI ---
df_p = pd.DataFrame(data).T
for p in data.keys():
    df_p.at[p, 'costo'] = conf[p]['costo']
    df_p.at[p, 'diff'] = conf[p]['diff']
    df_p.at[p, 'res'] = conf[p]['res']
    # Impatto Netto CO2
    df_p.at[p, 'Imp_Netto'] = ((-df_p.at[p, 'd_emiss'] + df_p.at[p, 'd_carb'] + 0.5) * (1 - safety_buffer/100))

# --- NUOVA FORMULA MCDA ---
# Lo Score ora premia la Resa (Attrattività per l'agricoltore)
# Score = (Impatto * Res^Peso_Resa) / (Costo * Difficoltà^Alpha)
df_p['Score'] = (df_p['Imp_Netto'] * (df_p['res']**peso_resa)) / (df_p['costo'] * (df_p['diff']**alpha))

# --- ALLOCAZIONE ---
ETTARI_FILIERA = 10000
BASELINE_TOT = 40000 
target_ton = BASELINE_TOT * (target_decarb / 100)
budget_restante = budget_max
ettari_allocati = {p: 0.0 for p in df_p.index}

df_sorted = df_p.sort_values(by='Score', ascending=False)

for nome, row in df_sorted.iterrows():
    attuale = sum(ettari_allocati[pr] * df_p.at[pr, 'Imp_Netto'] for pr in df_p.index)
    if attuale >= target_ton or budget_restante <= 0: break
    
    # Se la resa è alta (Res 5), l'agricoltore è più facile da ingaggiare -> cap operativo più alto
    cap_op = (ETTARI_FILIERA / (row['diff']**(alpha/2))) * (row['res']/3)
    
    ha_mancanti = (target_ton - attuale) / row['Imp_Netto']
    ha_finanz = budget_restante / row['costo']
    ha_fisici = ETTARI_FILIERA - sum(ettari_allocati.values())
    
    da_aggiungere = max(0, min(ha_mancanti, ha_finanz, cap_op, ha_fisici))
    ettari_allocati[nome] += da_aggiungere
    budget_restante -= da_aggiungere * row['costo']

# --- VISUALIZZAZIONE ---
c1, c2, c3, c4 = st.columns(4)
abb_finale = sum(ettari_allocati[p] * df_p.at[p, 'Imp_Netto'] for p in df_p.index)
c1.metric("Superficie Totale", f"{int(sum(ettari_allocati.values()))} ha")
c2.metric("CO2 Abbattuta", f"{int(abb_finale)} t")
c3.metric("Budget Residuo", f"€ {int(budget_restante):,}")
c4.metric("Efficienza Media", f"{round(abb_finale/max(1, sum(ettari_allocati.values())), 2)} t/ha")

st.markdown("---")
l, r = st.columns([1.5, 1])

with l:
    st.subheader("📊 Portfolio Mix (Influenzato da Resa & Difficoltà)")
    lbls = [k for k,v in ettari_allocati.items() if v > 0]
    vals = [v for v in ettari_allocati.values() if v > 0]
    if vals:
        st.plotly_chart(go.Figure(data=[go.Pie(labels=lbls, values=vals, hole=.4)]), use_container_width=True)

with r:
    st.subheader("📈 Top Pratiche per Attrattività")
    # Mostriamo come la resa spinge le pratiche
    for p, h in ettari_allocati.items():
        if h > 0:
            st.write(f"**{p}**")
            st.caption(f"Res: {conf[p]['res']} | Diff: {conf[p]['diff']} | Ettari: {int(h)}")
            st.progress(min(1.0, df_p.at[p, 'Score'] / df_p['Score'].max()))

st.success("💡 **Logica Attuale:** Se aumenti 'Importanza Resa', vedrai che l'Interramento (Res 5) e la Combo C.C.+Minima Lav (Res 5) dominano il mix, perché l'agricoltore le accetta più volentieri nonostante i costi.")
