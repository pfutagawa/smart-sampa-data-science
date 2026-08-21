"""Inspeção/ingestão inicial da base SSP - Celulares Subtraídos.

Uso:
    python src/ingest_ssp_cellphones.py data/raw/CelularesSubtraidos_2025.xlsx

Nesta fase o script apenas valida o esquema, filtra Município de São Paulo quando
o campo CIDADE existe e reporta possíveis chaves/ rubricas. A agregação por
subprefeitura só deve ser implementada depois de inspecionar coordenadas e obter
a geometria oficial do GeoSampa.
"""
from pathlib import Path
import sys
import unicodedata
import pandas as pd

def norm(value):
    text = str(value).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

def load(path):
    path = Path(path)
    if path.suffix.lower() in {'.xlsx', '.xls'}:
        df = pd.read_excel(path)
    elif path.suffix.lower() == '.csv':
        df = pd.read_csv(path, low_memory=False)
    else:
        raise ValueError('Formato esperado: XLSX, XLS ou CSV.')
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def main(path):
    df = load(path)
    print(f'Linhas originais: {len(df):,}')
    print('Colunas:', ', '.join(df.columns))
    if 'CIDADE' in df.columns:
        mask = df['CIDADE'].map(norm).eq('SAO PAULO')
        df = df.loc[mask].copy()
        print(f'Linhas com CIDADE = São Paulo: {len(df):,}')
    key_cols = ['NOME_DELEGACIA', 'ANO_BO', 'NUM_BO']
    if all(c in df.columns for c in key_cols):
        df['BO_KEY'] = df[key_cols].astype(str).agg('|'.join, axis=1)
        print(f'BOs únicos pela chave NOME_DELEGACIA+ANO_BO+NUM_BO: {df.BO_KEY.nunique():,}')
    if 'RUBRICA' in df.columns:
        rubric = df['RUBRICA'].astype(str).map(norm)
        print(f'Linhas cuja RUBRICA contém ROUBO: {rubric.str.contains("ROUBO", na=False).sum():,}')
        print(f'Linhas cuja RUBRICA contém FURTO: {rubric.str.contains("FURTO", na=False).sum():,}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Informe o caminho do XLSX/CSV da SSP.')
    main(sys.argv[1])
