"""Atribui cada BO georreferenciado da SSP a distrito e subprefeitura.

A associação territorial é feita pelas coordenadas do local do fato, não pelo
campo BAIRRO nem pela delegacia de registro. Os CSVs territoriais incluem apenas
BOs efetivamente atribuídos a um polígono; perdas de coordenadas/atribuição são
registradas separadamente em um arquivo mensal de qualidade.
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


def bool_mask(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1"})


def load_event_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def events_with_valid_coordinates(df: pd.DataFrame) -> gpd.GeoDataFrame:
    valid = df.loc[bool_mask(df["tem_coordenada_valida"])].copy()
    return gpd.GeoDataFrame(
        valid,
        geometry=gpd.points_from_xy(valid["longitude"], valid["latitude"]),
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

    def _agg(group_cols, territory_col):
        scoped = base.loc[base[territory_col].fillna("").astype(str).str.strip().ne("")].copy()
        rows = []
        for keys, g in scoped.groupby(group_cols, dropna=False):
            keys = keys if isinstance(keys, tuple) else (keys,)
            row = dict(zip(group_cols, keys))
            row.update({
                "subtracoes_total": g["BO_KEY"].nunique(),
                "roubos": g.loc[bool_mask(g["roubo"]), "BO_KEY"].nunique(),
                "furtos": g.loc[bool_mask(g["furto"]), "BO_KEY"].nunique(),
            })
            rows.append(row)
        return pd.DataFrame(rows)

    sub = _agg(
        ["ano_ocorrencia", "mes_ocorrencia", "subprefeitura_geosampa"],
        "subprefeitura_geosampa",
    )
    dist = _agg(
        ["ano_ocorrencia", "mes_ocorrencia", "distrito_geosampa"],
        "distrito_geosampa",
    )
    return sub, dist


def geocoding_quality(all_events: pd.DataFrame, joined: pd.DataFrame) -> pd.DataFrame:
    base = all_events.dropna(subset=["ano_ocorrencia", "mes_ocorrencia"]).copy()
    base["coord_valida"] = bool_mask(base["tem_coordenada_valida"])

    total = (
        base.groupby(["ano_ocorrencia", "mes_ocorrencia"], as_index=False)
        .agg(
            bos_elegiveis=("BO_KEY", "nunique"),
            bos_coordenada_valida=("coord_valida", "sum"),
        )
    )

    assigned = joined.copy()
    assigned["atribuido_subprefeitura"] = assigned["subprefeitura_geosampa"].fillna("").astype(str).str.strip().ne("")
    assigned["atribuido_distrito"] = assigned["distrito_geosampa"].fillna("").astype(str).str.strip().ne("")
    assignment = (
        assigned.groupby(["ano_ocorrencia", "mes_ocorrencia"], as_index=False)
        .agg(
            bos_atribuidos_subprefeitura=("atribuido_subprefeitura", "sum"),
            bos_atribuidos_distrito=("atribuido_distrito", "sum"),
        )
    )

    quality = total.merge(assignment, on=["ano_ocorrencia", "mes_ocorrencia"], how="left").fillna(0)
    for col in ["bos_coordenada_valida", "bos_atribuidos_subprefeitura", "bos_atribuidos_distrito"]:
        quality[col] = quality[col].astype(int)
    quality["pct_coordenada_valida"] = (quality["bos_coordenada_valida"] * 100 / quality["bos_elegiveis"]).round(2)
    quality["pct_atribuido_subprefeitura_total"] = (quality["bos_atribuidos_subprefeitura"] * 100 / quality["bos_elegiveis"]).round(2)
    quality["pct_atribuido_distrito_total"] = (quality["bos_atribuidos_distrito"] * 100 / quality["bos_elegiveis"]).round(2)
    quality["pct_atribuido_subprefeitura_com_coord"] = (
        quality["bos_atribuidos_subprefeitura"] * 100 / quality["bos_coordenada_valida"]
    ).round(2)
    quality["pct_atribuido_distrito_com_coord"] = (
        quality["bos_atribuidos_distrito"] * 100 / quality["bos_coordenada_valida"]
    ).round(2)
    return quality.sort_values(["ano_ocorrencia", "mes_ocorrencia"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, default=Path("data/external/ssp/processed/ssp_cellphones_events.csv.gz"))
    parser.add_argument("--subpref", type=Path, default=Path("data/external/geosampa/geosampa_subprefeituras.geojson"))
    parser.add_argument("--district", type=Path, default=Path("data/external/geosampa/geosampa_distritos.geojson"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    all_events = load_event_frame(args.events)
    events = events_with_valid_coordinates(all_events)
    joined = join_boundaries(events, args.subpref, args.district)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    event_level_dir = Path("data/external/ssp/processed")
    event_level_dir.mkdir(parents=True, exist_ok=True)
    joined.to_csv(event_level_dir / "ssp_cellphones_events_geocoded.csv.gz", index=False, compression="gzip")

    by_sub, by_dist = aggregate(joined)
    quality = geocoding_quality(all_events, joined)
    by_sub.to_csv(args.output_dir / "ssp_cellphones_by_subpref_month.csv", index=False)
    by_dist.to_csv(args.output_dir / "ssp_cellphones_by_district_month.csv", index=False)
    quality.to_csv(args.output_dir / "ssp_geocoding_quality_month.csv", index=False)

    total = int(quality["bos_elegiveis"].sum())
    valid = int(quality["bos_coordenada_valida"].sum())
    assigned_sub = int(quality["bos_atribuidos_subprefeitura"].sum())
    assigned_dist = int(quality["bos_atribuidos_distrito"].sum())
    print(f"BOs elegíveis: {total:,}")
    print(f"Coordenada válida: {valid:,} ({valid * 100 / total:.2f}%)")
    print(f"Atribuídos a subprefeitura: {assigned_sub:,} ({assigned_sub * 100 / total:.2f}% do total; {assigned_sub * 100 / valid:.2f}% dos geocodificados)")
    print(f"Atribuídos a distrito: {assigned_dist:,} ({assigned_dist * 100 / total:.2f}% do total; {assigned_dist * 100 / valid:.2f}% dos geocodificados)")


if __name__ == "__main__":
    main()
