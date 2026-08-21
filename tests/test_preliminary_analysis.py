from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import analyze_camera_crime


def test_preliminary_analysis_reconciles_versioned_totals():
    analytical, summary, quartiles = analyze_camera_crime.build_analytical_dataset()
    metrics = dict(zip(summary["metrica"], summary["valor"]))

    assert len(analytical) == 32
    assert int(analytical["cameras_2025_09"].sum()) == 40000
    assert int(analytical["celulares_subtraidos_geocod_2025"].sum()) == 132933
    assert int(metrics["bos_elegiveis_2025"]) == 161145
    assert int(metrics["bos_com_coordenada_valida_2025"]) == 133051
    assert round(float(metrics["pct_spatial_join_subpref_entre_coords_validas"]), 2) == 99.91
    assert len(quartiles) == 4
    assert analytical["subprefeitura"].nunique() == 32


def test_main_association_is_positive_but_descriptive():
    _, summary, _ = analyze_camera_crime.build_analytical_dataset()
    metrics = dict(zip(summary["metrica"], summary["valor"]))

    assert float(metrics["pearson_cameras10k_celulares100k"]) > 0
    assert float(metrics["spearman_cameras10k_celulares100k"]) > 0
