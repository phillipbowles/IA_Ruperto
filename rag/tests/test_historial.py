import pandas as pd

from rag.historial import cargar_serie, chunks_historial, riegos

from .conftest import RIEGO


def test_riego_detectado_con_la_regla_del_contrato(snapshot_chico, episodios_chico):
    df = cargar_serie(snapshot_chico, episodios_chico)
    assert list(riegos(df)) == [RIEGO]


def test_sin_caida_no_hay_riego(tmp_path, snapshot_chico, episodios_chico):
    raw = pd.read_csv(snapshot_chico)
    raw["suelo_mv"] = 1900.0
    ruta = tmp_path / "plano.csv"
    raw.to_csv(ruta, index=False)
    assert riegos(cargar_serie(ruta, episodios_chico)).empty


def test_maceta_02_se_une(snapshot_chico, episodios_chico):
    df = cargar_serie(snapshot_chico, episodios_chico)
    assert set(df.dispositivo) == {"maceta-01"}
    assert len(df) == 216
    assert set(df.boot_id) == {7, 1001}


def test_resumen_diario(snapshot_chico, episodios_chico):
    cs = chunks_historial(snapshot_chico, episodios_chico)
    dias = [c for c in cs if c.id.startswith("historial/dia-")]
    assert [c.id for c in dias] == ["historial/dia-2026-10-07#0", "historial/dia-2026-10-08#0"]
    assert [c.fecha for c in dias] == ["2026-10-07", "2026-10-08"]
    d7, d8 = (c.texto for c in dias)
    # 07/10 local: 09:00 → 23:55 = 180 muestras; 08/10: 00:00 → 02:55 = 36.
    assert "Muestras a 5 min: 180" in d7 and "de 09:00 a 23:55" in d7
    assert "Muestras a 5 min: 36" in d8
    assert "mín 1500" in d7 and "máx 1900" in d7
    assert "Riegos detectados (caída de la sonda ≥ 250 mV): 07/10 15:00." in d7
    assert "Riegos detectados: ninguno." in d8
    assert "Episodio 1: estresado (clase estresada, origen manual)" in d7 and "Sustrato seco" in d7
    assert "Episodio 2: saludable" in d7 and "Episodio 2: saludable" in d8
    assert "Temperatura del aire (DHT11): mín 20,0" in d7


def test_un_chunk_por_episodio(snapshot_chico, episodios_chico):
    cs = chunks_historial(snapshot_chico, episodios_chico)
    eps = [c for c in cs if c.id.startswith("historial/episodio-")]
    assert [c.id for c in eps] == ["historial/episodio-1#0", "historial/episodio-2#0"]
    e1, e2 = eps
    assert e1.fecha == "2026-10-07" and e1.titulo == "Episodio 1 (estresado)"
    assert "6,0 h" in e1.texto and "Muestras a 5 min: 72" in e1.texto
    assert "Riegos detectados en el episodio: ninguno" in e1.texto
    assert "07/10 15:00" in e2.texto
    assert all(c.fuente == "historial" and c.url is None for c in cs)
    # Los días van antes que los episodios, en orden.
    assert [c.id for c in cs].index("historial/episodio-1#0") == 2
