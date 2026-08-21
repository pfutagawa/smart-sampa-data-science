from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from spatial_join_crimes import join_boundaries, aggregate, geocoding_quality


def test_spatial_join_and_aggregation(tmp_path):
    sub = gpd.GeoDataFrame(
        {"nm_subprefeitura": ["Teste"]},
        geometry=[Polygon([(-47, -24), (-46, -24), (-46, -23), (-47, -23)])],
        crs="EPSG:4326",
    )
    dist = gpd.GeoDataFrame(
        {"nm_distrito_municipal": ["Distrito Teste"]},
        geometry=[Polygon([(-47, -24), (-46, -24), (-46, -23), (-47, -23)])],
        crs="EPSG:4326",
    )
    sub_path = tmp_path / "sub.geojson"
    dist_path = tmp_path / "dist.geojson"
    sub.to_file(sub_path, driver="GeoJSON")
    dist.to_file(dist_path, driver="GeoJSON")

    events = gpd.GeoDataFrame(
        {
            "BO_KEY": ["a", "b"],
            "ano_ocorrencia": [2025, 2025],
            "mes_ocorrencia": [1, 1],
            "roubo": [True, False],
            "furto": [False, True],
            "latitude": [-23.5, -23.6],
            "longitude": [-46.5, -46.6],
        },
        geometry=gpd.points_from_xy([-46.5, -46.6], [-23.5, -23.6]),
        crs="EPSG:4326",
    )

    joined = join_boundaries(events, sub_path, dist_path)
    assert set(joined["subprefeitura_geosampa"]) == {"TESTE"}
    assert set(joined["distrito_geosampa"]) == {"DISTRITO TESTE"}

    by_sub, by_dist = aggregate(joined)
    assert int(by_sub.iloc[0]["subtracoes_total"]) == 2
    assert int(by_sub.iloc[0]["roubos"]) == 1
    assert int(by_sub.iloc[0]["furtos"]) == 1
    assert int(by_dist.iloc[0]["subtracoes_total"]) == 2

    all_events = pd.DataFrame({
        "BO_KEY": ["a", "b", "c"],
        "ano_ocorrencia": [2025, 2025, 2025],
        "mes_ocorrencia": [1, 1, 1],
        "tem_coordenada_valida": [True, True, False],
    })
    quality = geocoding_quality(all_events, joined)
    row = quality.iloc[0]
    assert int(row["bos_elegiveis"]) == 3
    assert int(row["bos_coordenada_valida"]) == 2
    assert int(row["bos_atribuidos_subprefeitura"]) == 2
    assert float(row["pct_coordenada_valida"]) == 66.67
    assert float(row["pct_atribuido_subprefeitura_com_coord"]) == 100.0
