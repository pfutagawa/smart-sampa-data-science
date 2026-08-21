from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ingest_ssp_cellphones import is_sao_paulo, norm_city, transform


def test_city_variants():
    assert is_sao_paulo("S.PAULO")
    assert is_sao_paulo("São Paulo")
    assert is_sao_paulo("SAO PAULO")
    assert norm_city("  S. Paulo ") == "SPAULO"


def test_other_city_is_rejected():
    assert not is_sao_paulo("Guarulhos")


def test_transform_keeps_latest_version_and_occurrence_year(tmp_path):
    rows = [
        {
            "NOME_DELEGACIA": "DELEGACIA ELETRONICA", "ANO_BO": 2025, "NUM_BO": "AA1", "VERSAO": 1,
            "DATA_OCORRENCIA_BO": "2024-12-31", "RUBRICA": "Furto (art. 155)", "CIDADE": "S.PAULO",
            "BAIRRO": "SE", "LOGRADOURO": "RUA A", "NUMERO_LOGRADOURO": 1,
            "LATITUDE": -23.55, "LONGITUDE": -46.63,
        },
        {
            "NOME_DELEGACIA": "DELEGACIA ELETRONICA", "ANO_BO": 2025, "NUM_BO": "AA1", "VERSAO": 2,
            "DATA_OCORRENCIA_BO": "2024-12-31", "RUBRICA": "Roubo (art. 157)", "CIDADE": "S.PAULO",
            "BAIRRO": "SE", "LOGRADOURO": "RUA A", "NUMERO_LOGRADOURO": 1,
            "LATITUDE": -23.55, "LONGITUDE": -46.63,
        },
        {
            "NOME_DELEGACIA": "01 DP", "ANO_BO": 2025, "NUM_BO": "2", "VERSAO": 1,
            "DATA_OCORRENCIA_BO": "2025-02-10", "RUBRICA": "Furto (art. 155)", "CIDADE": "São Paulo",
            "BAIRRO": "PINHEIROS", "LOGRADOURO": "RUA B", "NUMERO_LOGRADOURO": 2,
            "LATITUDE": -23.56, "LONGITUDE": -46.68,
        },
        {
            "NOME_DELEGACIA": "01 DP", "ANO_BO": 2025, "NUM_BO": "3", "VERSAO": 1,
            "DATA_OCORRENCIA_BO": "2025-02-10", "RUBRICA": "Roubo (art. 157)", "CIDADE": "Guarulhos",
            "BAIRRO": "CENTRO", "LOGRADOURO": "RUA C", "NUMERO_LOGRADOURO": 3,
            "LATITUDE": -23.45, "LONGITUDE": -46.53,
        },
    ]
    path = tmp_path / "CelularesSubtraidos_2025.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    only_2024 = transform([path], {2024})
    assert len(only_2024) == 1
    assert only_2024.iloc[0]["tipo_subtracao"] == "roubo"
    assert int(only_2024.iloc[0]["ano_ocorrencia"]) == 2024

    only_2025 = transform([path], {2025})
    assert len(only_2025) == 1
    assert only_2025.iloc[0]["tipo_subtracao"] == "furto"
