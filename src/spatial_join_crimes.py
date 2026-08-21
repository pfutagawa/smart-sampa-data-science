"""Atribui cada BO georreferenciado da SSP a distrito e subprefeitura.

A associação territorial é feita pelas coordenadas do local do fato, não pelo
campo BAIRRO nem pela delegacia de registro.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd


def norm(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().upper()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)


def find_column(columns, candidates):
    lookup = {norm(c): c for c in columns}
    for candidate in candidates:
        if norm(candidate) in lookup:
            return lookup[norm(candidate)]
    raise KeyError(f"Nenhuma das colunas esperadas encontrada: {candidates}. Disponíveis: {list(columns)}")


def load_events(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, low_memory=False)
    df = df.loc[df["tem_coordenada_valida"].astype(str).str.lower().isin({"true", "1"})].copy()
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )


def join_boundaries(events: gpd.GeoDataFrame, subpref_path: Path, district_path: Path) -> pd.DataFrame:
    sub = gpd.read_file(subpref_path).to_crs(events.crs)
    dist = gpd.read_file(district_path).to_crs(events.crs)

    sub_name = find_column(sub.columns, ["nm_subprefeitura", "subprefeitura", "nome"])
    dist_name = find_column(dist.columns, ["nm_distrito_municipal", "nm_distrito", "distrito", "nome"])

    sub_small = sub[[sub_name, "geometry"]].rename(columns={sub_name: "subprefeitura_geosampa"})
    dist_small = dist[[dist_name, "geometry"]].rename(columns={dist_name: "distrito_geosampa"})

    joined = gpd.sjoin(events, sub_small, how="left", predicate="within").drop(columns=["index_right"], errors="ignore")
    joined = gpd.sjoin(joined, dist_small, how="left", predicate="within").drop(columns=["index_right"], errors="ignore")
    joined["subprefeitura_geosampa"] = joined["subprefeitura_geosampa"].map(norm)
    joined["distrito_geosampa"] = joined["distrito_geosampa"].map(norm)
    return pd.DataFrame(joined.drop(columns="geometry"))


def aggregate(joined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = joined.dropna(subset=["ano_ocorrencia", "mes_ocorrencia"]).copy()

    def _agg(group_cols):
        rows = []
        for keys, g in base.groupby(group_cols, dropna=False):
            keys = keys if isinstance(keys, tuple) else (keys,)
            row = dict(zip(group_cols, keys))
            row.update({
                "subtracoes_total": g["BO_KEY"].nunique(),
                "roubos": g.loc[g["roubo"].astype(str).str.lower().isin({"true", "1"}), "BO_KEY"].nunique(),
                "furtos": g.loc[g["furto"].astype(str).str.lower().isin({"true", "1"}), "BO_KEY"].nunique(),
            })
            rows.append(row)
        return pd.DataFrame(rows)

    sub = _agg(["ano_ocorrencia", "mes_ocorrencia", "subprefeitura_geosampa"])
    dist = _agg(["ano_ocorrencia", "mes_ocorrencia", "distrito_geosampa"])
    return sub, dist


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, default=Path("data/external/ssp/processed/ssp_cellphones_events.csv.gz"))
    parser.add_argument("--subpref", type=Path, default=Path("data/external/geosampa/geosampa_subprefeituras.geojson"))
    parser.add_argument("--district", type=Path, default=Path("data/external/geosampa/geosampa_distritos.geojson"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    events = load_events(args.events)
    joined = join_boundaries(events, args.subpref, args.district)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    event_level_dir = Path("data/external/ssp/processed")
    event_level_dir.mkdir(parents=True, exist_ok=True)
    joined.to_csv(event_level_dir / "ssp_cellphones_events_geocoded.csv.gz", index=False, compression="gzip")

    by_sub, by_dist = aggregate(joined)
    by_sub.to_csv(args.output_dir / "ssp_cellphones_by_subpref_month.csv", index=False)
    by_dist.to_csv(args.output_dir / "ssp_cellphones_by_district_month.csv", index=False)

    pct_sub = joined["subprefeitura_geosampa"].replace("", pd.NA).notna().mean() * 100
    pct_dist = joined["distrito_geosampa"].replace("", pd.NA).notna().mean() * 100
    print(f"Spatial join subprefeitura: {pct_sub:.2f}%")
    print(f"Spatial join distrito: {pct_dist:.2f}%")


if __name__ == "__main__":
    main()
