import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Plan & Govern Scope 3 | Agri-E-MRV", layout="wide")

# --- TITOLO ---
st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Strategia di Decarbonizzazione Dinamica per la Filiera Pomodoro")
st.markdown("---")

# --- SIDEBAR: LE LEVE DI GOVERNANCE (Ripristinate) ---
st.sidebar.header("🕹️ Pannello di Controllo")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
incentivo_percent = st.sidebar.slider("Incentivo (% costo coperto)", 50, 100, 75)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio e Incertezza")
incertezza_tier3 = st.sidebar.slider("Incertezza Modello Tier 3 (%)", 5, 30, 15, help="Errore intrinseco del modello RothC/Liu")
safety_buffer = st.sidebar.slider("Safety Buffer (Rischio Permanenza %)", 5, 40, 20, help="Accantonamento per rischio abbandono agricoltori")

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EMISSIONI_BASE_HA = 4.0
LOSS_SOC_BASE_HA = 0.5
BASELINE_TOT = ETTARI_FILIERA * (EMISSIONI_BASE_HA + LOSS_SOC_BASE_HA)
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000

# --- DATABASE PRATICHE ---
pratiche = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1,  'costo': 300, 'diff': 3, 'res': 7},
    'Interramento':         {'d_emiss': 0.5,  'd_carb': 2.2,  'costo': 400, 'diff': 1, 'res': 6},
    'Minima Lav.':          {'d_emiss': -0.5, 'd_carb': 0.36, 'costo': 400, 'diff': 1, 'res': 8},
    'C.C. + Interramento':  {'d_emiss': 0.5,  'd_carb': 3.3,  'costo': 700, 'diff': 4, 'res': 7},
    'C.C. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 1.46, 'costo': 500, 'diff': 5, 'res': 9},
    'Int. + Minima Lav.':   {'d_emiss': -0.2, 'd_carb': 2.9,  'costo': 400, 'diff': 5, 'res': 8},
    'Tripletta':            {'d_emiss': 0.2,  'd_carb': 3.67, 'costo': 800, 'diff': 5, 'res': 9}
}

df_p = pd.DataFrame(pratiche).T

def calcola_impatto(row):
    risparmio_input = -row['d_emiss']
    sequestro_netto = row['d_carb'] + LOSS_SOC_BASE_HA
    totale_lordo = risparmio_input + sequestro_netto
    return totale_lordo * (1 - incertezza_tier3/100) * (1 - safety_buffer/100)

df_p['Impatto_Netto_Ha'] = df_p.apply(calcola_impatto, axis=1)
df_p['Costo_Ton'] = (df_p['costo'] * (incentivo_percent/100)) / df_p['Impatto_Netto_Ha']

# --- CALCOLO KPI (Area-Weighted) ---
target_ton_tot = BASELINE_TOT * (target_decarb / 100)
# Per i KPI usiamo un mix simulato (40% Tripletta, 30% C.C+Min, 30% Int)
impatto_medio_mix = (df_p.loc['Tripletta','Impatto_Netto_Ha']*0.4 + 
                     df_p.loc['C.C. + Minima Lav.','Impatto_Netto_Ha']*0.3 + 
                     df_p.loc['Interramento','Impatto_Netto_Ha']*0.3)

costo_medio_mix = (df_p.loc['Tripletta','Costo_Ton']*0.4 + 
                   df_p.loc['C.C. + Minima Lav.','Costo_Ton']*0.3 + 
                   df_p.loc['Interramento','Costo_Ton']*0.3)

ettari_anno = min(target_ton_tot / impatto_medio_mix, ETTARI_FILIERA)
ef_target = ((BASELINE_TOT - (ettari_anno * impatto_medio_mix)) / VOL_TOT_TON) * 1000

# --- BOX KPI ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Base vs Target", f"{EF_BASE_KG_TON:.1f} kg/t", f"{ef_target:.1f} kg/t", delta_color="inverse")
c2.metric("Ettari/Anno Target", f"{int(ettari_anno)} ha", f"{(ettari_anno/ETTARI_FILIERA)*100:.1f}% filiera")
c3.metric("Costo Medio (€/t)", f"{costo_medio_mix:.2f} €/t")
c4.metric("Budget Utilizzato", f"{int(ettari_anno * 550 * (incentivo_percent/100)):,} €")

st.markdown("---")

# --- GRAFICI VERTICALI ---
# 1. Waterfall
st.subheader("📉 La strada verso il Net Zero (Analisi annata)")
fig_wf = go.Figure(go.Waterfall(
    x = ["Baseline 2025", "Variazione Input", "Carbon Removal (SOC)", "Emissioni Nette"],
    y = [BASELINE_TOT, -ettari_anno*0.2, -ettari_anno*2.5, 0], # Valori pesati mix
    measure = ["absolute", "relative", "relative", "total"]
))
st.plotly_chart(fig_wf, use_container_width=True)

# 2. Proiezione Temporale
st.subheader("📅 Proiezione Strategica Temporale (Cumulativa)")
anni = np.arange(2025, orizzonte_anno + 1)
n_anni = len(anni)
emiss_lorde = [BASELINE_TOT] * n_anni
assorbimenti = [-(ettari_anno * impatto_medio_mix * (i/n_anni)) for i in range(n_anni)]
emissioni_nette = [a + b for a, b in zip(emiss_lorde, assorbimenti)]

fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(x=anni, y=emiss_lorde, name='Emissioni Lorde', line=dict(color='red')))
fig_temp.add_trace(go.Scatter(x=anni, y=assorbimenti, fill='tozeroy', name='Assorbimenti C', line_color='green'))
fig_temp.add_trace(go.Scatter(x=anni, y=emissioni_nette, name='Emissioni Nette Totali', line=dict(color='black', width=4)))
st.plotly_chart(fig_temp, use_container_width=True)

# 3. Radar
st.subheader("🎯 Bilancio Multidimensionale Pratiche")
fig_radar = go.Figure()
for index, row in df_p.iterrows():
    scores = [row['Impatto_Netto_Ha']*2, 10-(row['Costo_Ton']/10), 6-row['diff'], row['res']]
    fig_radar.add_trace(go.Scatterpolar(r=scores, theta=['Clima', 'Economia', 'Facilità', 'Resilienza'], fill='toself', name=index))
st.plotly_chart(fig_radar, use_container_width=True)

# --- OTTIMIZZATORE GRAFICO ---
st.markdown("---")
if st.button("🚀 CALCOLA MIX OTTIMALE DI PRATICHE"):
    st.subheader("📊 Allocazione Ottimale del Portfolio Pratiche")
    
    labels = ["Tripletta (High Impact)", "C.C. + Minima Lav. (Resilience)", "Interramento (Low Cost)"]
    values = [ettari_anno * 0.4, ettari_anno * 0.3, ettari_anno * 0.3]
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)])
    fig_donut.update_layout(annotations=[dict(text='Mix Ha', x=0.5, y=0.5, font_size=20, showarrow=False)])
    st.plotly_chart(fig_donut)
    
    st.write(f"L'AI suggerisce di distribuire i {int(ettari_anno)} ettari per minimizzare il rischio di mancato sequestro dovuto all'incertezza del {incertezza_tier3}%.")
