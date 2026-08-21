# Metodologia e decisões de modelagem

## 1. Unidade de análise

A etapa inicial descreve **como a cobertura do Smart Sampa se distribui pelas 32 subprefeituras de São Paulo**, porque essa é a fotografia territorial mais completa encontrada publicamente para as câmeras (setembro de 2025).

Os microdados da SSP-SP, porém, incluem latitude e longitude do local do fato. Por isso, a criminalidade pode ser atribuída espacialmente tanto às **subprefeituras** quanto aos **96 distritos municipais** por meio dos limites oficiais do GeoSampa.

O campo `BAIRRO` da SSP não é usado como chave administrativa: nomes de bairros são informais, podem variar e não correspondem necessariamente aos limites oficiais. A unidade territorial é atribuída pelas coordenadas do fato através de *spatial join*.

## 2. Smart Sampa

A contagem de câmeras representa um **estoque dinâmico de equipamentos conectados**, e não um acumulado monotônico de instalações. Câmeras privadas integradas podem entrar ou sair do sistema.

A fotografia completa das 32 subprefeituras em setembro de 2025 soma **40.000 câmeras**, exatamente o total municipal divulgado oficialmente para o mesmo período, funcionando como validação cruzada.

### Indicadores atuais

**Câmeras por 10 mil habitantes**

`câmeras em setembro/2025 ÷ população do Censo 2022 × 10.000`

O denominador não é contemporâneo à contagem de câmeras; o nome da variável registra explicitamente essa diferença temporal.

**Câmeras por km²**

`câmeras em setembro/2025 ÷ área oficial da subprefeitura em 2025`

Este indicador mede densidade espacial, mas não controla população flutuante, uso comercial do solo, concentração de câmeras privadas ou critérios operacionais de implantação.

## 3. SSP-SP — celulares subtraídos

A SSP-SP disponibiliza arquivos anuais de celulares subtraídos. O esquema observado contém, entre outros, os campos:

- `NOME_DELEGACIA`, `ANO_BO`, `NUM_BO` e `VERSAO`;
- `DATA_OCORRENCIA_BO`;
- `RUBRICA`;
- `CIDADE`, `BAIRRO`, `LOGRADOURO` e `NUMERO_LOGRADOURO`;
- `LATITUDE` e `LONGITUDE`.

### Regra temporal

O ano no nome do XLSX corresponde ao **ano de registro do BO**, não necessariamente ao ano do fato. Há ocorrências de dezembro registradas em janeiro do ano seguinte.

Por isso, para analisar o ano `t`, o pipeline pode ler também o arquivo de `t+1` e só então filtrar por `DATA_OCORRENCIA_BO`. Exemplo para 2025:

```bash
python src/ingest_ssp_cellphones.py \
  --download-years 2025 2026 \
  --occurrence-years 2025
```

### Município

A SSP usa variantes como `S.PAULO`, `São Paulo` e `SAO PAULO`. O ETL normaliza esses valores antes do filtro para evitar exclusão silenciosa de ocorrências da capital.

### Deduplicação

A chave de BO utilizada é:

`NOME_DELEGACIA + ANO_BO + NUM_BO`

Como um mesmo BO pode aparecer em versões diferentes, o pipeline mantém primeiro a maior `VERSAO`. Depois reduz o BO a uma única observação analítica e registra se a rubrica contém roubo, furto ou ambos.

A contagem final é feita por **BO único**, não por linha da planilha nem por objeto listado.

## 4. Coordenadas e associação territorial

Latitude e longitude são convertidas para valores numéricos e submetidas a uma validação geográfica básica para a região de São Paulo. Registros sem coordenadas válidas permanecem fora do *spatial join* e a taxa de cobertura deve ser reportada na análise.

Os limites administrativos são obtidos diretamente do WFS oficial do GeoSampa:

- `geoportal:subprefeitura`;
- `geoportal:distrito_municipal`.

O script `src/download_geosampa.py` baixa as duas camadas e as converte para EPSG:4326. Em seguida, `src/spatial_join_crimes.py` atribui cada ocorrência georreferenciada aos polígonos por relação espacial `within`.

O pipeline gera agregados mensais por:

- subprefeitura;
- distrito.

Antes de qualquer interpretação, devem ser verificadas a porcentagem de BOs com coordenadas válidas e a taxa de sucesso dos dois *spatial joins*.

## 5. Minimização e versionamento dos dados

Os XLSX originais da SSP e os intermediários em nível de ocorrência, que contêm coordenadas e endereços, ficam em `data/external/` e são ignorados pelo Git.

O repositório deve versionar apenas os **agregados territoriais necessários à análise**, reduzindo volume e evitando redistribuição desnecessária de microdados localizáveis.

## 6. Inferência

Nesta fase, o projeto é **descritivo e associativo**. Diferenças entre cobertura de câmeras e criminalidade não serão apresentadas como efeito causal do Smart Sampa.

Uma eventual análise antes/depois ou painel temporal deverá discutir explicitamente endogeneidade: regiões com mais crimes podem receber mais câmeras, e outros fatores podem afetar simultaneamente implantação e registros criminais.
