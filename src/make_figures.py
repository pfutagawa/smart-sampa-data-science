"""Generate two lightweight exploratory figures from the integrated snapshot."""
from pathlib import Path
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "smart_sampa.sqlite"
OUT = ROOT / "reports" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    con = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM vw_subpref_cameras_2025_09", con)
    con.close()

    top = df.nlargest(10, "cameras_2025_09").sort_values("cameras_2025_09")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(top["subprefeitura"], top["cameras_2025_09"])
    ax.set_title("Smart Sampa: 10 subprefeituras com mais câmeras")
    ax.set_xlabel("Câmeras conectadas — setembro de 2025")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(OUT / "top10_cameras_2025_09.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    pc = df.nlargest(10, "cameras_por_10_mil_hab_pop2022").sort_values("cameras_por_10_mil_hab_pop2022")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(pc["subprefeitura"], pc["cameras_por_10_mil_hab_pop2022"])
    ax.set_title("Cobertura exploratória: câmeras por 10 mil habitantes")
    ax.set_xlabel("Câmeras de set/2025 por 10 mil hab. (população Censo 2022)")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(OUT / "top10_cameras_per_capita_2025_09.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
