# Metodologia e decisões de modelagem

## Pergunta de pesquisa

A etapa inicial pergunta **como a cobertura do Smart Sampa se distribui territorialmente** e se essa distribuição acompanha, em etapas posteriores, a distribuição de roubos e furtos de celulares.

Nesta fase, o projeto é **descritivo e exploratório**. Não atribui causalidade entre câmeras e criminalidade.

## Unidade territorial

A fotografia mais completa encontrada publicamente para câmeras é a **subprefeitura** (32 unidades), com referência em setembro de 2025. O mapa futuro poderá usar distritos (96 unidades) apenas se a granularidade dos dados de câmeras permitir uma desagregação válida.

## Indicadores atuais

### Câmeras por 10 mil habitantes

`câmeras em setembro/2025 ÷ população do Censo 2022 × 10.000`

O denominador não é contemporâneo à contagem de câmeras. O nome da variável registra explicitamente esse fato.

### Câmeras por km²

`câmeras em setembro/2025 ÷ área oficial da subprefeitura em 2025`

Este indicador mede densidade espacial, mas não controla circulação diária de pessoas, uso comercial do solo ou concentração de câmeras privadas.

## Proveniência e qualidade

A tabela completa por subprefeitura foi publicada pelo Metrópoles com base em resposta obtida via LAI. Sua soma (40.000) coincide com o total municipal anunciado oficialmente para setembro/2025, funcionando como validação cruzada.

Os agregados por cinco regiões reportados pelo Smart Sampa não são automaticamente tratados como a mesma regionalização administrativa da Prefeitura. Como as somas não se reconciliam, os dois recortes permanecem separados no banco.

## Próxima etapa

1. Inspecionar os XLSX anuais de celulares subtraídos da SSP-SP.
2. Definir chave de BO e regras de deduplicação com base no esquema real.
3. Obter geometria oficial do GeoSampa.
4. Geocodificar/agregar ocorrências somente com critérios reproduzíveis.
5. Criar tabela `subprefeitura × mês × tipo de ocorrência`.
6. Integrar criminalidade ao banco e produzir mapa interativo.
