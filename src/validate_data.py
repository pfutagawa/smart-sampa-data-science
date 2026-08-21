"""Small reproducible quality checks for the versioned project data."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def main() -> None:
    cameras = pd.read_csv(RAW / "cameras_subpref_2025_09.csv")
    population = pd.read_csv(RAW / "populacao_subpref_ibge_2022.csv")
    areas = pd.read_csv(RAW / "area_subpref_2025.csv")

    assert len(cameras) == 32, "Esperadas 32 subprefeituras na fotografia de set/2025."
    assert cameras["camera_count"].sum() == 40000, "A soma das câmeras deveria ser 40.000."
    assert len(population) == 32 and population["populacao_2022"].sum() == 11451999
    assert len(areas) == 32 and (areas["area_km2"] > 0).all()
    assert set(cameras["subprefeitura"]) == set(population["subprefeitura"]) == set(areas["subprefeitura"])

    print("OK — validações principais concluídas.")


if __name__ == "__main__":
    main()
