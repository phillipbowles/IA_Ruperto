"""Fixture: un snapshot crudo chico con el esquema de Railway y sus episodios.

18 h a 5 min (07/10 12:00 → 08/10 05:55 UTC = 09:00 del 07 → 02:55 del 08 en
Montevideo): la sonda en 1900 mV y un riego a las 18:00 UTC (cae a 1500 mV).
Las últimas 2 h llegan con el identificador viejo `maceta-02`, que se tiene
que unir a `maceta-01`.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
for p in (RAIZ, RAIZ / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

COLUMNAS = ["id", "dispositivo", "numero_muestra", "boot_id", "firmware_version", "ts_dispositivo",
            "ts_servidor", "temperatura_c", "humedad_ambiente_pct", "luz_raw", "luz_mv", "luz_pct",
            "suelo_raw", "suelo_mv", "suelo_pct", "termistor_raw", "termistor_mv", "temp_ntc_c",
            "condicion_codigo", "condicion_etiqueta", "etiqueta_origen", "wifi_rssi", "errores"]

INICIO = pd.Timestamp("2026-10-07 12:00", tz="UTC")
RIEGO = pd.Timestamp("2026-10-07 18:00", tz="UTC")
N = 216
ALIAS_DESDE = pd.Timestamp("2026-10-08 04:00", tz="UTC")


def _filas():
    filas = []
    for i in range(N):
        ts = INICIO + pd.Timedelta(minutes=5 * i)
        suelo = 1900.0 if ts < RIEGO else 1500.0
        alias = ts >= ALIAS_DESDE
        filas.append({
            "id": i + 1, "dispositivo": "maceta-02" if alias else "maceta-01",
            "numero_muestra": i, "boot_id": 1 if alias else 7, "firmware_version": "1.1.0",
            "ts_dispositivo": str(ts), "ts_servidor": str(ts + pd.Timedelta(seconds=3)),
            "temperatura_c": 20.0 + (i % 3), "humedad_ambiente_pct": 50.0,
            "luz_raw": 1000, "luz_mv": 900.0 + i, "luz_pct": 30.0,
            "suelo_raw": 2000, "suelo_mv": suelo, "suelo_pct": 40.0,
            "termistor_raw": 1000, "termistor_mv": 990.0, "temp_ntc_c": 24.0,
            "condicion_codigo": 1, "condicion_etiqueta": "saludable", "etiqueta_origen": "propagada",
            "wifi_rssi": -50, "errores": None,
        })
    return filas


@pytest.fixture
def snapshot_chico(tmp_path):
    ruta = tmp_path / "mediciones_raw_2026-10-08.csv"
    pd.DataFrame(_filas(), columns=COLUMNAS).to_csv(ruta, index=False)
    return ruta


@pytest.fixture
def episodios_chico(tmp_path):
    ruta = tmp_path / "episodios.csv"
    pd.DataFrame([
        {"episodio_id": 1, "dispositivo": "maceta-01", "ts_inicio": "2026-10-07T12:00:00Z",
         "ts_fin": "2026-10-07T18:00:00Z", "clase": "estresada", "origen": "manual",
         "autor": "test", "nota": "Sustrato seco antes del riego."},
        {"episodio_id": 2, "dispositivo": "maceta-01", "ts_inicio": "2026-10-07T18:00:00Z",
         "ts_fin": "2026-10-08T06:00:00Z", "clase": "saludable", "origen": "propagada",
         "autor": "test", "nota": ""},
    ]).to_csv(ruta, index=False)
    return ruta
