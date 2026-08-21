# Dados

Este diretório separa os dados pequenos e versionáveis do projeto dos microdados externos usados apenas durante o processamento.

## Estrutura

### `raw/`

Dados públicos estruturados/transcritos que são pequenos o suficiente para versionamento e cuja proveniência está registrada em `raw/sources.csv`.

Arquivos atuais:

- `cameras_subpref_2025_09.csv`: fotografia completa das 32 subprefeituras em setembro/2025.
- `populacao_subpref_ibge_2022.csv`: população do Censo 2022 agregada por subprefeitura.
- `area_subpref_2025.csv`: área oficial 2025 em km².
- `cameras_subpref_historico_parcial.csv`: snapshots adicionais para Mooca e Itaim Paulista.
- `cameras_regioes_historico.csv`: totais por cinco regiões conforme reportados pelo Smart Sampa.
- `cameras_municipio_historico.csv`: marcos municipais conhecidos.
- `sources.csv`: registro de proveniência.

### `external/`

Criado localmente pelos scripts e ignorado pelo Git. Guarda:

- XLSX anuais da SSP-SP;
- geometrias baixadas do GeoSampa;
- intermediários em nível de BO com coordenadas/endereço.

Esses arquivos não são necessários no histórico do Git e não devem ser publicados automaticamente.

### `processed/`

Tabelas derivadas adequadas ao versionamento e à análise.

Atual:

- `subprefeituras_cameras_populacao_area_2025_09.csv`.

Quando o pipeline SSP+GeoSampa for executado com os arquivos oficiais, também serão gerados:

- `ssp_cellphones_by_subpref_month.csv`;
- `ssp_cellphones_by_district_month.csv`.

## Princípios de qualidade

- Toda observação deve manter referência a `source_id` quando possível.
- Lacunas históricas não são preenchidas por interpolação.
- A contagem de câmeras é um **estoque dinâmico de equipamentos conectados**; integrações privadas podem entrar e sair do sistema.
- O ano do arquivo da SSP é tratado como ano de registro do BO; o período analítico usa `DATA_OCORRENCIA_BO`.
- O campo textual `BAIRRO` da SSP não é usado como chave administrativa. Distrito e subprefeitura são obtidos por spatial join das coordenadas com os limites oficiais do GeoSampa.
- Microdados localizáveis permanecem fora do repositório; apenas agregados territoriais necessários à análise são candidatos a commit.
