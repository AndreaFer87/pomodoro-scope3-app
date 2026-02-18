import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="Agri-E-MRV | Strategia Filiera", layout="wide")

st.title("🌱 Plan & Govern Scope 3: Agri-E-MRV")
st.subheader("Simulatore Dinamico: Surface Minimization & Fattibilità Tecnica")
st.markdown("---")

# --- SIDEBAR: LEVE DI GOVERNANCE ---
st.sidebar.header("🕹️ Pannello di Controllo")

target_decarb = st.sidebar.slider("Target Decarbonizzazione (%)", 10, 50, 27)
budget_max = st.sidebar.number_input("Budget Annuo Disponibile (€)", value=1000000)
orizzonte_anno = st.sidebar.select_slider("Orizzonte Target", options=[2026, 2027, 2028, 2029, 2030, 2035])

st.sidebar.subheader("🛡️ Gestione del Rischio")
safety_buffer = st.sidebar.slider("Safety Buffer (Rischio Permanenza %)", 5, 40, 20)
churn_rate = st.sidebar.slider("Churn Rate Annuo (%)", 0, 20, 10, help="Percentuale di agricoltori che abbandonano ogni anno")

# --- DATI FISSI FILIERA ---
VOL_TOT_TON = 800000
ETTARI_FILIERA = 10000
EMISSIONI_BASE_HA = 4.0   # t CO2e/ha
LOSS_SOC_BASE_HA = 0.5    # t CO2e/ha perdita naturale
BASELINE_TOT = ETTARI_FILIERA * (EMISSIONI_BASE_HA + LOSS_SOC_BASE_HA)
EF_BASE_KG_TON = (BASELINE_TOT / VOL_TOT_TON) * 1000

# --- DATABASE PRATICHE CON INPUT UTENTE ---
st.sidebar.header("⚙️ Configurazione Pratiche")
# d_emiss: variazione input, d_carb: sequestro, costo: eur/ha, diff: 1-5, res: resa 1-5
pratiche_base = {
    'Cover Crops':          {'d_emiss': 0.2,  'd_carb': 1.1, 'costo': 250, 'diff': 2, 'res': 4},
    'Interramento':         {'costo': 200, 'diff': 1, 'res': 5, 'd_emiss': 0.3,  'd_carb': 2.0},
    'Minima Lav.':          {'costo': 250, 'diff': 1, 'res': 4, 'd_emiss': -0.7, 'd_carb': 0.36},
    'C.C. + Interramento':  {'costo': 450, 'diff': 4, 'res': 4, 'd_emiss': 0.5,  'd_carb': 3.0},
    'C.C. + Minima Lav.':   {'costo': 350, 'diff': 3, 'res': 5, 'd_emiss': -0.5, 'd_carb': 1.46},
    'Int. + Minima Lav.':   {'costo': 450, 'diff': 3, 'res': 4, 'd_emiss': -0.4, 'd_carb': 2.7},
    'Tripletta':            {'costo': 800, 'diff': 5, 'res': 3, 'd_emiss': 0.2,  'd_carb': 3.5}
}

# Raccolta modifiche da sidebar
conf_pratiche = {}
for p, v in pratiche_base.items():
    with st.sidebar.expander(f"Parametri {p}"):
        c = st.number_input(f"Eur/ha {p}", 0, 1500, v['costo'])
        d = st.slider(f"Difficoltà {p}", 1, 5, v['diff'])
        r = st.slider(f"Resa (Res) {p}", 1, 5, v['res'])
        conf_pratiche[p] = {'costo': c, 'diff': d, 'res': r, 'd_emiss': v['d_emiss'], 'd_carb': v['d_carb']}

df_p = pd.DataFrame(conf_pratiche).T

# --- CALCOLO IMPATTO E SCORE ---
# Impatto Netto = (Risparmio Input + Carbonio + Stop Perdita) * Buffer
df_p['Impatto_Netto_Ha'] = ((-df_p['d_emiss'] + df_p['d_carb'] + LOSS_SOC_BASE_HA) * (1 - safety_buffer/100))

# Score di priorità: Cerchiamo alto impatto, basso costo, bassa difficoltà e alta resa
# Semplificato: Impatto / (Costo * Difficoltà) * Res
df_p['Score_Ottimizzazione'] = (df_p['Impatto_Netto_Ha'] / (df_p['costo'] * df_p['diff'])) * df_p['res']

# --- MOTORE DI ALLOCAZIONE (ROI-DRIVEN SURFACE MINIMIZATION) ---
target_ton_tot = BASELINE_TOT * (target_decarb / 100)
df_sorted = df_p.sort_values(by='Score_Ottimizzazione', ascending=False)

ettari_allocati = {p: 0.0 for p in df_p.index}
abbattimento_progressivo = 0
budget_residuo = budget_max

for nome, row in df_sorted.iterrows():
    if abbattimento_progressivo >= target_ton_tot or budget_residuo <= 0:
        break
    
    # Quanti ettari servirebbero di questa pratica per chiudere il gap?
    gap_rimanente = target_ton_tot - abbattimento_progressivo
    ha_necessari = gap_rimanente / row['Impatto_Netto_Ha']
    
    # Limiti: non più degli ettari totali e non più del budget
    ha_finanziabili = budget_residuo / row['costo']
    ha_fisici_disponibili = ETTARI_FILIERA - sum(ettari_allocati.values())
    
    da_allocare = min(ha_necessari, ha_finanziabili, ha_fisici_disponibili)
    
    ettari_allocati[nome] = da_allocare
    abbattimento_progressivo += da_allocare * row['Impatto_Netto_Ha']
    budget_residuo -= da_allocare * row['costo']

# --- KPI DI SINTESI ---
abb_effettivo = sum(ha * df_p.at[p, 'Impatto_Netto_Ha'] for p, ha in ettari_allocati.items())
ef_target = ((BASELINE_TOT - abb_effettivo) / VOL_TOT_TON) * 1000

c1, c2, c3, c4 = st.columns(4)
c1.metric("EF Finale Target", f"{ef_target:.1f} kg/t", f"Base: {EF_BASE_KG_TON:.1f}")
c2.metric("Superficie Totale", f"{int(sum(ettari_allocati.values()))} ha", f"{(sum(ettari_allocati.values())/ETTARI_FILIERA)*100:.1f}% filiera")
c3.metric("Budget Utilizzato", f"€ {int(budget_max - budget_residuo):,}")
c4.metric("Gap al Target", f"{int(max(0, target_ton_tot - abb_effettivo))} tCO2")

st.markdown("---")

# --- GRAFICI ---

col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📅 Traiettoria Temporale con Carry-over e Churn")
    anni = np.arange(2025, orizzonte_anno + 1)
    n_anni = len(anni)
    
    # Simulazione dinamica
    history_nette = []
    current_abb = 0
    for i in range(n_anni):
        # Ogni anno aggiungiamo la quota di nuove pratiche (linearmente fino a regime)
        # e sottraiamo il churn (chi abbandona)
        quota_regime = (i + 1) / n_anni
        potenziale_anno = abb_effettivo * quota_regime
        # Effetto Churn: perdita di efficacia cumulativa
        efficacia_reale = potenziale_anno * (1 - (churn_rate/100))**i
        history_nette.append(BASELINE_TOT - efficacia_reale)
        
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT]*n_anni, name='Baseline', line=dict(dash='dash', color='gray')))
    fig_temp.add_trace(go.Scatter(x=anni, y=history_nette, name='Emissione Netta (Proiezione)', line=dict(color='black', width=4)))
    fig_temp.add_trace(go.Scatter(x=anni, y=[BASELINE_TOT - target_ton_tot]*n_anni, name='Obiettivo', line=dict(dash='dot', color='red')))
    st.plotly_chart(fig_temp, use_container_width=True)

with col_right:
    st.subheader("📊 Mix Pratiche Ottimizzato")
    labels = [p for p, ha in ettari_allocati.items() if ha > 0]
    values = [ha for p, ha in ettari_allocati.items() if ha > 0]
    if values:
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("Nessuna pratica allocata. Verifica budget o target.")

# --- WATERFALL ---
st.subheader("📉 Analisi Variazione Emissioni (A regime)")
# Calcoliamo i contributi medi del mix allocato
mix_d_emiss = sum(ha * df_p.at[p, 'd_emiss'] for p, ha in ettari_allocati.items())
mix_d_carb = sum(ha * (df_p.at[p, 'd_carb'] + LOSS_SOC_BASE_HA) for p, ha in ettari_allocati.items())

fig_wf = go.Figure(go.Waterfall(
    x = ["Baseline", "Variazione Input", "Rimozione CO2 (Soil)", "Risultato Netto"],
    y = [BASELINE_TOT, mix_d_emiss, -mix_d_carb, 0],
    measure = ["absolute", "relative", "relative", "total"],
    connector = {"line":{"color":"rgb(63, 63, 63)"}},
))
st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("---")
st.write("### 🚀 Piano Operativo Dettagliato")
df_piano = pd.DataFrame.from_dict(ettari_allocati, orient='index', columns=['Ettari da Contrattualizzare'])
df_piano = df_piano[df_piano['Ettari da Contrattualizzare'] > 0]
st.table(df_piano.style.format("{:.0f} ha"))
