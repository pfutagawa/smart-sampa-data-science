# Etapa SSP-SP + GeoSampa

Esta etapa documenta o pipeline para integrar os microdados de celulares subtraídos da SSP-SP aos limites administrativos oficiais do GeoSampa.

## Fontes

### SSP-SP

O portal da SSP publica arquivos anuais no padrão:

```text
https://www.ssp.sp.gov.br/assets/estatistica/transparencia/baseDados/celularesSub/CelularesSubtraidos_{ANO}.xlsx
```

A planilha observada usa a aba `CELULAR_{ANO}`. O esquema inclui, entre outros, `NOME_DELEGACIA`, `ANO_BO`, `NUM_BO`, `VERSAO`, `DATA_OCORRENCIA_BO`, `RUBRICA`, `CIDADE`, `BAIRRO`, `LOGRADOURO`, `LATITUDE` e `LONGITUDE`.

### GeoSampa

O GeoSampa documenta acesso vetorial via WFS. O pipeline usa:

```text
geoportal:subprefeitura
geoportal:distrito_municipal
```

## Decisões metodológicas

1. O campo `CIDADE` é normalizado para aceitar variantes como `S.PAULO`, `São Paulo` e `SAO PAULO`.
2. O arquivo anual é tratado como ano de registro do BO. O filtro analítico é feito depois por `DATA_OCORRENCIA_BO`.
3. A chave de deduplicação é `NOME_DELEGACIA + ANO_BO + NUM_BO`.
4. Quando existem versões do mesmo BO, mantém-se a maior `VERSAO`.
5. A unidade espacial vem das coordenadas do local do fato e de um spatial join com os polígonos oficiais; `BAIRRO` não é usado como chave administrativa.
6. Microdados e intermediários com coordenadas ficam em `data/external/` e não são versionados. Apenas agregados mensais por distrito/subprefeitura são candidatos a commit.

## Execução

Para uma análise completa das ocorrências de 2025, é recomendável ler também o arquivo de registro de 2026, pois fatos ocorridos no fim de dezembro podem ser registrados em janeiro:

```bash
python src/ingest_ssp_cellphones.py --download-years 2025 2026 --occurrence-years 2025
python src/download_geosampa.py
python src/spatial_join_crimes.py
```

Produtos agregados previstos:

```text
data/processed/ssp_cellphones_by_subpref_month.csv
data/processed/ssp_cellphones_by_district_month.csv
```

Antes de usar os agregados na análise, deve-se verificar a porcentagem de BOs com coordenadas válidas e a taxa de sucesso do spatial join.
