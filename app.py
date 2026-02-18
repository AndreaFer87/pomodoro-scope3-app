import streamlit as st
import pandas as pd

# Titolo e intestazione
st.set_page_config(page_title="Pomodoro Carbon Plan", layout="wide")
st.title("🍅 Dashboard Decarbonizzazione Scope 3 - Pomodoro")
st.markdown("---")

# --- DATI DI INPUT FISSI (TUOI DATI) ---
vol_tot = 800000
resa_media = 80
superficie_tot = 10000
target_percent = 27
budget_max = 1000000

# Parametri sicurezza
incertezza = 0.15
buffer_perm = 0.20
churn_rate = 0.15

# --- LOGICA DELLE PRATICHE ---
# Delta Emissioni e Delta Carbonio (Rispetto alla baseline)
pratiche_dict = {
    "Cover Crops": {"d_emiss": 0.2, "d_carb": 1.6, "costo": 300, "diff": 3},
    "Interramento Residui": {"d_emiss": 0.5, "d_carb": 2.7, "costo": 400, "diff": 1},
    "Minima Lavorazione": {"d_emiss": -0.5, "d_carb": 0.86, "costo": 400, "diff": 1},
    "C.C. + Interramento": {"d_emiss": 0.5, "d_carb": 3.8, "costo": 700, "diff": 4},
    "C.C. + Minima Lav.": {"d_emiss": -0.2, "d_carb": 1.96, "costo": 500, "diff": 5},
    "Int. + Minima Lav.": {"d_emiss": -0.2, "d_carb": 3.4, "costo": 400, "diff": 5},
    "Tripletta (Tutte)": {"d_emiss": 0.2, "d_carb": 4.17, "costo": 800, "diff": 5},
}

# --- SIDEBAR PER SIMULAZIONE ---
st.sidebar.header("Parametri di Simulazione")
scelta = st.sidebar.selectbox("Seleziona Pratica Dominante", list(pratiche_dict.keys()))
incentivo_percent = st.sidebar.slider("Percentuale Costo Coperto (%)", 0, 100, 75)

# --- CALCOLI ---
p = pratiche_dict[scelta]
# Impatto Netto Ha = (Delta Carb - Delta Emiss) * Sicurezza
impatto_netto_ha = (p["d_carb"] - p["d_emiss"]) * (1 - incertezza) * (1 - buffer_perm)
costo_incentivo_ha = p["costo"] * (incentivo_percent / 100)

# Baseline Totale (4.5 t/ha * 10.000 ha)
baseline_tot = superficie_tot * 4.5
obiettivo_abbattimento = baseline_tot * (target_percent / 100)

# Ettari necessari
ettari_necessari = obiettivo_abbattimento / impatto_netto_ha
costo_totale = ettari_necessari * costo_incentivo_ha

# --- VISUALIZZAZIONE KPI ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Target da Abbattere", f"{obiettivo_abbattimento:,.0f} t CO2e")
with col2:
    st.metric("Ettari Necessari", f"{int(ettari_necessari)} ha", delta=f"{(ettari_necessari/superficie_tot)*100:.1f}% filiera")
with col3:
    col3.metric("Costo Totale Stimato", f"{costo_totale:,.0f} €", delta=f"{budget_max - costo_totale:,.0f} € vs Budget", delta_color="normal")

# Grafico semplice
st.subheader("Evoluzione Decarbonizzazione")
st.bar_chart(pd.DataFrame({"Baseline": [baseline_tot], "Dopo Intervento": [baseline_tot - obiettivo_abbattimento]}))

st.info(f"Nota: Il calcolo include un Buffer di Non-Permanenza del {buffer_perm*100}% e un'Incertezza Modello del {incertezza*100}%.")
