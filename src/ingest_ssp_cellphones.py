"""ETL dos microdados de celulares subtraídos da SSP-SP.

O portal da SSP publica um XLSX por *ano de registro* do BO. Como a data do
fato pode pertencer ao ano anterior, o pipeline aceita vários arquivos e filtra
por DATA_OCORRENCIA_BO somente depois de consolidá-los.

Exemplos:
    python src/ingest_ssp_cellphones.py \
        data/external/CelularesSubtraidos_2025.xlsx \
        data/external/CelularesSubtraidos_2026.xlsx \
        --occurrence-years 2025 --output data/external/ssp/processed/ssp_cellphones_events.csv.gz

    python src/ingest_ssp_cellphones.py --download-years 2024 2025 2026 \
        --occurrence-years 2024 2025

Os XLSX originais não são versionados no repositório.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

SSP_URL = (
    "https://www.ssp.sp.gov.br/assets/estatistica/transparencia/baseDados/"
    "celularesSub/CelularesSubtraidos_{year}.xlsx"
)

USECOLS = [
    "NOME_DELEGACIA",
    "ANO_BO",
    "NUM_BO",
    "VERSAO",
    "DATA_OCORRENCIA_BO",
    "RUBRICA",
    "CIDADE",
    "BAIRRO",
    "LOGRADOURO",
    "NUMERO_LOGRADOURO",
    "LATITUDE",
    "LONGITUDE",
]


def norm_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", text)


def norm_city(value: object) -> str:
    """Normaliza variantes como 'S.PAULO', 'SÃO PAULO' e 'SAO PAULO'."""
    return re.sub(r"[^A-Z]", "", norm_text(value))


def is_sao_paulo(value: object) -> bool:
    return norm_city(value) in {"SAOPAULO", "SPAULO"}


def download_ssp(year: int, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"CelularesSubtraidos_{year}.xlsx"
    if target.exists() and target.stat().st_size > 0:
        return target

    url = SSP_URL.format(year=year)
    print(f"Baixando SSP {year}: {url}")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=180) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return target


def registration_year_from_name(path: Path) -> int | None:
    match = re.search(r"(20\d{2})", path.name)
    return int(match.group(1)) if match else None


def load_xlsx(path: Path) -> pd.DataFrame:
    year = registration_year_from_name(path)
    sheet = f"CELULAR_{year}" if year else 0
    df = pd.read_excel(path, sheet_name=sheet, usecols=lambda c: str(c).upper() in USECOLS)
    df.columns = [str(c).strip().upper() for c in df.columns]
    missing = [c for c in USECOLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: colunas ausentes: {missing}")
    df["ARQUIVO_REGISTRO_ANO"] = year
    return df


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False, usecols=lambda c: str(c).upper() in USECOLS)
    df.columns = [str(c).strip().upper() for c in df.columns]
    missing = [c for c in USECOLS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: colunas ausentes: {missing}")
    df["ARQUIVO_REGISTRO_ANO"] = registration_year_from_name(path)
    return df


def load_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return load_xlsx(path)
    if suffix in {".csv", ".gz"} or path.name.lower().endswith(".csv.gz"):
        return load_csv(path)
    raise ValueError(f"Formato não suportado: {path}")


def _pick_first(series: pd.Series):
    values = series.dropna()
    return values.iloc[0] if not values.empty else pd.NA


def transform(files: list[Path], occurrence_years: set[int] | None = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in files:
        print(f"Lendo {path.name} ...")
        frames.append(load_file(path))
    raw = pd.concat(frames, ignore_index=True)
    print(f"Linhas lidas: {len(raw):,}")

    raw = raw.loc[raw["CIDADE"].map(is_sao_paulo)].copy()
    print(f"Linhas do município de São Paulo: {len(raw):,}")

    raw["DATA_OCORRENCIA_BO"] = pd.to_datetime(raw["DATA_OCORRENCIA_BO"], errors="coerce")
    raw["ANO_OCORRENCIA"] = raw["DATA_OCORRENCIA_BO"].dt.year.astype("Int64")
    raw["MES_OCORRENCIA"] = raw["DATA_OCORRENCIA_BO"].dt.month.astype("Int64")

    if occurrence_years:
        raw = raw.loc[raw["ANO_OCORRENCIA"].isin(occurrence_years)].copy()

    raw["BO_KEY"] = (
        raw[["NOME_DELEGACIA", "ANO_BO", "NUM_BO"]]
        .fillna("")
        .astype(str)
        .agg("|".join, axis=1)
    )
    raw["VERSAO_NUM"] = pd.to_numeric(raw["VERSAO"], errors="coerce").fillna(-1)
    max_version = raw.groupby("BO_KEY")["VERSAO_NUM"].transform("max")
    latest = raw.loc[raw["VERSAO_NUM"].eq(max_version)].copy()

    latest["RUBRICA_NORM"] = latest["RUBRICA"].map(norm_text)
    latest["IS_ROUBO"] = latest["RUBRICA_NORM"].str.contains(r"\bROUBO\b", regex=True, na=False)
    latest["IS_FURTO"] = latest["RUBRICA_NORM"].str.contains(r"\bFURTO\b", regex=True, na=False)

    latest["LATITUDE"] = pd.to_numeric(latest["LATITUDE"], errors="coerce")
    latest["LONGITUDE"] = pd.to_numeric(latest["LONGITUDE"], errors="coerce")
    valid_coord = (
        latest["LATITUDE"].between(-24.1, -23.2)
        & latest["LONGITUDE"].between(-47.1, -46.2)
    )
    latest.loc[~valid_coord, ["LATITUDE", "LONGITUDE"]] = pd.NA

    agg = latest.groupby("BO_KEY", as_index=False).agg(
        data_ocorrencia=("DATA_OCORRENCIA_BO", _pick_first),
        ano_ocorrencia=("ANO_OCORRENCIA", _pick_first),
        mes_ocorrencia=("MES_OCORRENCIA", _pick_first),
        bairro_ssp=("BAIRRO", _pick_first),
        logradouro_ssp=("LOGRADOURO", _pick_first),
        numero_logradouro=("NUMERO_LOGRADOURO", _pick_first),
        latitude=("LATITUDE", _pick_first),
        longitude=("LONGITUDE", _pick_first),
        roubo=("IS_ROUBO", "max"),
        furto=("IS_FURTO", "max"),
    )

    agg = agg.loc[agg["roubo"] | agg["furto"]].copy()
    agg["tipo_subtracao"] = "outro"
    agg.loc[agg["roubo"] & ~agg["furto"], "tipo_subtracao"] = "roubo"
    agg.loc[agg["furto"] & ~agg["roubo"], "tipo_subtracao"] = "furto"
    agg.loc[agg["roubo"] & agg["furto"], "tipo_subtracao"] = "roubo_e_furto_no_mesmo_bo"
    agg["tem_coordenada_valida"] = agg["latitude"].notna() & agg["longitude"].notna()

    print(f"BOs únicos de roubo/furto: {len(agg):,}")
    print(f"BOs com coordenada válida: {agg['tem_coordenada_valida'].sum():,}")
    return agg.sort_values(["data_ocorrencia", "BO_KEY"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", type=Path, help="XLSX/CSV da SSP")
    parser.add_argument("--download-years", nargs="*", type=int, default=[])
    parser.add_argument("--occurrence-years", nargs="*", type=int, default=[])
    parser.add_argument("--external-dir", type=Path, default=Path("data/external/ssp"))
    parser.add_argument("--output", type=Path, default=Path("data/external/ssp/processed/ssp_cellphones_events.csv.gz"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    files = list(args.files)
    for year in args.download_years:
        files.append(download_ssp(year, args.external_dir))
    if not files:
        raise SystemExit("Informe arquivos ou --download-years.")

    result = transform(files, set(args.occurrence_years) or None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, compression="infer")
    print(f"Salvo: {args.output}")


if __name__ == "__main__":
    main()
