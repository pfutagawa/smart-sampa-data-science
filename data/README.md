# Dados

Este diretório separa **dados transcritos/baixados** (`raw`), arquivos externos não versionados (`external`) e tabelas derivadas (`processed`).

## Princípios

- Toda observação deve manter uma referência a `source_id` quando possível.
- Lacunas históricas não são preenchidas por interpolação.
- A contagem de câmeras representa um **estoque dinâmico de equipamentos conectados**; integrações privadas podem entrar e sair do sistema.
- Microdados da SSP-SP com endereço/coordenadas permanecem em `data/external/` e não entram no Git.
- Apenas agregados territoriais e métricas de qualidade são versionados.

## Arquivos atuais

- `raw/cameras_subpref_2025_09.csv`: fotografia completa das 32 subprefeituras em setembro/2025.
- `raw/populacao_subpref_ibge_2022.csv`: população do Censo 2022 agregada por subprefeitura.
- `raw/area_subpref_2025.csv`: área oficial 2025 em km².
- `raw/cameras_subpref_historico_parcial.csv`: snapshots adicionais encontrados para Mooca e Itaim Paulista.
- `raw/cameras_regioes_historico.csv`: totais por cinco regiões conforme reportados pelo Smart Sampa.
- `raw/cameras_municipio_historico.csv`: marcos municipais conhecidos.
- `raw/sources.csv`: registro de proveniência.
- `processed/subprefeituras_cameras_populacao_area_2025_09.csv`: integração analítica de câmeras, população e área.
- `processed/ssp_cellphones_by_subpref_month.csv`: BOs de celulares subtraídos em 2025 espacialmente atribuídos às 32 subprefeituras.
- `processed/ssp_cellphones_by_district_month.csv`: mesma base espacialmente atribuída aos 96 distritos.
- `processed/ssp_geocoding_quality_month.csv`: cobertura mensal do processo de geocodificação/atribuição territorial.

## Cobertura espacial da SSP em 2025

O pipeline identificou 161.145 BOs únicos elegíveis. Destes, 133.051 (82,57%) possuem coordenadas válidas e 132.933 (82,49% do total) foram atribuídos aos polígonos do GeoSampa. As tabelas territoriais, portanto, representam a **parcela espacialmente atribuível** da base, e não a totalidade dos BOs.
