"""Rebuild the project's SQLite database from versioned CSV files.

Run from the repository root:
    python src/build_database.py

Crime aggregates are optional: when the SSP+GeoSampa workflow has generated
versioned monthly CSVs in data/processed, they are loaded automatically.
"""
from pathlib import Path
import re
import sqlite3
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB = ROOT / "database" / "smart_sampa.sqlite"
SCHEMA = ROOT / "database" / "schema.sql"

# GeoSampa and the camera/publication table use different punctuation in some
# administrative names (e.g. hyphens versus slashes). Canonicalization removes
# punctuation first; only genuine naming differences remain as explicit aliases.
SUBPREF_ALIASES = {
    "SAO MIGUEL": "SAO MIGUEL PAULISTA",
    "CASA VERDE CACHOEIRINHA": "CASA VERDE LIMAO CACHOEIRINHA",
    "PERUS": "PERUS ANHANGUERA",
}


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name)


def norm_geo_key(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )
    key = re.sub(r"[^A-Z0-9]+", " ", text)
    key = re.sub(r"\s+", " ", key).strip()
    return SUBPREF_ALIASES.get(key, key)


def load_crime_aggregates(con: sqlite3.Connection, sub: pd.DataFrame) -> tuple[bool, bool]:
    sub_path = PROCESSED / "ssp_cellphones_by_subpref_month.csv"
    dist_path = PROCESSED / "ssp_cellphones_by_district_month.csv"
    loaded_sub = False
    loaded_dist = False

    if sub_path.exists():
        crime_sub = pd.read_csv(sub_path)
        required = {
            "ano_ocorrencia", "mes_ocorrencia", "subprefeitura_geosampa",
            "subtracoes_total", "roubos", "furtos",
        }
        missing = required.difference(crime_sub.columns)
        if missing:
            raise ValueError(f"Agregado SSP por subprefeitura sem colunas: {sorted(missing)}")

        id_map = {norm_geo_key(name): sid for name, sid in zip(sub["nome"], sub["subprefeitura_id"])}
        crime_sub["territory_key"] = crime_sub["subprefeitura_geosampa"].map(norm_geo_key)
        crime_sub = crime_sub.loc[crime_sub["territory_key"].ne("")].copy()
        unmapped = sorted(set(crime_sub["territory_key"]) - set(id_map))
        if unmapped:
            raise ValueError(f"Subprefeituras SSP/GeoSampa não mapeadas na dimensão SQL: {unmapped}")

        crime_sub["subprefeitura_id"] = crime_sub["territory_key"].map(id_map)
        crime_sub["source_id"] = 11
        crime_sub = crime_sub.rename(columns={
            "ano_ocorrencia": "occurrence_year",
            "mes_ocorrencia": "occurrence_month",
            "subtracoes_total": "cellphone_subtractions_total",
            "roubos": "robberies",
            "furtos": "thefts",
        })
        crime_sub[[
            "subprefeitura_id", "occurrence_year", "occurrence_month",
            "cellphone_subtractions_total", "robberies", "thefts", "source_id",
        ]].to_sql("crime_subpref_month", con, if_exists="append", index=False)
        loaded_sub = True

    if dist_path.exists():
        crime_dist = pd.read_csv(dist_path)
        required = {
            "ano_ocorrencia", "mes_ocorrencia", "distrito_geosampa",
            "subtracoes_total", "roubos", "furtos",
        }
        missing = required.difference(crime_dist.columns)
        if missing:
            raise ValueError(f"Agregado SSP por distrito sem colunas: {sorted(missing)}")

        crime_dist["district_name"] = crime_dist["distrito_geosampa"].map(norm_geo_key)
        crime_dist = crime_dist.loc[crime_dist["district_name"].ne("")].copy()
        crime_dist["source_id"] = 11
        crime_dist = crime_dist.rename(columns={
            "ano_ocorrencia": "occurrence_year",
            "mes_ocorrencia": "occurrence_month",
            "subtracoes_total": "cellphone_subtractions_total",
            "roubos": "robberies",
            "furtos": "thefts",
        })
        crime_dist[[
            "district_name", "occurrence_year", "occurrence_month",
            "cellphone_subtractions_total", "robberies", "thefts", "source_id",
        ]].to_sql("crime_district_month", con, if_exists="append", index=False)
        loaded_dist = True

    return loaded_sub, loaded_dist


def build() -> None:
    sources = read_csv("sources.csv")
    pop = read_csv("populacao_subpref_ibge_2022.csv")
    areas = read_csv("area_subpref_2025.csv")
    cameras = read_csv("cameras_subpref_2025_09.csv")
    history = read_csv("cameras_subpref_historico_parcial.csv")
    regions = read_csv("cameras_regioes_historico.csv")
    city = read_csv("cameras_municipio_historico.csv")

    dimensions = pop.merge(
        areas,
        on="subprefeitura",
        how="left",
        validate="one_to_one",
        suffixes=("_population", "_area"),
    )
    if dimensions["area_km2"].isna().any():
        missing = dimensions.loc[dimensions["area_km2"].isna(), "subprefeitura"].tolist()
        raise ValueError(f"Área ausente para: {missing}")

    analytical = cameras.merge(
        dimensions[["subprefeitura", "regiao_administrativa", "populacao_2022", "area_km2"]],
        on="subprefeitura",
        how="left",
        validate="one_to_one",
    )
    analytical["cameras_por_10_mil_hab_pop2022"] = (
        analytical["camera_count"] * 10000 / analytical["populacao_2022"]
    ).round(2)
    analytical["cameras_por_km2_area2025"] = (
        analytical["camera_count"] / analytical["area_km2"]
    ).round(2)
    analytical = analytical.rename(columns={"camera_count": "cameras_2025_09"})
    analytical.to_csv(
        PROCESSED / "subprefeituras_cameras_populacao_area_2025_09.csv",
        index=False,
        encoding="utf-8-sig",
    )

    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        sources.to_sql("sources", con, if_exists="append", index=False)

        sub = dimensions.reset_index(drop=True).copy()
        sub.insert(0, "subprefeitura_id", range(1, len(sub) + 1))
        sub = sub.rename(columns={"subprefeitura": "nome"})
        sub[[
            "subprefeitura_id", "nome", "regiao_administrativa", "populacao_2022",
            "area_km2", "source_id_population", "source_id_area",
        ]].to_sql("subprefeituras", con, if_exists="append", index=False)

        id_map = dict(zip(sub["nome"], sub["subprefeitura_id"]))
        complete = cameras[["subprefeitura", "reference_period", "camera_count", "source_id", "notes"]]
        hist = pd.concat([complete, history], ignore_index=True).drop_duplicates(
            subset=["subprefeitura", "reference_period", "source_id"], keep="last"
        )
        hist["subprefeitura_id"] = hist["subprefeitura"].map(id_map)
        hist[[
            "subprefeitura_id", "reference_period", "camera_count", "source_id", "notes",
        ]].to_sql("camera_subpref_snapshots", con, if_exists="append", index=False)

        regions.rename(columns={"regiao_reportada_smart_sampa": "regiao_reportada"})[[
            "reference_period", "regiao_reportada", "camera_count", "source_id", "notes",
        ]].to_sql("camera_region_snapshots", con, if_exists="append", index=False)

        city[[
            "reference_period", "camera_count", "public_camera_count",
            "private_integrated_count", "source_id", "notes",
        ]].to_sql("camera_city_snapshots", con, if_exists="append", index=False)

        loaded_sub, loaded_dist = load_crime_aggregates(con, sub)
        crime_status = "aggregates_ingested" if loaded_sub and loaded_dist else "etl_ready_not_materialized"
        geo_status = "used_in_spatial_pipeline" if loaded_sub and loaded_dist else "wfs_pipeline_ready"

        registry = pd.DataFrame([
            ["Smart Sampa por subprefeitura", 1, "2025-09", "CSV", "integrated", "Fotografia completa das 32 subprefeituras."],
            ["População por subprefeitura", 2, "2022", "CSV", "integrated", "Censo 2022."],
            ["Área por subprefeitura", 10, "2025", "CSV", "integrated", "Área oficial em km²."],
            ["Celulares subtraídos SSP-SP", 11, "2025", "XLSX → CSV agregado", crime_status, "ETL usa ano do fato, versão mais recente do BO e agregação territorial."],
            ["Geometrias GeoSampa", 12, "current", "WFS/GeoJSON", geo_status, "Subprefeituras e distritos usados no spatial join."],
        ], columns=[
            "dataset_name", "source_id", "temporal_coverage", "format", "ingestion_status", "notes",
        ])
        registry.to_sql("dataset_registry", con, if_exists="append", index=False)
        con.commit()
    finally:
        con.close()

    print(f"Database rebuilt: {DB}")
    print(f"Analytical dataset exported: {PROCESSED / 'subprefeituras_cameras_populacao_area_2025_09.csv'}")


if __name__ == "__main__":
    build()
