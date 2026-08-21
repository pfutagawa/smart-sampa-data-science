"""Rebuild the project's SQLite database from versioned CSV files.

Run from the repository root:
    python src/build_database.py
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB = ROOT / "database" / "smart_sampa.sqlite"
SCHEMA = ROOT / "database" / "schema.sql"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name)


def build() -> None:
    sources = read_csv("sources.csv")
    pop = read_csv("populacao_subpref_ibge_2022.csv")
    areas = read_csv("area_subpref_2025.csv")
    cameras = read_csv("cameras_subpref_2025_09.csv")
    history = read_csv("cameras_subpref_historico_parcial.csv")
    regions = read_csv("cameras_regioes_historico.csv")
    city = read_csv("cameras_municipio_historico.csv")

    dimensions = pop.merge(areas, on="subprefeitura", how="left", validate="one_to_one", suffixes=("_population", "_area"))
    if dimensions["area_km2"].isna().any():
        missing = dimensions.loc[dimensions["area_km2"].isna(), "subprefeitura"].tolist()
        raise ValueError(f"Área ausente para: {missing}")

    analytical = cameras.merge(
        dimensions[["subprefeitura", "regiao_administrativa", "populacao_2022", "area_km2"]],
        on="subprefeitura", how="left", validate="one_to_one",
    )
    analytical["cameras_por_10_mil_hab_pop2022"] = (analytical["camera_count"] * 10000 / analytical["populacao_2022"]).round(2)
    analytical["cameras_por_km2_area2025"] = (analytical["camera_count"] / analytical["area_km2"]).round(2)
    analytical = analytical.rename(columns={"camera_count": "cameras_2025_09"})
    analytical.to_csv(PROCESSED / "subprefeituras_cameras_populacao_area_2025_09.csv", index=False, encoding="utf-8-sig")

    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        sources.to_sql("sources", con, if_exists="append", index=False)
        sub = dimensions.reset_index(drop=True).copy()
        sub.insert(0, "subprefeitura_id", range(1, len(sub) + 1))
        sub = sub.rename(columns={"subprefeitura": "nome"})
        sub[["subprefeitura_id", "nome", "regiao_administrativa", "populacao_2022", "area_km2", "source_id_population", "source_id_area"]].to_sql("subprefeituras", con, if_exists="append", index=False)
        id_map = dict(zip(sub["nome"], sub["subprefeitura_id"]))
        complete = cameras[["subprefeitura", "reference_period", "camera_count", "source_id", "notes"]]
        hist = pd.concat([complete, history], ignore_index=True).drop_duplicates(subset=["subprefeitura", "reference_period", "source_id"], keep="last")
        hist["subprefeitura_id"] = hist["subprefeitura"].map(id_map)
        hist[["subprefeitura_id", "reference_period", "camera_count", "source_id", "notes"]].to_sql("camera_subpref_snapshots", con, if_exists="append", index=False)
        regions.rename(columns={"regiao_reportada_smart_sampa": "regiao_reportada"})[["reference_period", "regiao_reportada", "camera_count", "source_id", "notes"]].to_sql("camera_region_snapshots", con, if_exists="append", index=False)
        city[["reference_period", "camera_count", "public_camera_count", "private_integrated_count", "source_id", "notes"]].to_sql("camera_city_snapshots", con, if_exists="append", index=False)
        registry = pd.DataFrame([
            ["Smart Sampa por subprefeitura", 1, "2025-09", "CSV", "integrated", "Fotografia completa das 32 subprefeituras."],
            ["População por subprefeitura", 2, "2022", "CSV", "integrated", "Censo 2022."],
            ["Área por subprefeitura", 10, "2025", "CSV", "integrated", "Área oficial em km²."],
            ["Celulares subtraídos SSP-SP", 8, "2017-2026", "XLSX", "located_not_ingested", "Aguardando download e inspeção do esquema."],
            ["Geometrias GeoSampa", None, "current", "GeoJSON/SHP", "located_not_ingested", "Aguardando materialização da camada oficial."],
        ], columns=["dataset_name", "source_id", "temporal_coverage", "format", "ingestion_status", "notes"])
        registry.to_sql("dataset_registry", con, if_exists="append", index=False)
        con.commit()
    finally:
        con.close()

    print(f"Database rebuilt: {DB}")
    print(f"Analytical dataset exported: {PROCESSED / 'subprefeituras_cameras_populacao_area_2025_09.csv'}")


if __name__ == "__main__":
    build()
