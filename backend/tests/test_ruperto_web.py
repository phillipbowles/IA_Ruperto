"""El router `/api/v1/ruperto` (la pestaña «Hablar con Ruperto») con TestClient:
base SQLite del fixture, Gemini falso y ElevenLabs por `httpx.MockTransport`."""
import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from conftest import GeminiFalso, cargar
from fastapi.testclient import TestClient
from test_bot_voz import AUDIO, MP3, PREGUNTA, Eleven, cliente_falso, err

from app.bot import persona, prompt, recuperar, voz
from app.bot import responder as responder_mod
from app.database import get_db
from app.main import app
from app.models import Conversacion
from app.routers import ruperto

URL = "/api/v1/ruperto"
WEBM = {"content-type": "audio/webm;codecs=opus"}
CLASES = {"saludable", "estresada", "marchita"}


@pytest.fixture
def web(db, monkeypatch):
    """La app con todo lo externo falso. Nada de lo que hay en el .env entra."""
    for v in ("ELEVENLABS_VOZ_ID", "ELEVENLABS_MODELO_TTS", "ELEVENLABS_MODELO_STT", "ELEVENLABS_URL",
              "VOZ_MAX_CHARS_DIA", "VOZ_MAX_AUDIOS_DIA", "RUPERTO_WEB_POR_MINUTO",
              "RUPERTO_WEB_POR_HORA", "RUPERTO_WEB_GLOBAL_POR_MINUTO", "RUPERTO_WEB_GLOBAL_POR_DIA"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    eleven = Eleven()
    cliente = cliente_falso(eleven)
    monkeypatch.setattr(voz, "cliente", lambda: cliente)
    monkeypatch.setattr(voz, "configurada", lambda env=None: True)
    gemini = GeminiFalso()
    monkeypatch.setattr(responder_mod, "_gemini_default", lambda: gemini)
    monkeypatch.setattr(responder_mod, "_memoria", prompt.Memoria())
    monkeypatch.setattr(recuperar, "buscar", lambda *a, **k: [])
    monkeypatch.setattr(recuperar, "recientes", lambda *a, **k: [])
    ruperto._pedidos.clear()
    ruperto._todos.clear()
    voz.reiniciar()
    app.dependency_overrides[get_db] = lambda: db
    yield SimpleNamespace(c=TestClient(app), db=db, eleven=eleven, voz=cliente, gemini=gemini,
                          mp=monkeypatch)
    app.dependency_overrides.pop(get_db, None)
    ruperto._pedidos.clear()
    ruperto._todos.clear()
    voz.reiniciar()


def sin_voz(web):
    web.mp.delenv("ELEVENLABS_API_KEY")
    web.mp.setattr(voz, "configurada", lambda env=None: False)


def recientes(db, suelos):
    """Una serie que termina hace 2 minutos (los sensores no están caídos)."""
    paso = timedelta(minutes=5)
    return cargar(db, suelos, t0=datetime.now(UTC) - timedelta(minutes=2) - paso * (len(suelos) - 1))


# ─── chat_id de la web ────────────────────────────────────────────────────
def test_chat_id_web_estable_negativo_y_fuera_del_rango_de_telegram():
    a = ruperto.chat_id_web("sesion-a", "1.1.1.1")
    assert a == ruperto.chat_id_web("sesion-a", "9.9.9.9")       # la sesión manda, no la IP
    assert a != ruperto.chat_id_web("sesion-b", "1.1.1.1")
    for sesion, ip in [("sesion-a", "x"), ("", "1.1.1.1"), (None, "1.1.1.1"), ("ñ" * 500, "x"),
                       *[(f"s{i}", "x") for i in range(200)]]:
        cid = ruperto.chat_id_web(sesion, ip)
        assert -2 * 10**15 < cid <= -10**15 and ruperto.es_chat_web(cid)
        assert cid >= -(2**63)                                    # entra en el BigInteger
    assert len({ruperto.chat_id_web(f"s{i}", "x") for i in range(200)}) == 200


def test_chat_id_web_sin_sesion_sale_de_la_ip():
    assert ruperto.chat_id_web(None, "1.1.1.1") == ruperto.chat_id_web("", "1.1.1.1")
    assert ruperto.chat_id_web(None, "1.1.1.1") != ruperto.chat_id_web(None, "2.2.2.2")
    assert not ruperto.es_chat_web(123456789) and not ruperto.es_chat_web(-1001234567890)


# ─── GET /estado ──────────────────────────────────────────────────────────
def test_estado_sin_datos(web):
    r = web.c.get(f"{URL}/estado")
    assert r.status_code == 200
    assert r.json() == {"nombre": "Ruperto", "estado": None, "sensores_caidos": True, "edad_min": None,
                        "tierra": None, "temperatura_c": None, "humedad_pct": None,
                        "h_desde_riego": None, "voz": True, "chat": True,
                        "saludo": persona.SALUDO_VOZ}


def test_estado_sin_claves(web):
    sin_voz(web)
    web.mp.setenv("GEMINI_API_KEY", "  ")
    j = web.c.get(f"{URL}/estado").json()
    assert j["voz"] is False and j["chat"] is False


def test_estado_si_el_cliente_de_voz_no_se_puede_crear(web):
    def roto():
        raise voz.SinVoz("falta ELEVENLABS_API_KEY")
    web.mp.setattr(voz, "cliente", roto)
    assert web.c.get(f"{URL}/estado").json()["voz"] is False


def test_estado_con_datos_recientes(web):
    recientes(web.db, [1500.0] * 24)
    j = web.c.get(f"{URL}/estado").json()
    assert j["sensores_caidos"] is False and j["estado"] in CLASES
    assert j["edad_min"] in (1, 2, 3) and j["tierra"] == "húmeda"
    assert (j["temperatura_c"], j["humedad_pct"]) == (22.0, 55.0)
    assert j["h_desde_riego"] is None                    # la sonda no vio ningún riego


def test_estado_con_un_riego_detectado(web):
    recientes(web.db, [2100.0] * 12 + [1500.0] * 12)     # caída ≥ 250 mV hace ~1 h
    j = web.c.get(f"{URL}/estado").json()
    assert j["h_desde_riego"] is not None and 0.5 <= j["h_desde_riego"] <= 1.5
    assert j["h_desde_riego"] == round(j["h_desde_riego"], 1)


def test_estado_con_sensores_caidos_no_dice_como_esta(web):
    cargar(web.db, [1500.0] * 24)                         # T0: hace semanas
    j = web.c.get(f"{URL}/estado").json()
    assert j["sensores_caidos"] is True and j["estado"] is None
    assert j["edad_min"] > 60 and j["tierra"] == "húmeda"   # lo último que se supo sí va


def test_estado_no_gasta_voz_ni_gemini_ni_cupo(web):
    for _ in range(30):
        assert web.c.get(f"{URL}/estado").status_code == 200
    assert web.eleven.pedidos == [] and web.gemini.prompts_clasificar == []
    assert not ruperto._pedidos


# ─── POST /hablar ─────────────────────────────────────────────────────────
def test_hablar_camino_feliz(web):
    recientes(web.db, [1500.0] * 24)
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers={**WEBM, "X-Ruperto-Sesion": "abc"})
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"pregunta", "respuesta", "estado", "en_dominio", "intencion", "audio_b64",
                      "audio_mime", "error_voz", "error", "latencia_ms"}
    assert j["pregunta"] == PREGUNTA and j["respuesta"] == "Soy Ruperto."
    assert base64.b64decode(j["audio_b64"]) == MP3 and j["audio_mime"] == "audio/mpeg"
    assert (j["en_dominio"], j["intencion"], j["error_voz"], j["error"]) == (True, "estado", None, None)
    assert j["estado"] in CLASES and j["latencia_ms"] >= 0
    # ElevenLabs recibió el audio con su tipo (sin los parámetros) y pidió mp3.
    stt, tts = web.eleven.pedidos
    assert AUDIO in stt.content and b"Content-Type: audio/webm\r\n" in stt.content
    assert tts.url.params["output_format"] == "mp3_44100_64"
    # Pasó por `responder` en modo voz y quedó logueado con el chat de la web.
    assert persona.NOTA_VOZ in web.gemini.llamadas_generar[0][1][-1]["text"]
    fila = web.db.query(Conversacion).one()
    assert fila.chat_id == ruperto.chat_id_web("abc", "testclient") and ruperto.es_chat_web(fila.chat_id)
    assert (fila.pregunta, fila.respuesta) == (PREGUNTA, "Soy Ruperto.")


def test_hablar_sin_sesion_usa_la_ip_como_chat(web):
    web.c.post(f"{URL}/hablar", content=AUDIO, headers={**WEBM, "X-Forwarded-For": "7.7.7.7"})
    assert web.db.query(Conversacion).one().chat_id == ruperto.chat_id_web(None, "7.7.7.7")


def test_sesiones_distintas_no_comparten_la_charla(web):
    for sesion in ("a", "b", "a"):
        web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?", "con_audio": False},
                   headers={"X-Ruperto-Sesion": sesion})
    ids = [f.chat_id for f in web.db.query(Conversacion).order_by(Conversacion.id)]
    assert ids[0] == ids[2] != ids[1]
    # La memoria corta es por sesión: sólo la segunda vuelta de «a» lleva historia.
    assert [len(ll[1]) for ll in web.gemini.llamadas_generar] == [1, 1, 3]


@pytest.mark.parametrize("falta, detalle", [("ELEVENLABS_API_KEY", "La voz no está disponible"),
                                            ("GEMINI_API_KEY", "GEMINI_API_KEY")])
def test_hablar_503_si_falta_una_clave(web, falta, detalle):
    if falta == "ELEVENLABS_API_KEY":
        sin_voz(web)
    else:
        web.mp.delenv(falta)
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 503 and detalle in r.json()["detail"]
    assert web.eleven.pedidos == [] and web.db.query(Conversacion).count() == 0
    assert not ruperto._pedidos and not ruperto._todos   # un 503 no gasta cupo, ni el global


@pytest.mark.parametrize("cabeceras", [{"content-type": "text/plain"}, {"content-type": "application/json"},
                                      {"content-type": "image/png"}, {}])
def test_hablar_415_si_no_es_audio(web, cabeceras):
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=cabeceras)
    assert r.status_code == 415 and web.eleven.pedidos == []


@pytest.mark.parametrize("tipo", sorted(ruperto.TIPOS_AUDIO))
def test_hablar_acepta_los_tipos_de_audio(web, tipo):
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers={"content-type": tipo.upper()})
    assert r.status_code == 200 and r.json()["pregunta"] == PREGUNTA


def test_hablar_413_si_el_audio_es_demasiado_largo(web):
    r = web.c.post(f"{URL}/hablar", content=b"x" * (ruperto.MAX_BYTES_AUDIO_WEB + 1), headers=WEBM)
    assert r.status_code == 413 and web.eleven.pedidos == []
    assert web.db.query(Conversacion).count() == 0
    r = web.c.post(f"{URL}/hablar", content=b"x" * ruperto.MAX_BYTES_AUDIO_WEB, headers=WEBM)
    assert r.status_code == 200 and r.json()["pregunta"] == PREGUNTA      # el borde entra


def test_el_limite_de_audio_de_la_web_es_mas_chico_que_el_de_la_voz():
    """Lo que el router deja pasar nunca lo rechaza después `transcribir` por tamaño."""
    assert ruperto.MAX_BYTES_AUDIO_WEB == 1_500_000 <= voz.MAX_BYTES_AUDIO


def test_hablar_400_si_el_audio_esta_vacio(web):
    r = web.c.post(f"{URL}/hablar", content=b"", headers=WEBM)
    assert r.status_code == 400 and web.eleven.pedidos == []


def test_hablar_no_se_entendio(web):
    web.eleven.stt = [{"text": "(ruido)"}]
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200
    j = r.json()
    assert (j["pregunta"], j["respuesta"], j["error_voz"]) == ("", persona.NO_ENTENDI, "no-se-entendio")
    assert (j["en_dominio"], j["intencion"], j["error"]) == (None, None, None)
    assert base64.b64decode(j["audio_b64"]) == MP3
    assert web.gemini.prompts_clasificar == [] and web.db.query(Conversacion).count() == 0


def test_hablar_un_toque_al_microfono_no_viaja_a_elevenlabs(web):
    r = web.c.post(f"{URL}/hablar", content=b"x" * 100, headers=WEBM)
    assert r.json()["error_voz"] == "no-se-entendio" and web.eleven.transcripciones == []


@pytest.mark.parametrize("tts, error", [(err(500), "error: _ErrorHttp"), (err(402), "sin-creditos")])
def test_hablar_si_falla_la_sintesis_el_texto_sale_igual(web, tts, error):
    web.eleven.tts = [tts]
    j = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).json()
    assert j["respuesta"] == "Soy Ruperto." and j["pregunta"] == PREGUNTA
    assert (j["audio_b64"], j["audio_mime"], j["error_voz"]) == (None, None, error)


def test_hablar_si_elevenlabs_no_oye(web):
    web.eleven.stt = [err(402)]
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200
    assert (r.json()["respuesta"], r.json()["error_voz"]) == (persona.SIN_OIDOS, "sin-creditos")


def test_hablar_error_de_gemini_va_en_el_json(web):
    from app.bot.gemini import SinCupo
    web.gemini.error_generar = SinCupo("cupo")
    j = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).json()
    assert j["respuesta"] == persona.SIN_ALIENTO and j["error"].startswith("429")
    assert base64.b64decode(j["audio_b64"]) == MP3


def test_hablar_si_el_estado_falla_la_charla_sale_igual(web):
    def roto(db):
        raise RuntimeError("base caída")
    web.mp.setattr(ruperto, "_estado", roto)
    r = web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?"})
    assert r.status_code == 200 and r.json()["estado"] is None and r.json()["respuesta"] == "Soy Ruperto."


# ─── POST /mensaje ────────────────────────────────────────────────────────
def test_mensaje_camino_feliz(web):
    r = web.c.post(f"{URL}/mensaje", json={"texto": "  ¿cómo estás?  "},
                   headers={"X-Ruperto-Sesion": "abc"})
    assert r.status_code == 200
    j = r.json()
    assert j["pregunta"] == "¿cómo estás?" and j["respuesta"] == "Soy Ruperto."
    assert base64.b64decode(j["audio_b64"]) == MP3 and j["audio_mime"] == "audio/mpeg"
    assert (j["en_dominio"], j["intencion"], j["error_voz"], j["error"], j["estado"]) == \
        (True, "estado", None, None, None)
    assert web.eleven.transcripciones == [] and len(web.eleven.sintesis) == 1
    fila = web.db.query(Conversacion).one()
    assert (fila.chat_id, fila.pregunta) == (ruperto.chat_id_web("abc", "testclient"), "¿cómo estás?")


def test_mensaje_sin_audio(web):
    j = web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?", "con_audio": False}).json()
    assert j["respuesta"] == "Soy Ruperto." and (j["audio_b64"], j["error_voz"]) == (None, None)
    assert web.eleven.pedidos == []


def test_mensaje_sin_voz_configurada_contesta_en_texto(web):
    sin_voz(web)
    r = web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?"})
    assert r.status_code == 200
    assert (r.json()["respuesta"], r.json()["audio_b64"], r.json()["error_voz"]) == \
        ("Soy Ruperto.", None, "sin-voz")


def test_mensaje_fuera_de_dominio(web):
    web.gemini.en_dominio, web.gemini.intencion = False, "otro"
    j = web.c.post(f"{URL}/mensaje", json={"texto": "una receta de ñoquis"}).json()
    assert j["respuesta"] in persona.RECHAZOS and j["en_dominio"] is False
    assert web.gemini.llamadas_generar == [] and base64.b64decode(j["audio_b64"]) == MP3


def test_mensaje_503_sin_gemini(web):
    web.mp.delenv("GEMINI_API_KEY")
    r = web.c.post(f"{URL}/mensaje", json={"texto": "hola"})
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]
    assert web.db.query(Conversacion).count() == 0


@pytest.mark.parametrize("cuerpo, estado", [
    ({"texto": "x" * (ruperto.MAX_TEXTO + 1)}, 422),
    ({"texto": ""}, 422),
    ({}, 422),
    ({"texto": 5}, 422),
    ({"texto": "   "}, 400),
])
def test_mensaje_invalido(web, cuerpo, estado):
    r = web.c.post(f"{URL}/mensaje", json=cuerpo)
    assert r.status_code == estado
    assert web.gemini.prompts_clasificar == [] and web.db.query(Conversacion).count() == 0
    assert not ruperto._pedidos and not ruperto._todos


def test_mensaje_en_el_borde_del_largo(web):
    r = web.c.post(f"{URL}/mensaje", json={"texto": "x" * ruperto.MAX_TEXTO, "con_audio": False})
    assert r.status_code == 200


# ─── límite por IP ────────────────────────────────────────────────────────
def mensaje(web, ip=None, sesion=None):
    cab = ({"X-Forwarded-For": ip} if ip else {}) | ({"X-Ruperto-Sesion": sesion} if sesion else {})
    return web.c.post(f"{URL}/mensaje", json={"texto": "hola", "con_audio": False}, headers=cab)


def test_limite_por_minuto_y_por_ip(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "2")
    assert [mensaje(web, "1.1.1.1").status_code for _ in range(3)] == [200, 200, 429]
    assert "respiro" in mensaje(web, "1.1.1.1").json()["detail"]
    # Otra IP tiene su propio cupo; la IP del cliente es la primera de X-Forwarded-For.
    assert mensaje(web, "2.2.2.2").status_code == 200
    assert mensaje(web, "1.1.1.1, 10.0.0.9").status_code == 429
    assert mensaje(web, "3.3.3.3, 1.1.1.1").status_code == 200
    # Cambiar de sesión no esquiva el límite: es por IP.
    assert mensaje(web, "1.1.1.1", sesion="otra").status_code == 429
    assert web.db.query(Conversacion).count() == 4          # los 429 no llegaron a Gemini


def test_limite_por_defecto(web):
    estados = [mensaje(web, "1.1.1.1").status_code for _ in range(ruperto.POR_MINUTO_DEFAULT + 1)]
    assert estados == [200] * ruperto.POR_MINUTO_DEFAULT + [429]


def test_limite_sin_cabeceras_usa_x_real_ip_o_el_socket(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    assert mensaje(web).status_code == 200 and mensaje(web).status_code == 429
    assert set(ruperto._pedidos) == {"testclient"}
    r = web.c.post(f"{URL}/mensaje", json={"texto": "hola", "con_audio": False},
                   headers={"X-Real-IP": "5.5.5.5"})
    assert r.status_code == 200 and "5.5.5.5" in ruperto._pedidos


def test_limite_por_minuto_se_libera_al_pasar_el_minuto(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "2")
    assert [mensaje(web, "1.1.1.1").status_code for _ in range(3)] == [200, 200, 429]
    cola = ruperto._pedidos["1.1.1.1"]
    viejos = [t - 61 for t in cola]
    cola.clear()
    cola.extend(viejos)
    assert mensaje(web, "1.1.1.1").status_code == 200


def test_limite_por_hora(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "100")
    web.mp.setenv("RUPERTO_WEB_POR_HORA", "3")
    assert [mensaje(web, "1.1.1.1").status_code for _ in range(4)] == [200, 200, 200, 429]
    cola = ruperto._pedidos["1.1.1.1"]
    viejos = [t - 600 for t in cola]                        # 10 min después siguen contando
    cola.clear()
    cola.extend(viejos)
    assert mensaje(web, "1.1.1.1").status_code == 429
    viejos = [t - 3601 for t in cola]                       # pasada la hora, no
    cola.clear()
    cola.extend(viejos)
    assert mensaje(web, "1.1.1.1").status_code == 200 and len(ruperto._pedidos["1.1.1.1"]) == 1


def test_limite_lo_comparten_hablar_y_mensaje(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "2")
    cab = {"X-Forwarded-For": "1.1.1.1"}
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers={**WEBM, **cab}).status_code == 200
    assert mensaje(web, "1.1.1.1").status_code == 200
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers={**WEBM, **cab})
    assert r.status_code == 429 and len(web.eleven.transcripciones) == 1


def test_limite_olvida_las_ips_que_no_vuelven(web):
    import time
    ahora = time.monotonic()
    for i in range(5001):
        ruperto._pedidos[f"vieja-{i}"].append(ahora - 4000)
    assert mensaje(web, "1.1.1.1").status_code == 200
    assert set(ruperto._pedidos) == {"1.1.1.1"}


# ─── GET /frase ───────────────────────────────────────────────────────────
def test_frase_saludo_y_cache(web):
    r = web.c.get(f"{URL}/frase/saludo")
    assert r.status_code == 200
    j = r.json()
    assert j["texto"] == persona.SALUDO_VOZ and j["audio_mime"] == "audio/mpeg"
    assert base64.b64decode(j["audio_b64"]) == MP3
    gastado = web.voz._chars_hoy
    assert web.c.get(f"{URL}/frase/saludo").json() == j
    assert len(web.eleven.sintesis) == 1 and web.voz._chars_hoy == gastado   # una sola vez por proceso


def test_frase_cosquillas_rota_por_n(web):
    textos = [web.c.get(f"{URL}/frase/cosquillas", params={"n": n}).json()["texto"] for n in range(5)]
    assert textos == [*persona.COSQUILLAS, persona.COSQUILLAS[0]]
    assert web.c.get(f"{URL}/frase/cosquillas").json()["texto"] == persona.COSQUILLAS[0]
    assert web.c.get(f"{URL}/frase/cosquillas", params={"n": -1}).json()["texto"] == persona.COSQUILLAS[-1]
    assert len(web.eleven.sintesis) == len(persona.COSQUILLAS)                # cada frase, una vez
    assert web.c.get(f"{URL}/frase/cosquillas", params={"n": "x"}).status_code == 422


def test_frase_cosquillas_cuando_esta_marchito(web):
    web.mp.setattr(ruperto, "_estado_seguro", lambda db: "marchita")
    assert web.c.get(f"{URL}/frase/cosquillas", params={"n": 3}).json()["texto"] == persona.COSQUILLAS_MAL[1]
    web.mp.setattr(ruperto, "_estado_seguro", lambda db: "estresada")
    assert web.c.get(f"{URL}/frase/cosquillas", params={"n": 3}).json()["texto"] == persona.COSQUILLAS[3]


@pytest.mark.parametrize("clave", ["insulto", "SALUDO", "saludo2"])
def test_frase_inexistente(web, clave):
    r = web.c.get(f"{URL}/frase/{clave}")
    assert r.status_code == 404 and web.eleven.pedidos == []


def test_frase_sin_voz_devuelve_solo_el_texto(web):
    sin_voz(web)
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    for _ in range(3):                                      # sin voz no gasta nada: no se limita
        r = web.c.get(f"{URL}/frase/saludo")
        assert r.status_code == 200
        assert r.json() == {"texto": persona.SALUDO_VOZ, "audio_b64": None, "audio_mime": None}
    assert web.eleven.pedidos == []


def test_frase_si_falla_la_sintesis_devuelve_solo_el_texto(web):
    web.eleven.tts = [err(402)]
    r = web.c.get(f"{URL}/frase/saludo")
    assert r.status_code == 200
    assert r.json() == {"texto": persona.SALUDO_VOZ, "audio_b64": None, "audio_mime": None}


def test_frase_no_necesita_gemini_ni_loguea(web):
    web.mp.delenv("GEMINI_API_KEY")
    assert web.c.get(f"{URL}/frase/saludo").status_code == 200
    assert web.gemini.prompts_clasificar == [] and web.db.query(Conversacion).count() == 0


def test_frase_no_tiene_limite_ni_gasta_el_de_la_charla(web):
    """Son pocas frases fijas y cada una se sintetiza una vez por proceso:
    tocar a Ruperto muchas veces no da 429 ni le saca cupo a /mensaje."""
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "1")
    cab = {"X-Forwarded-For": "1.1.1.1"}
    estados = [web.c.get(f"{URL}/frase/cosquillas", params={"n": n}, headers=cab).status_code
               for n in range(20)]
    estados += [web.c.get(f"{URL}/frase/saludo", headers=cab).status_code for _ in range(5)]
    assert estados == [200] * 25
    assert len(web.eleven.sintesis) == len(persona.COSQUILLAS) + 1
    assert not ruperto._pedidos and not ruperto._todos
    assert mensaje(web, "1.1.1.1").status_code == 200      # el cupo de la charla está intacto


def test_frase_sigue_andando_con_los_limites_agotados(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "1")
    assert [mensaje(web, "1.1.1.1").status_code for _ in range(2)] == [200, 429]
    r = web.c.get(f"{URL}/frase/saludo", headers={"X-Forwarded-For": "1.1.1.1"})
    assert r.status_code == 200 and base64.b64decode(r.json()["audio_b64"]) == MP3


def test_frases_fijas_son_pocas(web):
    """El supuesto que justifica no limitarlas: el gasto total está acotado."""
    assert ruperto.FRASES == ("saludo", "cosquillas")
    assert 1 + len(persona.COSQUILLAS) + len(persona.COSQUILLAS_MAL) == 7 <= voz.CACHE_FRASES


# ─── techo global (todas las IPs juntas) ──────────────────────────────────
def envejecer(cola, segundos):
    viejos = [t - segundos for t in cola]
    cola.clear()
    cola.extend(viejos)


def test_techo_global_por_minuto_lo_comparten_todas_las_ips(web):
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "3")
    assert [mensaje(web, f"1.1.1.{i}").status_code for i in range(3)] == [200] * 3
    r = mensaje(web, "9.9.9.9")                             # una IP que nunca habló
    assert r.status_code == 429 and "mucha gente" in r.json()["detail"]
    # El rechazado no queda anotado en ninguna de las dos estructuras.
    assert len(ruperto._todos) == 3 and not ruperto._pedidos.get("9.9.9.9")
    assert web.db.query(Conversacion).count() == 3 and len(web.gemini.prompts_clasificar) == 3
    # Rotar X-Forwarded-For no lo esquiva; al pasar el minuto se libera.
    assert [mensaje(web, f"8.8.8.{i}").status_code for i in range(5)] == [429] * 5
    assert len(ruperto._todos) == 3
    envejecer(ruperto._todos, 61)
    assert mensaje(web, "9.9.9.9").status_code == 200


def test_techo_global_por_minuto_por_defecto(web):
    n = ruperto.GLOBAL_POR_MINUTO_DEFAULT
    assert n == 30
    estados = [mensaje(web, f"10.0.0.{i}").status_code for i in range(n + 1)]
    assert estados == [200] * n + [429]


def test_techo_global_por_dia(web):
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "100")
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_DIA", "2")
    assert [mensaje(web, f"1.1.1.{i}").status_code for i in range(2)] == [200, 200]
    r = mensaje(web, "9.9.9.9")
    assert r.status_code == 429 and "mañana" in r.json()["detail"]
    assert len(ruperto._todos) == 2 and not ruperto._pedidos.get("9.9.9.9")
    envejecer(ruperto._todos, 3 * 3600)                     # tres horas después sigue cerrado
    assert mensaje(web, "9.9.9.9").status_code == 429
    envejecer(ruperto._todos, 86400)                        # al otro día, no
    assert mensaje(web, "9.9.9.9").status_code == 200 and len(ruperto._todos) == 1


def test_techo_global_por_dia_por_defecto(web):
    import time
    assert ruperto.GLOBAL_POR_DIA_DEFAULT == 600
    hace_una_hora = time.monotonic() - 3600
    ruperto._todos.extend([hace_una_hora] * 599)
    assert mensaje(web, "1.1.1.1").status_code == 200
    assert mensaje(web, "2.2.2.2").status_code == 429


def test_un_rechazo_por_ip_no_gasta_el_techo_global(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "2")
    assert [mensaje(web, "1.1.1.1").status_code for _ in range(4)] == [200, 429, 429, 429]
    assert len(ruperto._todos) == 1 and len(ruperto._pedidos["1.1.1.1"]) == 1
    assert mensaje(web, "2.2.2.2").status_code == 200       # el insistente no le cerró la puerta a otro


def test_el_techo_global_se_mira_antes_que_el_de_la_ip(web):
    web.mp.setenv("RUPERTO_WEB_POR_MINUTO", "1")
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "1")
    assert mensaje(web, "1.1.1.1").status_code == 200
    assert "mucha gente" in mensaje(web, "1.1.1.1").json()["detail"]
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_DIA", "1")        # y el del día antes que el del minuto
    assert "mañana" in mensaje(web, "1.1.1.1").json()["detail"]


def test_techo_global_lo_comparten_hablar_y_mensaje(web):
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "2")
    assert web.c.post(f"{URL}/hablar", content=AUDIO,
                      headers={**WEBM, "X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert mensaje(web, "2.2.2.2").status_code == 200
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers={**WEBM, "X-Forwarded-For": "3.3.3.3"})
    assert r.status_code == 429 and len(web.eleven.transcripciones) == 1


def test_estado_no_gasta_el_techo_global(web):
    web.mp.setenv("RUPERTO_WEB_GLOBAL_POR_MINUTO", "1")
    assert mensaje(web, "1.1.1.1").status_code == 200
    assert web.c.get(f"{URL}/estado").status_code == 200 and len(ruperto._todos) == 1


# ─── tope diario de audios (voz.py) visto desde la web ────────────────────
def test_hablar_con_el_tope_de_audios_agotado(web):
    web.voz.max_audios_dia = 1
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).json()["pregunta"] == PREGUNTA
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200
    j = r.json()
    assert (j["pregunta"], j["respuesta"], j["error_voz"], j["audio_b64"]) == \
        ("", persona.SIN_OIDOS, "sin-creditos", None)
    assert len(web.eleven.transcripciones) == 1 and web.db.query(Conversacion).count() == 1
    # Escribiendo se sigue pudiendo.
    assert web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?"}).json()["respuesta"] == "Soy Ruperto."


def test_hablar_si_elevenlabs_contesta_algo_que_no_es_json(web):
    web.eleven.stt = [(200, b"<html>502 Bad Gateway</html>")]
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200
    assert (r.json()["respuesta"], r.json()["error_voz"]) == (persona.SIN_OIDOS, "error: ErrorVoz")


# ─── voz fuera de servicio por un rato (voz.ClienteVoz.disponible) ────────
def caer(web):
    web.voz._anotar_caida(voz.SinCreditos("sin créditos"))
    assert web.voz.disponible is False


def levantar(web):
    web.voz._caida_hasta -= voz.PAUSA_SIN_VOZ_S + 1
    assert web.voz.disponible is True


def test_estado_dice_sin_voz_durante_la_pausa(web):
    caer(web)
    j = web.c.get(f"{URL}/estado").json()
    assert j["voz"] is False and j["chat"] is True
    levantar(web)
    assert web.c.get(f"{URL}/estado").json()["voz"] is True


def test_hablar_503_durante_la_pausa(web):
    caer(web)
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 503
    assert web.eleven.pedidos == [] and web.db.query(Conversacion).count() == 0
    assert not ruperto._pedidos and not ruperto._todos
    levantar(web)
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200 and base64.b64decode(r.json()["audio_b64"]) == MP3


def test_mensaje_contesta_en_texto_durante_la_pausa(web):
    caer(web)
    r = web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?"})
    assert r.status_code == 200
    j = r.json()
    assert (j["respuesta"], j["audio_b64"], j["audio_mime"], j["error_voz"]) == \
        ("Soy Ruperto.", None, None, "sin-voz")
    assert web.eleven.pedidos == [] and web.db.query(Conversacion).count() == 1


def test_frase_solo_texto_durante_la_pausa_aunque_este_cacheada(web):
    """Durante la pausa el front habla con la voz del navegador (`/estado` dice
    `voz: false`); la frase cacheada no se manda para no mezclar dos voces."""
    assert web.c.get(f"{URL}/frase/saludo").json()["audio_b64"]          # queda en el caché
    caer(web)
    r = web.c.get(f"{URL}/frase/saludo")
    assert r.status_code == 200
    assert r.json() == {"texto": persona.SALUDO_VOZ, "audio_b64": None, "audio_mime": None}
    assert web.c.get(f"{URL}/frase/cosquillas").json()["audio_b64"] is None
    assert len(web.eleven.sintesis) == 1
    levantar(web)
    assert base64.b64decode(web.c.get(f"{URL}/frase/saludo").json()["audio_b64"]) == MP3
    assert len(web.eleven.sintesis) == 1                                  # y sale del caché


@pytest.mark.parametrize("tts, error", [(err(402), "sin-creditos"), (err(401, "invalid_api_key"), "sin-voz"),
                                        (err(401, "quota_exceeded"), "sin-creditos")])
def test_una_sintesis_sin_creditos_abre_la_pausa_para_todos(web, tts, error):
    web.eleven.tts = [tts]
    j = web.c.post(f"{URL}/mensaje", json={"texto": "¿cómo estás?"}).json()
    assert (j["respuesta"], j["audio_b64"], j["error_voz"]) == ("Soy Ruperto.", None, error)
    antes = len(web.eleven.pedidos)
    assert web.c.get(f"{URL}/estado").json()["voz"] is False
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).status_code == 503
    assert web.c.post(f"{URL}/mensaje", json={"texto": "¿y ahora?"}).json()["error_voz"] == "sin-voz"
    assert web.c.get(f"{URL}/frase/saludo").json()["audio_b64"] is None
    assert len(web.eleven.pedidos) == antes                 # no se insiste contra ElevenLabs
    web.eleven.tts = [MP3]                                  # se recargaron los créditos y pasó la pausa
    levantar(web)
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200 and base64.b64decode(r.json()["audio_b64"]) == MP3


def test_una_transcripcion_rechazada_abre_la_pausa(web):
    web.eleven.stt = [err(401, "invalid_api_key")]
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert (r.status_code, r.json()["respuesta"], r.json()["error_voz"]) == (200, persona.SIN_OIDOS, "sin-voz")
    assert web.c.get(f"{URL}/estado").json()["voz"] is False
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).status_code == 503
    assert len(web.eleven.transcripciones) == 1


def test_los_topes_propios_abren_la_pausa(web):
    web.voz.max_audios_dia = 0
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).json()["error_voz"] == "sin-creditos"
    assert web.c.get(f"{URL}/estado").json()["voz"] is False
    # El tope propio no vuelve a los 10 minutos: dura hasta la medianoche UTC.
    web.voz._caida_hasta -= voz.PAUSA_SIN_VOZ_S + 1
    assert web.voz.disponible is False
    web.voz._caida_hasta = 0.0
    web.voz.max_chars_dia = 3
    assert web.c.post(f"{URL}/mensaje", json={"texto": "hola"}).json()["error_voz"] == "sin-creditos"
    assert web.c.get(f"{URL}/estado").json()["voz"] is False and web.eleven.pedidos == []


@pytest.mark.parametrize("cola, valor", [("tts", err(500)), ("stt", err(500)), ("stt", {"text": "(ruido)"}),
                                         ("stt", err(400, "invalid_audio"))])
def test_otros_errores_no_dejan_a_la_web_sin_voz(web, cola, valor):
    setattr(web.eleven, cola, [valor])
    assert web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM).status_code == 200
    assert web.c.get(f"{URL}/estado").json()["voz"] is True
    web.eleven.stt, web.eleven.tts = [{"text": PREGUNTA}], [MP3]
    r = web.c.post(f"{URL}/hablar", content=AUDIO, headers=WEBM)
    assert r.status_code == 200 and r.json()["audio_b64"]
