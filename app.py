from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(page_title="Électricité dans 12 quartiers", layout="wide")
st.title("Électricité dans 12 quartiers")
st.write(
"Relevés de janvier 2024 à décembre 2025 pour 12 quartiers de "
"Port-au-Prince, Delmas, Pétion-Ville et Cap-Haïtien."
)
st.write(
"Question du directeur : la consommation suit-elle la chaleur, "
"ou les heures de courant ?"
)


@st.cache_data
def charger():
    df = pd.read_csv("donnees/consommation_propre.csv")
    df["mois"] = pd.to_datetime(df["mois"])
    return df


df = charger()

# 3. Filtres
communes = sorted(df["commune"].unique())
choix = st.sidebar.multiselect("Communes", communes, default=communes)
annees = sorted(df["annee"].unique())
annee = st.sidebar.selectbox("Année", annees, index=annees.index(2025))

if not choix:
    st.warning("Choisissez au moins une commune.")
    st.stop()

dc = df[df["commune"].isin(choix)] # communes choisies, toutes années
d = dc[dc["annee"] == annee] # communes + année choisies

# 4. Indicateurs
c1, c2, c3 = st.columns(3)
c1.metric("Consommation totale", f"{d['kwh'].sum() / 1e6:.2f} millions de kWh")
c2.metric("kWh par abonné", f"{d['kwh_par_abonne'].mean():.1f}")
c3.metric("Heures de courant par jour", f"{d['heures_courant'].mean():.1f}")

# 5. Onglets : un par question
t1, t2, t3, t4, t5 = st.tabs([
"Par abonné",
"Évolution",
"Chaleur ou courant ?",
"Coupures",
"Relevés extrêmes",
])

with t1:
    st.subheader("Quels quartiers consomment le plus par abonné ?")
    classement = (
    d.groupby("quartier")["kwh_par_abonne"].mean().round(1)
    .sort_values(ascending=False)
    )
    st.bar_chart(classement)
    par_type = d.groupby("type")["kwh_par_abonne"].mean().round(1)
    texte = " ; ".join(f"{t} {v}" for t, v in par_type.items())
    st.write(
    f"Moyenne par abonné selon le type : {texte}. "
    f"En tête : {classement.index[0]} ({classement.iloc[0]})."
    )

with t2:
    st.subheader("Comment la consommation évolue-t-elle, commune par commune ?")
    courbes = dc.pivot_table(
    index="mois", columns="commune", values="kwh_par_abonne", aggfunc="mean"
    )
    st.line_chart(courbes)
    tableau = dc.pivot_table(
    index="commune", columns="annee", values="kwh", aggfunc="sum"
    )
    if 2024 in tableau.columns and 2025 in tableau.columns:
        hausse = ((tableau[2025] / tableau[2024] - 1) * 100).sort_values(
        ascending=False
        )
    st.write(
    f"Plus forte hausse 2024 → 2025 : {hausse.index[0]} "
    f"(+{hausse.iloc[0]:.1f} %). "
    f"Plus faible : {hausse.index[-1]} ({hausse.iloc[-1]:+.1f} %)."
    )

with t3:
    st.subheader("La consommation suit-elle la chaleur, ou les heures de courant ?")
    res = dc[dc["type"] == "Résidentiel"]
    if len(res) > 2:
        st.scatter_chart(res, x="heures_courant", y="kwh_par_abonne")
        r_courant = res["kwh_par_abonne"].corr(res["heures_courant"])
        r_chaleur = res["kwh_par_abonne"].corr(res["temperature_c"])
        st.write(
        f"Quartiers résidentiels (2024-2025) : corrélation de {r_courant:.2f} avec les "
        f"heures de courant, et de {r_chaleur:.2f} avec la température."
        )
    else:
        st.info("Pas assez de quartiers résidentiels pour calculer une corrélation.")

with t4:
    st.subheader("Où les coupures sont-elles les plus longues ?")
    mediane = dc.groupby("commune")["heures_courant"].median().round(1)
    st.bar_chart(mediane)
    faibles = d[d["heures_courant"] < 8]
    st.write(
    f"Médiane la plus basse (2024-2025) : {mediane.idxmin()} "
    f"({mediane.min()} h par jour). "
    f"Relevés sous 8 heures de courant en {annee} : {len(faibles)}."
    )
    if len(faibles):
        tab = faibles[["mois", "quartier", "heures_courant"]].copy()
        tab["mois"] = tab["mois"].dt.strftime("%Y-%m")
        st.dataframe(tab, hide_index=True)

with t5:
    st.subheader("Quels relevés sortent du lot ?")
    top = d.nlargest(3, "kwh")[["mois", "quartier", "type", "kwh", "heures_courant"]]
    st.dataframe(top, hide_index=True)
    if len(top):
        premier = top.iloc[0]
    st.write(
    f"Plus forte consommation : {premier['quartier']} en "
    f"{premier['mois']:%Y-%m} ({premier['kwh']:,.0f} kWh, "
    f"{premier['heures_courant']:.1f} heures de courant par jour)."
    )

# 6. Conclusion + données
st.markdown("## Conclusion")
st.markdown(
"La consommation suit les heures de courant, pas la chaleur : dans les "
"quartiers résidentiels, la corrélation avec les heures de courant est de "
"0.76, contre -0.15 avec la température. Autrement dit, les ménages "
"consomment surtout quand le courant est disponible. Attention : une "
"corrélation ne prouve pas qu'une variable est la cause de l'autre, et elle "
"ne dit rien des quartiers commerciaux."
)
with st.expander("Données filtrées"):
    st.dataframe(d)