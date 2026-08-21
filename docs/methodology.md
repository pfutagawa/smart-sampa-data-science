# Metodologia e decisões de modelagem

## 1. Unidade de análise

A etapa inicial descreve **como a cobertura do Smart Sampa se distribui pelas 32 subprefeituras de São Paulo**, porque essa é a fotografia territorial mais completa encontrada publicamente para as câmeras (setembro de 2025).

Os microdados da SSP-SP incluem latitude e longitude do local do fato. A criminalidade pode, portanto, ser atribuída espacialmente às **32 subprefeituras** e aos **96 distritos municipais** por meio dos limites oficiais do GeoSampa. O campo `BAIRRO` da SSP não é usado como chave administrativa.

## 2. Smart Sampa

A contagem de câmeras representa um **estoque dinâmico de equipamentos conectados**, e não um acumulado monotônico de instalações. Câmeras privadas integradas podem entrar ou sair do sistema.

A fotografia completa das 32 subprefeituras em setembro de 2025 soma **40.000 câmeras**, exatamente o total municipal divulgado oficialmente para o mesmo período.

### Indicadores atuais

**Câmeras por 10 mil habitantes**

`câmeras em setembro/2025 ÷ população do Censo 2022 × 10.000`

**Câmeras por km²**

`câmeras em setembro/2025 ÷ área oficial da subprefeitura em 2025`

A população residente é um denominador imperfeito especialmente em áreas centrais, que concentram grande população flutuante, comércio e turismo.

## 3. SSP-SP — celulares subtraídos

O esquema observado contém, entre outros, `NOME_DELEGACIA`, `ANO_BO`, `NUM_BO`, `VERSAO`, `DATA_OCORRENCIA_BO`, `RUBRICA`, endereço e coordenadas.

### Regra temporal

O ano no nome do XLSX corresponde ao **ano de registro do BO**, não necessariamente ao ano do fato. Para reconstruir 2025, o pipeline lê os arquivos de registro de 2025 e 2026 e só depois filtra `DATA_OCORRENCIA_BO` para 2025.

### Município e deduplicação

O ETL normaliza variantes como `S.PAULO`, `São Paulo` e `SAO PAULO`. A chave utilizada é:

`NOME_DELEGACIA + ANO_BO + NUM_BO`

Quando há mais de uma versão do mesmo BO, mantém-se a maior `VERSAO`. A unidade de contagem é o **BO único**, não a linha da planilha nem o número de objetos listados.

Os campos `roubos` e `furtos` nos agregados indicam presença da respectiva rubrica. Em 2025, 39 BOs espacialmente atribuídos possuem ambas; portanto essas duas colunas não devem ser somadas para reconstruir `subtracoes_total`.

## 4. Coordenadas, GeoSampa e cobertura espacial

Latitude e longitude são convertidas para valores numéricos e validadas para a região de São Paulo. Os limites administrativos vêm diretamente do WFS oficial do GeoSampa:

- `geoportal:subprefeitura` — 32 feições;
- `geoportal:distrito_municipal` — 96 feições.

O `spatial join` usa o predicado `within`. Diferenças de pontuação entre nomes territoriais (hífen, barra e apóstrofo) são normalizadas; diferenças semânticas permanecem em um pequeno de-para explícito.

### Cobertura observada em 2025

A execução reproduzível com os arquivos oficiais encontrou:

- **161.145 BOs únicos elegíveis** de roubo/furto de celular;
- **133.051 com coordenadas válidas** — 82,57%;
- **132.933 atribuídos a subprefeitura e distrito** — 82,49% de todos os BOs elegíveis e 99,91% dos casos com coordenadas válidas.

A cobertura de coordenadas permaneceu relativamente estável nos 12 meses, entre **81,85% e 83,35%**. O arquivo `data/processed/ssp_geocoding_quality_month.csv` preserva essas métricas mês a mês.

Por isso, mapas e taxas territoriais são descritos como referentes à **parcela geocodificada** dos registros, não à totalidade da criminalidade registrada.

## 5. Minimização e versionamento

Os XLSX originais da SSP e os intermediários em nível de ocorrência, que contêm coordenadas e endereços, ficam em `data/external/` e são ignorados pelo Git.

O repositório versiona apenas:

- agregados mensais por subprefeitura;
- agregados mensais por distrito;
- métricas agregadas de qualidade da geocodificação.

## 6. Limites da comparação Smart Sampa × criminalidade

A contagem de câmeras é uma fotografia de setembro de 2025, enquanto os crimes representam o ano de 2025. A comparação é **descritiva e associativa**, adequada para explorar coincidência espacial e alocação territorial, mas não para estimar o efeito causal das câmeras.

Entre os principais fatores de confusão estão:

- câmeras podem ser instaladas justamente onde há mais crimes;
- o estoque inclui câmeras privadas integradas;
- população residente não mede exposição diária ao risco em áreas de grande circulação;
- cerca de 17,5% dos BOs elegíveis não entram na análise espacial por falta de coordenadas válidas.

Uma análise longitudinal ou causal só deve ser considerada se obtivermos uma série histórica territorial confiável da implantação das câmeras.
