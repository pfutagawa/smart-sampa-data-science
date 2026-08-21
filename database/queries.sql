-- Consultas de showcase: execute com SQLite >= 3.25 (window functions).

-- 1) Ranking absoluto de câmeras em setembro/2025.
SELECT subprefeitura, cameras_2025_09
FROM vw_subpref_cameras_2025_09
ORDER BY cameras_2025_09 DESC;

-- 2) Cobertura per capita (câmeras de set/2025 / população do Censo 2022).
SELECT subprefeitura, populacao_2022, cameras_2025_09, cameras_por_10_mil_hab_pop2022
FROM vw_subpref_cameras_2025_09
ORDER BY cameras_por_10_mil_hab_pop2022 DESC;

-- 3) Densidade espacial de câmeras (câmeras de set/2025 / área oficial 2025).
SELECT subprefeitura, area_km2, cameras_2025_09, cameras_por_km2_area2025
FROM vw_subpref_cameras_2025_09
ORDER BY cameras_por_km2_area2025 DESC;

-- 4) Comparação de posições: volume absoluto vs. cobertura per capita.
SELECT
    subprefeitura,
    cameras_2025_09,
    rank_cameras_absoluto,
    cameras_por_10_mil_hab_pop2022,
    rank_cameras_per_capita,
    rank_cameras_absoluto - rank_cameras_per_capita AS diferenca_rank
FROM vw_subpref_cameras_2025_09
ORDER BY ABS(rank_cameras_absoluto - rank_cameras_per_capita) DESC;

-- 5) Participação de cada subprefeitura nas 40 mil câmeras de set/2025.
SELECT subprefeitura, participacao_cameras_cidade_pct
FROM vw_subpref_cameras_2025_09
ORDER BY participacao_cameras_cidade_pct DESC;

-- 6) Série parcial das subprefeituras com snapshots públicos adicionais.
SELECT *
FROM vw_camera_subpref_history
WHERE subprefeitura IN ('Mooca', 'Itaim Paulista')
ORDER BY subprefeitura, reference_period;

-- 7) Evolução municipal.
SELECT reference_period, camera_count, public_camera_count, private_integrated_count
FROM camera_city_snapshots
ORDER BY reference_period;

-- 8) Distribuição regional reportada pelo Smart Sampa.
SELECT reference_period, regiao_reportada, camera_count
FROM camera_region_snapshots
ORDER BY reference_period, camera_count DESC;

-- 9) CTE: subprefeituras acima da média municipal de cobertura per capita.
WITH media AS (
    SELECT AVG(cameras_por_10_mil_hab_pop2022) AS media_cobertura
    FROM vw_subpref_cameras_2025_09
)
SELECT v.subprefeitura, v.cameras_por_10_mil_hab_pop2022
FROM vw_subpref_cameras_2025_09 v
CROSS JOIN media m
WHERE v.cameras_por_10_mil_hab_pop2022 > m.media_cobertura
ORDER BY v.cameras_por_10_mil_hab_pop2022 DESC;

-- 10) Window function: participação acumulada das subprefeituras no estoque de câmeras.
SELECT
    subprefeitura,
    cameras_2025_09,
    ROUND(
        100.0 * SUM(cameras_2025_09) OVER (ORDER BY cameras_2025_09 DESC)
        / SUM(cameras_2025_09) OVER (), 2
    ) AS participacao_acumulada_pct
FROM vw_subpref_cameras_2025_09
ORDER BY cameras_2025_09 DESC;

-- 11) Ranking anual de subtrações de celulares por subprefeitura em 2025.
SELECT
    subprefeitura,
    celulares_subtraidos_2025,
    roubos_2025,
    furtos_2025,
    celulares_subtraidos_por_100_mil_pop2022
FROM vw_crime_subpref_2025
ORDER BY celulares_subtraidos_2025 DESC;

-- 12) Comparação transversal Smart Sampa × celulares subtraídos.
-- Snapshot de câmeras: setembro/2025; ocorrências: total do ano de 2025.
-- Uso exploratório: não interpretar como efeito causal.
SELECT
    subprefeitura,
    cameras_2025_09,
    cameras_por_10_mil_hab_pop2022,
    celulares_subtraidos_2025,
    celulares_subtraidos_por_100_mil_pop2022
FROM vw_camera_crime_subpref_2025
WHERE celulares_subtraidos_2025 IS NOT NULL
ORDER BY celulares_subtraidos_por_100_mil_pop2022 DESC;

-- 13) CTE + window functions: contraste entre ranking de vigilância e criminalidade.
WITH rankings AS (
    SELECT
        subprefeitura,
        cameras_por_10_mil_hab_pop2022,
        celulares_subtraidos_por_100_mil_pop2022,
        RANK() OVER (ORDER BY cameras_por_10_mil_hab_pop2022 DESC) AS rank_cameras,
        RANK() OVER (ORDER BY celulares_subtraidos_por_100_mil_pop2022 DESC) AS rank_crime
    FROM vw_camera_crime_subpref_2025
    WHERE celulares_subtraidos_por_100_mil_pop2022 IS NOT NULL
)
SELECT
    subprefeitura,
    cameras_por_10_mil_hab_pop2022,
    celulares_subtraidos_por_100_mil_pop2022,
    rank_cameras,
    rank_crime,
    rank_cameras - rank_crime AS diferenca_rank
FROM rankings
ORDER BY ABS(rank_cameras - rank_crime) DESC;
