# Dados

Este diretório separa **dados transcritos/baixados** (`raw`) de tabelas derivadas (`processed`).

## Princípios

- Toda observação deve manter uma referência a `source_id` quando possível.
- Lacunas históricas não são preenchidas por interpolação.
- A contagem de câmeras representa um **estoque dinâmico de equipamentos conectados**; integrações privadas podem entrar e sair do sistema.
- Os microdados anuais da SSP-SP não devem ser versionados neste repositório enquanto não forem avaliados tamanho, licença e necessidade de minimização. O script de ingestão aceita arquivos locais.

## Arquivos atuais

- `raw/cameras_subpref_2025_09.csv`: fotografia completa das 32 subprefeituras em setembro/2025.
- `raw/populacao_subpref_ibge_2022.csv`: população do Censo 2022 agregada por subprefeitura.
- `raw/area_subpref_2025.csv`: área oficial 2025 em km².
- `raw/cameras_subpref_historico_parcial.csv`: snapshots adicionais encontrados para Mooca e Itaim Paulista.
- `raw/cameras_regioes_historico.csv`: totais por cinco regiões conforme reportados pelo Smart Sampa.
- `raw/cameras_municipio_historico.csv`: marcos municipais conhecidos.
- `raw/sources.csv`: registro de proveniência.
- `processed/subprefeituras_cameras_populacao_area_2025_09.csv`: integração analítica reprodutível.
