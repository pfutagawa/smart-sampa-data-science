-- Smart Sampa portfolio project — relational schema
PRAGMA foreign_keys=ON;

CREATE TABLE sources (
  source_id INTEGER PRIMARY KEY,
  dataset TEXT NOT NULL,
  publisher TEXT NOT NULL,
  url TEXT NOT NULL,
  published_or_reference_date TEXT,
  accessed_on TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE subprefeituras (
  subprefeitura_id INTEGER PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  regiao_administrativa TEXT,
  populacao_2022 INTEGER NOT NULL,
  area_km2 REAL NOT NULL,
  source_id_population INTEGER NOT NULL REFERENCES sources(source_id),
  source_id_area INTEGER NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE camera_subpref_snapshots (
  snapshot_id INTEGER PRIMARY KEY,
  subprefeitura_id INTEGER NOT NULL REFERENCES subprefeituras(subprefeitura_id),
  reference_period TEXT NOT NULL,
  camera_count INTEGER NOT NULL CHECK(camera_count >= 0),
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  notes TEXT,
  UNIQUE(subprefeitura_id, reference_period, source_id)
);

CREATE TABLE camera_region_snapshots (
  snapshot_id INTEGER PRIMARY KEY,
  reference_period TEXT NOT NULL,
  regiao_reportada TEXT NOT NULL,
  camera_count INTEGER NOT NULL CHECK(camera_count >= 0),
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  notes TEXT
);

CREATE TABLE camera_city_snapshots (
  snapshot_id INTEGER PRIMARY KEY,
  reference_period TEXT NOT NULL,
  camera_count INTEGER NOT NULL CHECK(camera_count >= 0),
  public_camera_count INTEGER,
  private_integrated_count INTEGER,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  notes TEXT
);

CREATE TABLE crime_subpref_month (
  crime_id INTEGER PRIMARY KEY,
  subprefeitura_id INTEGER NOT NULL REFERENCES subprefeituras(subprefeitura_id),
  occurrence_year INTEGER NOT NULL,
  occurrence_month INTEGER NOT NULL CHECK(occurrence_month BETWEEN 1 AND 12),
  cellphone_subtractions_total INTEGER NOT NULL CHECK(cellphone_subtractions_total >= 0),
  robberies INTEGER NOT NULL CHECK(robberies >= 0),
  thefts INTEGER NOT NULL CHECK(thefts >= 0),
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  UNIQUE(subprefeitura_id, occurrence_year, occurrence_month, source_id)
);

CREATE TABLE crime_district_month (
  crime_id INTEGER PRIMARY KEY,
  district_name TEXT NOT NULL,
  occurrence_year INTEGER NOT NULL,
  occurrence_month INTEGER NOT NULL CHECK(occurrence_month BETWEEN 1 AND 12),
  cellphone_subtractions_total INTEGER NOT NULL CHECK(cellphone_subtractions_total >= 0),
  robberies INTEGER NOT NULL CHECK(robberies >= 0),
  thefts INTEGER NOT NULL CHECK(thefts >= 0),
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  UNIQUE(district_name, occurrence_year, occurrence_month, source_id)
);

CREATE TABLE dataset_registry (
  dataset_id INTEGER PRIMARY KEY,
  dataset_name TEXT NOT NULL,
  source_id INTEGER REFERENCES sources(source_id),
  temporal_coverage TEXT,
  format TEXT,
  ingestion_status TEXT NOT NULL,
  notes TEXT
);

CREATE VIEW vw_subpref_cameras_2025_09 AS
SELECT
  s.nome AS subprefeitura,
  s.regiao_administrativa,
  s.populacao_2022,
  s.area_km2,
  cs.camera_count AS cameras_2025_09,
  ROUND(cs.camera_count * 10000.0 / s.populacao_2022, 2) AS cameras_por_10_mil_hab_pop2022,
  ROUND(cs.camera_count * 1.0 / s.area_km2, 2) AS cameras_por_km2_area2025,
  ROUND(cs.camera_count * 100.0 / 40000, 3) AS participacao_cameras_cidade_pct,
  RANK() OVER (ORDER BY cs.camera_count DESC) AS rank_cameras_absoluto,
  RANK() OVER (ORDER BY cs.camera_count * 1.0 / s.populacao_2022 DESC) AS rank_cameras_per_capita,
  RANK() OVER (ORDER BY cs.camera_count * 1.0 / s.area_km2 DESC) AS rank_cameras_densidade
FROM subprefeituras s
JOIN camera_subpref_snapshots cs ON cs.subprefeitura_id = s.subprefeitura_id
WHERE cs.reference_period = '2025-09' AND cs.source_id = 1;

CREATE VIEW vw_camera_subpref_history AS
SELECT
  s.nome AS subprefeitura,
  cs.reference_period,
  cs.camera_count,
  cs.source_id,
  cs.notes
FROM camera_subpref_snapshots cs
JOIN subprefeituras s ON s.subprefeitura_id = cs.subprefeitura_id;

CREATE VIEW vw_crime_subpref_2025 AS
SELECT
  s.nome AS subprefeitura,
  SUM(c.cellphone_subtractions_total) AS celulares_subtraidos_2025,
  SUM(c.robberies) AS roubos_2025,
  SUM(c.thefts) AS furtos_2025,
  ROUND(SUM(c.cellphone_subtractions_total) * 100000.0 / s.populacao_2022, 2)
    AS celulares_subtraidos_por_100_mil_pop2022
FROM crime_subpref_month c
JOIN subprefeituras s ON s.subprefeitura_id = c.subprefeitura_id
WHERE c.occurrence_year = 2025
GROUP BY s.subprefeitura_id, s.nome, s.populacao_2022;

-- Comparação transversal: câmeras (snapshot set/2025) versus ocorrências no ano de 2025.
-- Esta view é descritiva e não estima efeito causal do Smart Sampa.
CREATE VIEW vw_camera_crime_subpref_2025 AS
SELECT
  cam.subprefeitura,
  cam.regiao_administrativa,
  cam.populacao_2022,
  cam.area_km2,
  cam.cameras_2025_09,
  cam.cameras_por_10_mil_hab_pop2022,
  cam.cameras_por_km2_area2025,
  crime.celulares_subtraidos_2025,
  crime.roubos_2025,
  crime.furtos_2025,
  crime.celulares_subtraidos_por_100_mil_pop2022
FROM vw_subpref_cameras_2025_09 cam
LEFT JOIN vw_crime_subpref_2025 crime
  ON crime.subprefeitura = cam.subprefeitura;
