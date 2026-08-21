from pathlib import Path
import sqlite3
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_database


def test_schema_and_geo_name_normalization():
    con = sqlite3.connect(":memory:")
    con.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
    objects = {row[0] for row in con.execute("SELECT name FROM sqlite_master")}
    assert "crime_subpref_month" in objects
    assert "crime_district_month" in objects
    assert "vw_camera_crime_subpref_2025" in objects
    assert build_database.norm_geo_key("Sé") == "SE"
    assert build_database.norm_geo_key("  M'Boi   Mirim ") == "M'BOI MIRIM"
    assert build_database.norm_geo_key("Casa Verde/Cachoeirinha") == "CASA VERDE/LIMAO/CACHOEIRINHA"
    assert build_database.norm_geo_key("São Miguel") == "SAO MIGUEL PAULISTA"
    assert build_database.norm_geo_key("Perus") == "PERUS/ANHANGUERA"
    con.close()


def test_optional_crime_aggregates_load_into_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(build_database, "PROCESSED", tmp_path)

    pd.DataFrame([
        {
            "ano_ocorrencia": 2025,
            "mes_ocorrencia": 1,
            "subprefeitura_geosampa": "SE",
            "subtracoes_total": 10,
            "roubos": 6,
            "furtos": 4,
        }
    ]).to_csv(tmp_path / "ssp_cellphones_by_subpref_month.csv", index=False)

    pd.DataFrame([
        {
            "ano_ocorrencia": 2025,
            "mes_ocorrencia": 1,
            "distrito_geosampa": "SE",
            "subtracoes_total": 7,
            "roubos": 5,
            "furtos": 2,
        }
    ]).to_csv(tmp_path / "ssp_cellphones_by_district_month.csv", index=False)

    con = sqlite3.connect(":memory:")
    con.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
    con.execute(
        "INSERT INTO sources (source_id, dataset, publisher, url, accessed_on) VALUES (11, 'SSP', 'SSP-SP', 'https://example.test', '2026-08-21')"
    )
    con.execute(
        "INSERT INTO sources (source_id, dataset, publisher, url, accessed_on) VALUES (2, 'Pop', 'IBGE', 'https://example.test', '2026-08-21')"
    )
    con.execute(
        "INSERT INTO sources (source_id, dataset, publisher, url, accessed_on) VALUES (10, 'Area', 'PMSP', 'https://example.test', '2026-08-21')"
    )
    con.execute(
        "INSERT INTO subprefeituras VALUES (1, 'Sé', 'Centro', 100000, 10.0, 2, 10)"
    )

    sub = pd.DataFrame([{"subprefeitura_id": 1, "nome": "Sé"}])
    loaded_sub, loaded_dist = build_database.load_crime_aggregates(con, sub)

    assert loaded_sub and loaded_dist
    assert con.execute("SELECT cellphone_subtractions_total FROM crime_subpref_month").fetchone()[0] == 10
    assert con.execute("SELECT cellphone_subtractions_total FROM crime_district_month").fetchone()[0] == 7
    con.close()
