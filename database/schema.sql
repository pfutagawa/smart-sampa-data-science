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
