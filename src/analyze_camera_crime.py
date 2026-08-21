"""Create the first cross-sectional Smart Sampa × cellphone-crime analysis.

Inputs (versioned, aggregated data only):
- data/processed/subprefeituras_cameras_populacao_area_2025_09.csv
- data/processed/ssp_cellphones_by_subpref_month.csv
- data/processed/ssp_geocoding_quality_month.csv

Outputs:
- data/processed/analytical_subprefeituras_2025.csv
- data/processed/analysis_summary_2025.csv
- data/processed/analysis_quartiles_2025.csv
- reports/figures/cameras_vs_cellphones_percap_2025.svg
- reports/figures/camera_quartiles_vs_cellphones_2025.svg

This stage is descriptive. A September 2025 camera snapshot is not a treatment
history and must not be interpreted as a causal estimate of deterrence.
"""
from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"

CAMERAS = PROCESSED / "subprefeituras_cameras_populacao_area_2025_09.csv"
CRIME = PROCESSED / "ssp_cellphones_by_subpref_month.csv"
QUALITY = PROCESSED / "ssp_geocoding_quality_month.csv"


def norm_key(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text = re.sub(r"[^A-Z0-9]+", " ", text).strip()
    aliases = {"SAO MIGUEL": "SAO MIGUEL PAULISTA"}
    return aliases.get(text, text)


def corr_pair(df: pd.DataFrame, x: str, y: str) -> tuple[float, float]:
    return float(df[[x, y]].corr(method="pearson").iloc[0, 1]), float(df[[x, y]].corr(method="spearman").iloc[0, 1])


def build_analytical_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cameras = pd.read_csv(CAMERAS)
    crime = pd.read_csv(CRIME)
    quality = pd.read_csv(QUALITY)
    cameras["territory_key"] = cameras["subprefeitura"].map(norm_key)
    crime["territory_key"] = crime["subprefeitura_geosampa"].map(norm_key)

    annual = crime.groupby("territory_key", as_index=False).agg(
        celulares_subtraidos_geocod_2025=("subtracoes_total", "sum"),
        roubos_geocod_2025=("roubos", "sum"),
        furtos_geocod_2025=("furtos", "sum"),
    )
    out = cameras.merge(annual, on="territory_key", how="left", validate="one_to_one")
    if out["celulares_subtraidos_geocod_2025"].isna().any():
        missing = out.loc[out["celulares_subtraidos_geocod_2025"].isna(), "subprefeitura"].tolist()
        raise ValueError(f"Subprefeituras sem agregado SSP: {missing}")
    if len(out) != 32:
        raise ValueError(f"Esperadas 32 subprefeituras; obtidas {len(out)}")

    out["bo_rubrica_roubo_e_furto_2025"] = out["roubos_geocod_2025"] + out["furtos_geocod_2025"] - out["celulares_subtraidos_geocod_2025"]
    out["celulares_geocod_por_100_mil_pop2022"] = (out["celulares_subtraidos_geocod_2025"] * 100000 / out["populacao_2022"]).round(2)
    out["roubos_geocod_por_100_mil_pop2022"] = (out["roubos_geocod_2025"] * 100000 / out["populacao_2022"]).round(2)
    out["furtos_geocod_por_100_mil_pop2022"] = (out["furtos_geocod_2025"] * 100000 / out["populacao_2022"]).round(2)
    out["celulares_geocod_por_km2_area2025"] = (out["celulares_subtraidos_geocod_2025"] / out["area_km2"]).round(2)
    out["rank_cameras_percap"] = out["cameras_por_10_mil_hab_pop2022"].rank(ascending=False, method="min").astype(int)
    out["rank_celulares_geocod_percap"] = out["celulares_geocod_por_100_mil_pop2022"].rank(ascending=False, method="min").astype(int)
    out["quartil_cameras_percap"] = pd.qcut(out["cameras_por_10_mil_hab_pop2022"], 4, labels=["Q1_menor", "Q2", "Q3", "Q4_maior"]).astype(str)

    med_cam = out["cameras_por_10_mil_hab_pop2022"].median()
    med_crime = out["celulares_geocod_por_100_mil_pop2022"].median()
    high_cam = out["cameras_por_10_mil_hab_pop2022"] >= med_cam
    high_crime = out["celulares_geocod_por_100_mil_pop2022"] >= med_crime
    out["quadrante_mediana"] = np.select(
        [high_cam & high_crime, high_cam & ~high_crime, ~high_cam & high_crime],
        ["mais_cameras_mais_bos", "mais_cameras_menos_bos", "menos_cameras_mais_bos"],
        default="menos_cameras_menos_bos",
    )

    quartiles = out.groupby("quartil_cameras_percap", observed=True).agg(
        n_subprefeituras=("subprefeitura", "size"),
        cameras_10k_mediana=("cameras_por_10_mil_hab_pop2022", "median"),
        celulares_100k_mediana=("celulares_geocod_por_100_mil_pop2022", "median"),
        roubos_100k_mediana=("roubos_geocod_por_100_mil_pop2022", "median"),
        furtos_100k_mediana=("furtos_geocod_por_100_mil_pop2022", "median"),
    ).reset_index().round(2)

    total_eligible = int(quality["bos_elegiveis"].sum())
    valid_coord = int(quality["bos_coordenada_valida"].sum())
    assigned_sub = int(quality["bos_atribuidos_subprefeitura"].sum())
    assigned_dist = int(quality["bos_atribuidos_distrito"].sum())

    p_rate, s_rate = corr_pair(out, "cameras_por_10_mil_hab_pop2022", "celulares_geocod_por_100_mil_pop2022")
    p_abs, s_abs = corr_pair(out, "cameras_2025_09", "celulares_subtraidos_geocod_2025")
    p_density, s_density = corr_pair(out, "cameras_por_km2_area2025", "celulares_geocod_por_km2_area2025")
    p_rob, s_rob = corr_pair(out, "cameras_por_10_mil_hab_pop2022", "roubos_geocod_por_100_mil_pop2022")
    p_theft, s_theft = corr_pair(out, "cameras_por_10_mil_hab_pop2022", "furtos_geocod_por_100_mil_pop2022")

    sep_dec = crime.loc[crime["mes_ocorrencia"].between(9, 12)].groupby("territory_key", as_index=False).agg(celulares_sep_dec=("subtracoes_total", "sum"))
    sep_dec = cameras[["territory_key", "populacao_2022", "cameras_por_10_mil_hab_pop2022"]].merge(sep_dec, on="territory_key", how="left", validate="one_to_one")
    sep_dec["celulares_sep_dec_100k"] = sep_dec["celulares_sep_dec"] * 100000 / sep_dec["populacao_2022"]
    p_sep_dec, s_sep_dec = corr_pair(sep_dec, "cameras_por_10_mil_hab_pop2022", "celulares_sep_dec_100k")

    sensitivity = out.loc[~out["subprefeitura"].isin(["Sé", "Pinheiros", "Vila Mariana", "Lapa"])].copy()
    p_sens, s_sens = corr_pair(sensitivity, "cameras_por_10_mil_hab_pop2022", "celulares_geocod_por_100_mil_pop2022")

    summary = pd.DataFrame([
        ("subprefeituras", 32), ("cameras_set_2025", int(out["cameras_2025_09"].sum())),
        ("bos_elegiveis_2025", total_eligible), ("bos_com_coordenada_valida_2025", valid_coord),
        ("bos_atribuidos_subprefeitura_2025", assigned_sub), ("bos_atribuidos_distrito_2025", assigned_dist),
        ("pct_bos_com_coord_valida", round(valid_coord * 100 / total_eligible, 2)),
        ("pct_bos_atribuidos_subpref_total", round(assigned_sub * 100 / total_eligible, 2)),
        ("pct_spatial_join_subpref_entre_coords_validas", round(assigned_sub * 100 / valid_coord, 2)),
        ("pearson_cameras10k_celulares100k", round(p_rate, 4)), ("spearman_cameras10k_celulares100k", round(s_rate, 4)),
        ("pearson_cameras_abs_celulares_abs", round(p_abs, 4)), ("spearman_cameras_abs_celulares_abs", round(s_abs, 4)),
        ("pearson_cameras_km2_celulares_km2", round(p_density, 4)), ("spearman_cameras_km2_celulares_km2", round(s_density, 4)),
        ("pearson_cameras10k_roubos100k", round(p_rob, 4)), ("spearman_cameras10k_roubos100k", round(s_rob, 4)),
        ("pearson_cameras10k_furtos100k", round(p_theft, 4)), ("spearman_cameras10k_furtos100k", round(s_theft, 4)),
        ("pearson_cameras10k_celulares100k_sep_dec", round(p_sep_dec, 4)), ("spearman_cameras10k_celulares100k_sep_dec", round(s_sep_dec, 4)),
        ("pearson_sensibilidade_sem_se_pinheiros_vmariana_lapa", round(p_sens, 4)), ("spearman_sensibilidade_sem_se_pinheiros_vmariana_lapa", round(s_sens, 4)),
        ("bos_com_rubrica_roubo_e_furto_geocod", int(out["bo_rubrica_roubo_e_furto_2025"].sum())),
    ], columns=["metrica", "valor"])

    keep = ["subprefeitura", "regiao_administrativa", "populacao_2022", "area_km2", "cameras_2025_09", "cameras_por_10_mil_hab_pop2022", "cameras_por_km2_area2025", "celulares_subtraidos_geocod_2025", "roubos_geocod_2025", "furtos_geocod_2025", "bo_rubrica_roubo_e_furto_2025", "celulares_geocod_por_100_mil_pop2022", "roubos_geocod_por_100_mil_pop2022", "furtos_geocod_por_100_mil_pop2022", "celulares_geocod_por_km2_area2025", "rank_cameras_percap", "rank_celulares_geocod_percap", "quartil_cameras_percap", "quadrante_mediana"]
    return out[keep].sort_values("rank_cameras_percap"), summary, quartiles


def make_figures(df: pd.DataFrame, quartiles: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    x = df["cameras_por_10_mil_hab_pop2022"]
    y = df["celulares_geocod_por_100_mil_pop2022"]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(x, y, alpha=0.78)
    slope, intercept = np.polyfit(x, y, 1)
    xx = np.linspace(x.min(), x.max(), 100)
    ax.plot(xx, slope * xx + intercept, linewidth=1.5)
    ax.axvline(x.median(), linestyle="--", linewidth=0.8)
    ax.axhline(y.median(), linestyle="--", linewidth=0.8)
    for row in df.loc[df["subprefeitura"].isin({"Sé", "Pinheiros", "Mooca", "Lapa", "Vila Mariana", "Cidade Tiradentes"})].itertuples():
        ax.annotate(row.subprefeitura, (row.cameras_por_10_mil_hab_pop2022, row.celulares_geocod_por_100_mil_pop2022), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_title("Smart Sampa × BOs geocodificados de roubo/furto de celular — 2025")
    ax.set_xlabel("Câmeras por 10 mil habitantes (câmeras: set/2025; população: Censo 2022)")
    ax.set_ylabel("BOs geocodificados por 100 mil habitantes (2025)")
    ax.text(0.01, 0.01, "Associação espacial descritiva; não estima efeito causal das câmeras.", transform=ax.transAxes, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "cameras_vs_cellphones_percap_2025.svg", format="svg")
    plt.close(fig)

    order = ["Q1_menor", "Q2", "Q3", "Q4_maior"]
    q = quartiles.set_index("quartil_cameras_percap").loc[order]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(order, q["celulares_100k_mediana"])
    ax.set_title("Mediana de BOs geocodificados por quartil de cobertura de câmeras")
    ax.set_xlabel("Quartil de câmeras por 10 mil habitantes")
    ax.set_ylabel("Mediana de BOs geocodificados por 100 mil habitantes")
    for bar, value in zip(bars, q["celulares_100k_mediana"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.0f}", ha="center", va="bottom", fontsize=9)
    ax.text(0.01, 0.01, "Comparação transversal; não mede deterrência nem eficácia do programa.", transform=ax.transAxes, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "camera_quartiles_vs_cellphones_2025.svg", format="svg")
    plt.close(fig)


def main() -> None:
    analytical, summary, quartiles = build_analytical_dataset()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    analytical.to_csv(PROCESSED / "analytical_subprefeituras_2025.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(PROCESSED / "analysis_summary_2025.csv", index=False, encoding="utf-8-sig")
    quartiles.to_csv(PROCESSED / "analysis_quartiles_2025.csv", index=False, encoding="utf-8-sig")
    make_figures(analytical, quartiles)
    print(f"Analytical rows: {len(analytical)}")
    for row in summary.itertuples(index=False):
        print(f"{row.metrica}: {row.valor}")


if __name__ == "__main__":
    main()
