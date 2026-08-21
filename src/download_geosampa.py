"""Baixa limites administrativos oficiais do GeoSampa via WFS.

Fontes vetoriais:
- geoportal:subprefeitura
- geoportal:distrito_municipal

O WFS é a interface oficial documentada pelo tutorial do GeoSampa.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

WFS_BASE = "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs"
LAYERS = {
    "subprefeituras": "geoportal:subprefeitura",
    "distritos": "geoportal:distrito_municipal",
}


def wfs_url(layer: str) -> str:
    return (
        f"{WFS_BASE}?version=1.1.0&request=GetFeature"
        f"&typeName={layer}&outputFormat=application/json"
    )


def download(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, layer in LAYERS.items():
        url = wfs_url(layer)
        print(f"Baixando {name}: {url}")
        gdf = gpd.read_file(url)
        if gdf.empty:
            raise RuntimeError(f"Camada {name} retornou vazia.")
        target = output_dir / f"geosampa_{name}.geojson"
        gdf.to_crs(4326).to_file(target, driver="GeoJSON")
        print(f"{name}: {len(gdf)} feições -> {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/external/geosampa"))
    args = parser.parse_args()
    download(args.output_dir)


if __name__ == "__main__":
    main()
