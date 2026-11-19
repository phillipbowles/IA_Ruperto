"""La voz de Ruperto (D219–D223) sin red: ElevenLabs es un `httpx.MockTransport`.

Cubre `texto_hablado`, `ClienteVoz` (oír, hablar, cupo, caché, elección de voz,
traducción de errores), `hablar`, `conversar` y el camino `voz=True` de
`responder` / `prompt.turno_usuario`.
"""
import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from conftest import GeminiFalso, cargar

from app.bot import persona, prompt, recuperar, voz
from app.bot.responder import responder
from app.models import Conversacion

MP3 = b"ID3\x04" + b"m" * 60
OGG = b"OggS" + b"o" * 60
AUDIO = b"a" * 2000            # un audio de micrófono cualquiera (≥ MIN_BYTES_AUDIO)
PREGUNTA = "¿Tenés sed, Ruperto?"


def correr(coro):
    return asyncio.run(coro)


class Eleven:
    """ElevenLabs falso. Cada cola (`stt`, `tts`, `lista`) es una lista de
    respuestas que se consumen en orden (la última se repite): bytes → audio,
    dict/list → JSON 200, (estado, cuerpo) → error, Exception → se levanta."""

    def __init__(self, stt=None, tts=None, lista=None):
        self.stt = list(stt) if stt is not None else [{"text": PREGUNTA}]
        self.tts = list(tts) if tts is not None else [MP3]
        self.lista = list(lista) if lista is not None else [
            {"voices": [{"voice_id": "otra"}, {"voice_id": voz.PREFERIDAS[1]}]}]
        self.pedidos: list[httpx.Request] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        ruta = pedido.url.path
        if ruta == "/v1/voices":
            cola = self.lista
        elif ruta == "/v1/speech-to-text":
            cola = self.stt
        elif ruta.startswith("/v1/text-to-speech/"):
            cola = self.tts
        else:
            return httpx.Response(404, json={"detail": "ruta desconocida"})
        r = cola.pop(0) if len(cola) > 1 else cola[0]
        if isinstance(r, Exception):
            raise r
        if isinstance(r, bytes):
            return httpx.Response(200, content=r)
        if isinstance(r, tuple):
            estado, cuerpo = r
            if isinstance(cuerpo, (dict, list)):
                return httpx.Response(estado, json=cuerpo)
            return httpx.Response(estado, content=cuerpo)
        return httpx.Response(200, json=r)

    def de(self, prefijo: str) -> list[httpx.Request]:
        return [p for p in self.pedidos if p.url.path.startswith(prefijo)]

    @property
    def sintesis(self) -> list[httpx.Request]:
        return self.de("/v1/text-to-speech/")

    @property
    def transcripciones(self) -> list[httpx.Request]:
        return self.de("/v1/speech-to-text")

    @property
    def listados(self) -> list[httpx.Request]:
        return self.de("/v1/voices")


def cliente_falso(eleven: Eleven, **kw) -> voz.ClienteVoz:
    kw.setdefault("voz_id", "voz-x")
    return voz.ClienteVoz(api_key="k", http=httpx.AsyncClient(transport=httpx.MockTransport(eleven)),
                          **kw)


def err(estado: int, codigo: str = "", mensaje: str = "x", clave: str = "status"):
    return (estado, {"detail": {clave: codigo, "message": mensaje}})


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Ni el .env del desarrollador ni el índice real entran a los tests."""
    for v in ("ELEVENLABS_API_KEY", "ELEVENLABS_VOZ_ID", "ELEVENLABS_MODELO_TTS",
              "ELEVENLABS_MODELO_STT", "ELEVENLABS_URL", "VOZ_MAX_CHARS_DIA", "VOZ_MAX_AUDIOS_DIA"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(recuperar, "recientes", lambda *a, **k: [])
    voz.reiniciar()
    yield
    voz.reiniciar()


def buscador(*frags):
    def f(consulta, k, fuentes):
        return list(frags)
    return f


def pasar_al_dia_siguiente(monkeypatch):
    class Maniana(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(days=1)
    monkeypatch.setattr(voz, "datetime", Maniana)


def deps(g=None):
    return {"gemini": g or GeminiFalso(), "buscar": buscador(), "memoria": prompt.Memoria()}


# ─── texto para ser escuchado ─────────────────────────────────────────────
def test_texto_hablado_saca_el_pie_de_fuentes():
    t = "Tengo sed.\n\n📚 Fuente: Universidad de Florida (UF/IFAS)"
    assert voz.texto_hablado(t) == "Tengo sed."
    assert voz.texto_hablado("Tengo sed.\n📚 Fuentes: A · B\n") == "Tengo sed."


def test_texto_hablado_saca_emojis():
    assert voz.texto_hablado("🟢 Estoy bien 🌱") == "Estoy bien."
    assert voz.texto_hablado("🎙️ ¡Hola! ⚠️ Cuidado ☀️") == "¡Hola! Cuidado."


def test_texto_hablado_vinetas_a_oraciones():
    t = ("Mis números:\n"
         "• Aire: 24,5 °C, 53 % de humedad\n"
         "- Tierra: 1500 mV · húmeda\n"
         "* Riego: hace 1 h\n"
         "· Luz: 800mV")
    assert voz.texto_hablado(t) == (
        "Mis números: Aire: 24,5 grados, 53 por ciento de humedad. "
        "Tierra: 1500 milivoltios, húmeda. Riego: hace 1 hora. Luz: 800 milivoltios.")


@pytest.mark.parametrize("crudo, hablado", [
    ("Hace 22°C", "Hace 22 grados."),
    ("Hace 22 ° C afuera", "Hace 22 grados afuera."),
    ("en °C", "en grados."),
    ("el valor en mV", "el valor en milivoltios."),
    ("HR 40%", "humedad 40 por ciento."),
    ("VPD 1,2 kPa", "déficit de presión de vapor 1,2 kilopascales."),
    ("hace 1 h", "hace 1 hora."),
    ("hace 3h", "hace 3 horas."),
    ("hace 21 h", "hace 21 horas."),
    ("hace 11 h", "hace 11 horas."),
    ("cada 5 min", "cada 5 minutos."),
    ("hace 1 min", "hace 1 minuto."),
    ("hace 1min", "hace 1 minuto."),
    ("hace 21 min", "hace 21 minutos."),
    ("hace 11 min", "hace 11 minutos."),
    ("hace 3,1 min", "hace 3,1 minutos."),
    ("hace 0.1 min", "hace 0.1 minutos."),
    ("hace 1 min y 1 h", "hace 1 minuto y 1 hora."),
    ("1 minuto", "1 minuto."),
    ("a 2–3 cm", "a 2 a 3 centímetros."),
    ("entre 18 — 24 grados", "entre 18 a 24 grados."),
    ("mi ESP32 mide", "mi E S P 32 mide."),
    ("mandá /estado o /riego", "mandá estado o riego."),
    ("1 hora", "1 hora."),                      # lo que ya está en palabras no se toca
    ("ahora mismo", "ahora mismo."),
])
def test_texto_hablado_unidades(crudo, hablado):
    assert voz.texto_hablado(crudo) == hablado


@pytest.mark.parametrize("crudo, hablado", [
    ("hace 1,1 h", "hace 1,1 horas."),
    ("hace 3,1 h", "hace 3,1 horas."),
    ("hace 0.1 h", "hace 0.1 horas."),
])
def test_texto_hablado_horas_con_decimales(crudo, hablado):
    """Sólo «1 h» exacto es singular: un decimal terminado en 1 va en plural."""
    assert voz.texto_hablado(crudo) == hablado


def test_texto_hablado_saca_markdown_y_signos():
    assert voz.texto_hablado("**Hola** _che_ `x` [dato] (nota) «cita» # fin") == \
        "Hola che x dato nota cita fin."


def test_texto_hablado_no_duplica_el_punto_final():
    assert voz.texto_hablado("¿Me regás?\n¡Dale!\nYa está…\nMirá:") == "¿Me regás? ¡Dale! Ya está… Mirá:"


def test_texto_hablado_corta_en_el_final_de_una_oracion():
    oraciones = [f"Esta es la oración número {i} de un texto largo." for i in range(40)]
    t = voz.texto_hablado(" ".join(oraciones), max_chars=200)
    assert len(t) <= 200 and t.endswith("largo.")
    assert " ".join(oraciones).startswith(t)
    # También corta en un signo de pregunta o de exclamación.
    t = voz.texto_hablado("¿Cómo estás hoy, querido Ruperto? " + "palabra " * 50, max_chars=60)
    assert t == "¿Cómo estás hoy, querido Ruperto?"
    t = voz.texto_hablado("¡Qué sed que tengo esta mañana! " + "palabra " * 50, max_chars=60)
    assert t == "¡Qué sed que tengo esta mañana!"
    # Una oración muy corta al principio no alcanza: se corta en una palabra.
    t = voz.texto_hablado("Hola. " + "palabra " * 50, max_chars=60)
    assert len(t) > 30 and t.endswith("palabra.")


def test_texto_hablado_largo_sin_oraciones_corta_en_una_palabra():
    t = voz.texto_hablado("palabra " * 300, max_chars=100)
    assert len(t) <= 101 and t.endswith("palabra.")
    assert len(voz.texto_hablado("palabra " * 300)) <= voz.MAX_CHARS_TTS + 1


def test_texto_hablado_corto_no_se_corta():
    t = "Estoy bien. " * 5
    assert voz.texto_hablado(t) == t.strip()


@pytest.mark.parametrize("crudo", ["", "   \n \n", "🌱🌱", "•", "** __", "🟢\n\n📚 Fuente: UF/IFAS"])
def test_texto_hablado_vacio(crudo):
    assert voz.texto_hablado(crudo) == ""


# ─── configuración ────────────────────────────────────────────────────────
def test_configurada_y_cliente_sin_clave(monkeypatch):
    assert voz.configurada({}) is False and voz.configurada({"ELEVENLABS_API_KEY": "  "}) is False
    assert voz.configurada({"ELEVENLABS_API_KEY": "k"}) is True
    assert voz.configurada() is False
    with pytest.raises(voz.SinVoz):
        voz.ClienteVoz()
    with pytest.raises(voz.SinVoz):
        voz.cliente()
    monkeypatch.setenv("ELEVENLABS_API_KEY", " k ")
    assert voz.configurada() is True
    c = voz.cliente()
    assert c.api_key == "k" and voz.cliente() is c       # uno solo por proceso
    voz.reiniciar()
    assert voz.cliente() is not c


def test_cliente_toma_la_configuracion_del_entorno(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    c = voz.ClienteVoz()
    assert (c.voz_id, c.modelo_tts, c.modelo_stt, c.url, c.max_chars_dia) == \
        (None, voz.MODELO_TTS_DEFAULT, voz.MODELO_STT_DEFAULT, voz.URL_DEFAULT, voz.MAX_CHARS_DIA_DEFAULT)
    monkeypatch.setenv("ELEVENLABS_VOZ_ID", "mi-voz")
    monkeypatch.setenv("ELEVENLABS_MODELO_TTS", "eleven_turbo_v2_5")
    monkeypatch.setenv("ELEVENLABS_URL", "https://eleven.test/")
    monkeypatch.setenv("VOZ_MAX_CHARS_DIA", "123")
    c = voz.ClienteVoz()
    assert (c.voz_id, c.modelo_tts, c.url, c.max_chars_dia) == \
        ("mi-voz", "eleven_turbo_v2_5", "https://eleven.test", 123)


# ─── oír (speech-to-text) ─────────────────────────────────────────────────
def test_transcribir_camino_feliz():
    e = Eleven(stt=[{"text": "  ¿Tenés   sed,\n Ruperto? "}])
    c = cliente_falso(e)
    assert correr(c.transcribir(AUDIO, "audio/webm;codecs=opus")) == "¿Tenés sed, Ruperto?"
    (p,) = e.pedidos
    assert p.method == "POST" and str(p.url) == "https://api.elevenlabs.io/v1/speech-to-text"
    assert p.headers["xi-api-key"] == "k"
    assert p.headers["content-type"].startswith("multipart/form-data")
    cuerpo = p.content
    assert b'name="model_id"\r\n\r\nscribe_v2' in cuerpo
    assert b'name="language_code"\r\n\r\nes' in cuerpo
    assert b'name="file"; filename="audio.webm"' in cuerpo and b"Content-Type: audio/webm\r\n" in cuerpo
    assert AUDIO in cuerpo


@pytest.mark.parametrize("mime, archivo", [
    ("audio/ogg", "audio.ogg"), ("AUDIO/MP4", "audio.m4a"), ("video/mp4", "audio.mp4"),
    ("audio/x-wav", "audio.wav"), ("application/x-raro", "audio.bin"), ("", "audio.webm"),
])
def test_transcribir_extension_segun_el_mime(mime, archivo):
    e = Eleven()
    correr(cliente_falso(e).transcribir(AUDIO, mime))
    assert f'filename="{archivo}"'.encode() in e.pedidos[0].content


def test_transcribir_audio_demasiado_corto_o_largo_no_llama():
    e = Eleven()
    c = cliente_falso(e)
    for audio in (b"", b"x" * (voz.MIN_BYTES_AUDIO - 1)):
        with pytest.raises(voz.NoSeEntendio):
            correr(c.transcribir(audio))
    with pytest.raises(voz.ErrorVoz) as ei:
        correr(c.transcribir(b"x" * (voz.MAX_BYTES_AUDIO + 1)))
    assert not isinstance(ei.value, voz.NoSeEntendio)
    assert e.pedidos == []
    assert correr(c.transcribir(b"x" * voz.MIN_BYTES_AUDIO)) == PREGUNTA      # el borde entra


@pytest.mark.parametrize("texto", ["", "   ", "...", "(risas)", "[música] (aplausos)", "1 2 3", "a", None])
def test_transcribir_sin_palabras(texto):
    c = cliente_falso(Eleven(stt=[{"text": texto}]))
    with pytest.raises(voz.NoSeEntendio):
        correr(c.transcribir(AUDIO))


def test_transcribir_respuesta_sin_campo_text():
    with pytest.raises(voz.NoSeEntendio):
        correr(cliente_falso(Eleven(stt=[{"language_code": "es"}])).transcribir(AUDIO))


def test_transcribir_saca_los_eventos_de_audio():
    c = cliente_falso(Eleven(stt=[{"text": "(risas) Hola Ruperto [música de fondo] ¿cómo estás? (tos)"}]))
    assert correr(c.transcribir(AUDIO)) == "Hola Ruperto ¿cómo estás?"


def test_transcribir_corta_a_600_caracteres():
    c = cliente_falso(Eleven(stt=[{"text": "hola " * 500}]))
    assert len(correr(c.transcribir(AUDIO))) == 600


@pytest.mark.parametrize("respuesta, clase", [
    (err(401, "invalid_api_key"), voz.SinVoz),
    (err(403, "forbidden"), voz.SinVoz),
    (err(402, "insufficient_credits", clave="code"), voz.SinCreditos),
    (err(402), voz.SinCreditos),
    (err(401, "quota_exceeded"), voz.SinCreditos),          # formato anterior
    (err(400, "quota_exceeded"), voz.SinCreditos),
    (err(400, "invalid_audio"), voz.NoSeEntendio),
    (err(422, "unprocessable"), voz.NoSeEntendio),
    ((422, {"detail": [{"loc": ["body", "file"], "msg": "field required"}]}), voz.NoSeEntendio),
    ((400, b"no es json"), voz.NoSeEntendio),
    (httpx.ConnectError("sin red"), voz.ErrorVoz),
    (httpx.ReadTimeout("lento"), voz.ErrorVoz),
    (err(500, "internal"), voz.ErrorVoz),
    (err(400, "invalid_model_id"), voz.ErrorVoz),            # el modelo, no el audio
])
def test_transcribir_traduce_los_errores(respuesta, clase):
    c = cliente_falso(Eleven(stt=[respuesta]))
    with pytest.raises(voz.ErrorVoz) as ei:
        correr(c.transcribir(AUDIO))
    assert type(ei.value) is clase or (clase is voz.ErrorVoz and not isinstance(
        ei.value, (voz.SinVoz, voz.SinCreditos, voz.NoSeEntendio)))


def test_error_con_detail_en_lista_conserva_el_mensaje():
    c = cliente_falso(Eleven(tts=[(422, {"detail": [{"loc": ["body", "text"], "msg": "muy largo"}]}),
                                  (422, {"detail": [{"loc": ["body", "text"], "msg": "muy largo"}]})]))
    with pytest.raises(voz.ErrorVoz) as ei:
        correr(c.sintetizar("hola"))
    assert "422" in str(ei.value) and "muy largo" in str(ei.value)


def test_error_de_red_no_filtra_la_clave():
    c = cliente_falso(Eleven(stt=[httpx.ConnectError("k secreta en la url")]))
    with pytest.raises(voz.ErrorVoz) as ei:
        correr(c.transcribir(AUDIO))
    assert str(ei.value) == "ElevenLabs no respondió: ConnectError"


# ─── hablar (text-to-speech) ──────────────────────────────────────────────
def test_sintetizar_forma_del_pedido():
    e = Eleven()
    c = cliente_falso(e)
    assert correr(c.sintetizar("Tengo 22 °C 🌱\n\n📚 Fuente: UF/IFAS")) == MP3
    (p,) = e.pedidos
    assert p.method == "POST"
    assert str(p.url) == "https://api.elevenlabs.io/v1/text-to-speech/voz-x?output_format=mp3_44100_64"
    assert p.headers["xi-api-key"] == "k" and p.headers["content-type"] == "application/json"
    cuerpo = json.loads(p.content)
    assert cuerpo["text"] == "Tengo 22 grados."           # lo hablado, no lo escrito
    assert cuerpo["model_id"] == "eleven_flash_v2_5" and cuerpo["language_code"] == "es"
    assert set(cuerpo) == {"text", "model_id", "language_code", "voice_settings"}
    assert set(cuerpo["voice_settings"]) == {"stability", "similarity_boost", "style", "use_speaker_boost"}


def test_sintetizar_formato_opus_y_deteccion_de_ogg():
    e = Eleven(tts=[OGG, b"\x00opus-pelado", OGG])
    c = cliente_falso(e)
    assert c.opus_es_ogg is None
    assert correr(c.sintetizar("hola", "opus")) == OGG and c.opus_es_ogg is True
    assert e.pedidos[0].url.params["output_format"] == "opus_48000_32"
    correr(c.sintetizar("hola", "opus"))
    assert c.opus_es_ogg is False
    correr(c.sintetizar("hola", "mp3"))                    # el mp3 no opina sobre el opus
    assert c.opus_es_ogg is False


def test_sintetizar_formato_desconocido():
    e = Eleven()
    with pytest.raises(KeyError):
        correr(cliente_falso(e).sintetizar("hola", "wav"))
    assert e.pedidos == []


@pytest.mark.parametrize("modelo, con_idioma", [
    ("eleven_flash_v2_5", True), ("eleven_turbo_v2_5", True),
    ("eleven_multilingual_v2", False), ("eleven_monolingual_v1", False),
])
def test_language_code_segun_el_modelo(modelo, con_idioma):
    e = Eleven()
    correr(cliente_falso(e, modelo_tts=modelo).sintetizar("hola"))
    cuerpo = json.loads(e.pedidos[0].content)
    assert cuerpo["model_id"] == modelo and ("language_code" in cuerpo) is con_idioma


def test_sintetizar_sin_nada_para_decir_no_llama_ni_gasta():
    e = Eleven()
    c = cliente_falso(e)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("🌱🌱"))
    assert e.pedidos == [] and c._chars_hoy == 0


def test_sintetizar_audio_vacio():
    with pytest.raises(voz.ErrorVoz):
        correr(cliente_falso(Eleven(tts=[b""])).sintetizar("hola"))


@pytest.mark.parametrize("respuesta, clase", [
    (err(401, "invalid_api_key"), voz.SinVoz),
    (err(402, "insufficient_credits", clave="code"), voz.SinCreditos),
    (err(401, "quota_exceeded"), voz.SinCreditos),
    (httpx.ConnectTimeout("lento"), voz.ErrorVoz),
    (err(500, "internal"), voz.ErrorVoz),
])
def test_sintetizar_traduce_los_errores(respuesta, clase):
    e = Eleven(tts=[respuesta])
    with pytest.raises(clase):
        correr(cliente_falso(e).sintetizar("hola"))
    assert len(e.sintesis) == 1                             # sin reintentos inútiles


# — elección de la voz —
def test_voz_preferida_si_la_cuenta_la_tiene():
    e = Eleven(lista=[{"voices": [{"voice_id": "otra"}, {"voice_id": voz.PREFERIDAS[2]},
                                  {"voice_id": voz.PREFERIDAS[0]}, {"name": "sin id"}]}])
    c = cliente_falso(e, voz_id=None)
    correr(c.sintetizar("hola"))
    correr(c.sintetizar("chau"))
    assert c.voz_id == voz.PREFERIDAS[0]                    # por orden de preferencia, no de la lista
    assert [p.url.path for p in e.pedidos] == ["/v1/voices"] + [f"/v1/text-to-speech/{voz.PREFERIDAS[0]}"] * 2
    assert e.listados[0].method == "GET" and e.listados[0].headers["xi-api-key"] == "k"


def test_voz_primera_de_la_cuenta_si_no_hay_preferida():
    e = Eleven(lista=[{"voices": [{"voice_id": "propia-1"}, {"voice_id": "propia-2"}]}])
    c = cliente_falso(e, voz_id=None)
    correr(c.sintetizar("hola"))
    assert c.voz_id == "propia-1" and e.sintesis[0].url.path == "/v1/text-to-speech/propia-1"


@pytest.mark.parametrize("lista", [
    err(401, "missing_permissions"), err(500), httpx.ConnectError("x"), {"voices": []}, {"voices": None}, {},
])
def test_voz_de_respaldo_si_no_se_puede_listar(lista):
    e = Eleven(lista=[lista])
    c = cliente_falso(e, voz_id=None)
    assert correr(c.sintetizar("hola")) == MP3
    assert c.voz_id == voz.VOZ_RESPALDO


def test_listar_voces_sin_creditos_no_cae_al_respaldo():
    e = Eleven(lista=[err(402)])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    assert e.sintesis == [] and c.voz_id is None and c._chars_hoy == 0


def test_voz_del_entorno_no_lista(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOZ_ID", "del-entorno")
    e = Eleven()
    c = voz.ClienteVoz(api_key="k", http=httpx.AsyncClient(transport=httpx.MockTransport(e)))
    correr(c.sintetizar("hola"))
    assert [p.url.path for p in e.pedidos] == ["/v1/text-to-speech/del-entorno"]


def test_404_de_la_voz_elige_de_nuevo_una_vez():
    e = Eleven(lista=[{"voices": [{"voice_id": "vieja"}]}, {"voices": [{"voice_id": "nueva"}]}],
               tts=[err(404, "voice_not_found"), MP3])
    c = cliente_falso(e, voz_id=None)
    assert correr(c.sintetizar("hola")) == MP3
    assert [p.url.path for p in e.pedidos] == ["/v1/voices", "/v1/text-to-speech/vieja",
                                               "/v1/voices", "/v1/text-to-speech/nueva"]
    assert c.voz_id == "nueva" and c._chars_hoy == len("hola.")       # el reintento no gasta doble
    assert "language_code" in json.loads(e.sintesis[1].content)         # ni pierde el idioma


def test_404_repetido_no_entra_en_un_bucle():
    e = Eleven(lista=[{"voices": [{"voice_id": "vieja"}]}], tts=[err(404, "voice_not_found")])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert len(e.sintesis) == 2 and len(e.listados) == 2


def test_404_con_voz_fija_no_la_cambia():
    e = Eleven(tts=[err(404, "voice_not_found")])
    c = cliente_falso(e, voz_id="fija")
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert c.voz_id == "fija" and e.listados == [] and len(e.sintesis) == 1


def test_404_del_modelo_no_cambia_la_voz():
    e = Eleven(tts=[err(404, "model_not_found")])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert len(e.listados) == 1 and len(e.sintesis) == 1


# — language_code rechazado —
def test_400_con_language_code_reintenta_sin_y_lo_recuerda():
    e = Eleven(tts=[err(400, "unsupported_language"), MP3])
    c = cliente_falso(e)
    assert correr(c.sintetizar("hola")) == MP3
    assert correr(c.sintetizar("chau")) == MP3
    cuerpos = [json.loads(p.content) for p in e.sintesis]
    assert ["language_code" in b for b in cuerpos] == [True, False, False]
    assert cuerpos[1]["text"] == "hola." and cuerpos[1]["model_id"] == "eleven_flash_v2_5"
    assert c._chars_hoy == len("hola.") + len("chau.")


def test_422_con_language_code_tambien_reintenta():
    e = Eleven(tts=[(422, {"detail": [{"loc": ["body", "language_code"], "msg": "no"}]}), MP3])
    assert correr(cliente_falso(e).sintetizar("hola")) == MP3
    assert len(e.sintesis) == 2


def test_400_sin_language_code_no_reintenta():
    e = Eleven(tts=[err(400, "invalid_text")])
    with pytest.raises(voz.ErrorVoz):
        correr(cliente_falso(e, modelo_tts="eleven_multilingual_v2").sintetizar("hola"))
    assert len(e.sintesis) == 1


def test_400_que_no_era_por_el_idioma_no_lo_apaga_para_siempre():
    """Si el reintento sin `language_code` falla igual, el problema era otro:
    los pedidos siguientes lo siguen mandando."""
    e = Eleven(tts=[err(400, "invalid_text"), err(400, "invalid_text"), MP3])
    c = cliente_falso(e)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert correr(c.sintetizar("chau")) == MP3
    assert ["language_code" in json.loads(p.content) for p in e.sintesis] == [True, False, True]


# — tope diario propio —
def test_tope_diario_y_reinicio_al_dia_siguiente(monkeypatch):
    e = Eleven()
    c = cliente_falso(e, max_chars_dia=12)
    correr(c.sintetizar("hola"))                            # "hola." = 5
    correr(c.sintetizar("chau"))                            # 10
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("otra"))                        # 15 > 12
    assert len(e.sintesis) == 2 and c._chars_hoy == 10      # el rechazado ni llama ni cuenta
    correr(c.sintetizar("y"))                               # "y." = 2 → 12, justo el tope
    assert c._chars_hoy == 12

    pasar_al_dia_siguiente(monkeypatch)
    assert correr(c.sintetizar("otra")) == MP3
    assert c._chars_hoy == 5 and c._dia == (datetime.now(UTC) + timedelta(days=1)).date().isoformat()


def test_tope_diario_cuenta_lo_hablado_no_lo_escrito():
    c = cliente_falso(Eleven())
    correr(c.sintetizar("Hola 🌱🌱🌱\n\n📚 Fuente: Universidad de Florida (UF/IFAS)"))
    assert c._chars_hoy == len("Hola.")


# — caché de frases fijas —
def test_fijo_cachea_y_no_gasta_dos_veces():
    e = Eleven()
    c = cliente_falso(e, max_chars_dia=len(voz.texto_hablado(persona.SALUDO_VOZ)))
    a1 = correr(c.sintetizar(persona.SALUDO_VOZ, fijo=True))
    gastado = c._chars_hoy
    for _ in range(5):
        assert correr(c.sintetizar(persona.SALUDO_VOZ, fijo=True)) == a1
    assert len(e.sintesis) == 1 and c._chars_hoy == gastado
    # Con el cupo agotado lo cacheado sigue saliendo; lo nuevo no.
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("otra cosa", fijo=True))


def test_sin_fijo_no_cachea():
    e = Eleven()
    c = cliente_falso(e)
    correr(c.sintetizar("hola"))
    correr(c.sintetizar("hola"))
    assert len(e.sintesis) == 2 and c._frases == {}


def test_cache_distingue_el_formato():
    e = Eleven(tts=[MP3, OGG])
    c = cliente_falso(e)
    assert correr(c.sintetizar("hola", "mp3", fijo=True)) == MP3
    assert correr(c.sintetizar("hola", "opus", fijo=True)) == OGG
    assert correr(c.sintetizar("hola", "mp3", fijo=True)) == MP3
    assert len(e.sintesis) == 2


def test_cache_no_guarda_los_errores():
    e = Eleven(tts=[err(500), MP3])
    c = cliente_falso(e)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola", fijo=True))
    assert correr(c.sintetizar("hola", fijo=True)) == MP3


def test_cache_tiene_tamanio_maximo():
    e = Eleven()
    c = cliente_falso(e)

    async def muchas():
        for i in range(voz.CACHE_FRASES + 5):
            await c.sintetizar(f"frase número {i}", fijo=True)
        await c.sintetizar("frase número 0", fijo=True)     # la más vieja ya salió
    correr(muchas())
    assert len(c._frases) == voz.CACHE_FRASES and len(e.sintesis) == voz.CACHE_FRASES + 6


# ─── hablar: nunca levanta ────────────────────────────────────────────────
def test_hablar_camino_feliz_y_sin_cliente():
    assert correr(voz.hablar("hola", cliente_falso(Eleven()))) == (MP3, "audio/mpeg", None)
    assert correr(voz.hablar("hola", cliente_falso(Eleven(tts=[OGG])), "opus")) == (OGG, "audio/ogg", None)
    assert correr(voz.hablar("hola", None)) == (None, None, "sin-voz")


@pytest.mark.parametrize("tts, error", [
    (err(402), "sin-creditos"),
    (err(401, "quota_exceeded"), "sin-creditos"),
    (err(401, "invalid_api_key"), "sin-voz"),
    (err(500), "error: _ErrorHttp"),
    (httpx.ConnectError("x"), "error: ErrorVoz"),
    (b"", "error: ErrorVoz"),
    (RuntimeError("algo inesperado"), "error: RuntimeError"),
])
def test_hablar_nunca_levanta(tts, error):
    assert correr(voz.hablar("hola", cliente_falso(Eleven(tts=[tts])))) == (None, None, error)


def test_hablar_no_levanta_con_texto_vacio_formato_malo_ni_tope():
    c = cliente_falso(Eleven(), max_chars_dia=3)
    assert correr(voz.hablar("🌱", c)) == (None, None, "error: ErrorVoz")
    assert correr(voz.hablar("hola", c, "wav")) == (None, None, "error: KeyError")
    assert correr(voz.hablar("hola", c)) == (None, None, "sin-creditos")


# ─── el camino voz=True de responder y del prompt ─────────────────────────
def test_turno_usuario_lleva_la_nota_de_voz_solo_con_voz():
    sin = prompt.turno_usuario("estado", "días", [], "¿tenés sed?", simple="simple")
    con = prompt.turno_usuario("estado", "días", [], "¿tenés sed?", simple="simple", voz=True)
    assert persona.NOTA_VOZ not in sin and sin.endswith("PREGUNTA\n¿tenés sed?")
    assert con == f"{sin}\n\n{persona.NOTA_VOZ}"          # pegada a la pregunta, al final (D221)


def test_responder_con_voz_pide_respuesta_hablada(db):
    cargar(db, [1500.0] * 3)
    g = GeminiFalso()
    correr(responder("¿tenés sed?", 1, db, **deps(g)))
    correr(responder("¿tenés sed?", 2, db, voz=True, **deps(g)))
    escrito, hablado = (ll[1][-1]["text"] for ll in g.llamadas_generar)
    assert persona.NOTA_VOZ not in escrito
    assert hablado.endswith(f"PREGUNTA\n¿tenés sed?\n\n{persona.NOTA_VOZ}")
    assert all(ll[0] == persona.SYSTEM for ll in g.llamadas_generar)   # la persona no cambia


def test_la_nota_de_voz_no_queda_en_la_memoria_ni_en_el_log(db):
    g, d = GeminiFalso(), deps()
    correr(responder("¿tenés sed?", 3, db, voz=True, **{**d, "gemini": g}))
    assert d["memoria"].historial(3)[0]["text"] == "¿tenés sed?"
    assert db.query(Conversacion).one().pregunta == "¿tenés sed?"


# ─── conversar: oír → responder → hablar ──────────────────────────────────
def test_conversar_con_audio_camino_feliz(db):
    cargar(db, [1500.0] * 3)
    e, g = Eleven(), GeminiFalso(intencion="riego", respuesta="Tengo sed [1].")
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), **deps(g)))
    assert c.pregunta == PREGUNTA and c.texto == "Tengo sed." == c.respuesta.texto
    assert (c.audio, c.audio_mime, c.error_voz) == (MP3, "audio/mpeg", None)
    assert c.respuesta.en_dominio is True and c.respuesta.intencion == "riego"
    assert c.ms_oir >= 0 and c.ms_hablar >= 0
    assert [p.url.path for p in e.pedidos] == ["/v1/speech-to-text", "/v1/text-to-speech/voz-x"]
    assert json.loads(e.sintesis[0].content)["text"] == "Tengo sed."
    # Lo transcripto es lo que entra a `responder`, con la nota de voz.
    turno = g.llamadas_generar[0][1][-1]["text"]
    assert turno.endswith(f"PREGUNTA\n{PREGUNTA}\n\n{persona.NOTA_VOZ}")
    fila = db.query(Conversacion).one()
    assert (fila.chat_id, fila.pregunta, fila.respuesta, fila.error) == (42, PREGUNTA, "Tengo sed.", None)


def test_conversar_formato_opus(db):
    e = Eleven(tts=[OGG])
    c = correr(voz.conversar(AUDIO, "audio/ogg", 1, db, voz=cliente_falso(e), formato="opus", **deps()))
    assert (c.audio, c.audio_mime) == (OGG, "audio/ogg")
    assert e.sintesis[0].url.params["output_format"] == "opus_48000_32"


def test_conversar_no_se_entendio_no_responde_ni_loguea(db):
    e, g = Eleven(stt=[{"text": "(ruido)"}]), GeminiFalso()
    cl = cliente_falso(e)
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cl, **deps(g)))
    assert c.respuesta is None and c.pregunta == "" and c.texto == persona.NO_ENTENDI
    assert c.error_voz == "no-se-entendio" and (c.audio, c.audio_mime) == (MP3, "audio/mpeg")
    assert g.prompts_clasificar == [] and g.llamadas_generar == []
    assert db.query(Conversacion).count() == 0
    # El «no te escuché» es una frase fija: la segunda vez sale del caché.
    correr(voz.conversar(b"", "audio/webm", 42, db, voz=cl, **deps(g)))
    assert len(e.sintesis) == 1 and len(e.transcripciones) == 1      # el audio vacío ni viaja


def test_conversar_no_se_entendio_sin_audio_de_vuelta(db):
    e = Eleven(stt=[err(400, "invalid_audio")])
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), con_audio=False, **deps()))
    assert (c.texto, c.audio, c.error_voz) == (persona.NO_ENTENDI, None, "no-se-entendio")
    assert e.sintesis == []


def test_conversar_no_se_entendio_y_la_voz_tampoco_anda(db):
    e = Eleven(stt=[{"text": ""}], tts=[err(500)])
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), **deps()))
    assert (c.texto, c.audio, c.error_voz) == (persona.NO_ENTENDI, None, "no-se-entendio")


def test_conversar_sin_cliente_de_voz(db):
    g = GeminiFalso()
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=None, **deps(g)))
    assert (c.pregunta, c.respuesta, c.texto, c.audio, c.error_voz) == \
        ("", None, persona.SIN_OIDOS, None, "sin-voz")
    assert g.prompts_clasificar == [] and db.query(Conversacion).count() == 0


@pytest.mark.parametrize("stt, error", [
    (err(401, "invalid_api_key"), "sin-voz"),
    (err(402), "sin-creditos"),
    (err(401, "quota_exceeded"), "sin-creditos"),
    (httpx.ConnectError("x"), "error: ErrorVoz"),
    (err(500), "error: _ErrorHttp"),
    ((200, b"esto no es json"), "error: ErrorVoz"),
])
def test_conversar_no_puede_oir(db, stt, error):
    e, g = Eleven(stt=[stt]), GeminiFalso()
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), **deps(g)))
    assert (c.respuesta, c.texto, c.audio, c.error_voz) == (None, persona.SIN_OIDOS, None, error)
    assert g.prompts_clasificar == [] and e.sintesis == [] and db.query(Conversacion).count() == 0


def test_conversar_audio_gigante_no_viaja(db):
    e = Eleven()
    c = correr(voz.conversar(b"x" * (voz.MAX_BYTES_AUDIO + 1), "audio/webm", 42, db,
                             voz=cliente_falso(e), **deps()))
    assert c.texto == persona.SIN_OIDOS and c.error_voz == "error: ErrorVoz" and e.pedidos == []


def test_conversar_con_texto_y_sin_audio(db):
    e, g = Eleven(), GeminiFalso()
    c = correr(voz.conversar(None, "", 42, db, texto="¿cómo estás?", voz=cliente_falso(e),
                             con_audio=False, **deps(g)))
    assert c.pregunta == "¿cómo estás?" and c.texto == "Soy Ruperto."
    assert (c.audio, c.audio_mime, c.error_voz) == (None, None, None)
    assert e.pedidos == [] and c.ms_oir == 0
    assert persona.NOTA_VOZ in g.llamadas_generar[0][1][-1]["text"]
    assert db.query(Conversacion).one().pregunta == "¿cómo estás?"


def test_conversar_con_texto_y_audio_no_transcribe(db):
    e = Eleven()
    c = correr(voz.conversar(None, "", 42, db, texto="¿cómo estás?", voz=cliente_falso(e), **deps()))
    assert c.audio == MP3 and e.transcripciones == [] and len(e.sintesis) == 1


def test_conversar_con_texto_sin_cliente_contesta_igual(db):
    c = correr(voz.conversar(None, "", 42, db, texto="¿cómo estás?", voz=None, **deps()))
    assert c.texto == "Soy Ruperto." and c.audio is None and c.error_voz == "sin-voz"
    assert db.query(Conversacion).count() == 1


@pytest.mark.parametrize("tts, error", [
    (err(500), "error: _ErrorHttp"), (err(402), "sin-creditos"), (err(401, "x"), "sin-voz"),
    (httpx.ReadTimeout("x"), "error: ErrorVoz"),
])
def test_conversar_si_falla_la_sintesis_el_texto_sale_igual(db, tts, error):
    e = Eleven(tts=[tts])
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), **deps()))
    assert c.pregunta == PREGUNTA and c.texto == "Soy Ruperto." and c.respuesta.error is None
    assert (c.audio, c.audio_mime, c.error_voz) == (None, None, error)
    assert db.query(Conversacion).one().respuesta == "Soy Ruperto."


def test_conversar_tope_diario_responde_solo_en_texto(db):
    e = Eleven()
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e, max_chars_dia=3), **deps()))
    assert c.texto == "Soy Ruperto." and c.audio is None and c.error_voz == "sin-creditos"
    assert e.sintesis == []


def test_conversar_fuera_de_dominio_usa_el_cache(db, monkeypatch):
    monkeypatch.setattr(persona, "rechazo", lambda rng=None: persona.RECHAZOS[0])
    e, g = Eleven(), GeminiFalso(en_dominio=False, intencion="otro")
    cl = cliente_falso(e)
    c1 = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cl, **deps(g)))
    gastado = cl._chars_hoy
    c2 = correr(voz.conversar(None, "", 43, db, texto="una receta de ñoquis", voz=cl, **deps(g)))
    assert c1.texto == c2.texto == persona.RECHAZOS[0] and c1.respuesta.en_dominio is False
    assert c1.audio == c2.audio == MP3 and g.llamadas_generar == []
    assert len(e.sintesis) == 1 and cl._chars_hoy == gastado
    assert db.query(Conversacion).count() == 2


def test_conversar_respuesta_generada_no_se_cachea(db):
    e = Eleven()
    cl = cliente_falso(e)
    for chat in (1, 2):
        correr(voz.conversar(None, "", chat, db, texto="¿cómo estás?", voz=cl, **deps()))
    assert len(e.sintesis) == 2 and cl._frases == {}


@pytest.mark.parametrize("gemini_kw, texto", [
    ({"error_generar": "sin-cupo"}, persona.SIN_ALIENTO),
    ({"error_generar": "error"}, persona.ERROR),
])
def test_conversar_errores_de_gemini_se_dicen_en_voz_y_se_cachean(db, gemini_kw, texto):
    from app.bot.gemini import ErrorGemini, SinCupo
    g = GeminiFalso(error_generar=SinCupo("q") if gemini_kw["error_generar"] == "sin-cupo"
                    else ErrorGemini("503"))
    e = Eleven()
    cl = cliente_falso(e)
    for _ in range(2):
        c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cl, **deps(g)))
        assert c.texto == texto and c.audio == MP3 and c.respuesta.error
    assert len(e.sintesis) == 1


def test_conversar_el_pie_de_fuentes_se_muestra_pero_no_se_dice(db):
    frag = recuperar.Fragmento("ciencia/ufifas#3", "ciencia", "UF/IFAS", "https://edis.ifas.ufl.edu",
                               None, "Spathiphyllum wilts when dry", 0.83)
    e = Eleven()
    d = deps(GeminiFalso(intencion="cuidados", respuesta="Me desmayo si me falta agua [1]."))
    d["buscar"] = buscador(frag)
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cliente_falso(e), **d))
    assert "📚 Fuente" in c.texto
    assert json.loads(e.sintesis[0].content)["text"] == "Me desmayo si me falta agua."


# ─── viñetas con guion y números negativos ────────────────────────────────
@pytest.mark.parametrize("crudo, hablado", [
    ("- Tierra: húmeda", "Tierra: húmeda."),               # guion + espacio: viñeta
    ("-5 mV", "-5 milivoltios."),                           # guion pegado: es un número
    ("-2 °C afuera", "-2 grados afuera."),
    ("Suelo: -5 mV", "Suelo: -5 milivoltios."),
    ("Datos:\n- Aire: 22 °C\n- Mínima: -1 °C", "Datos: Aire: 22 grados. Mínima: -1 grados."),
    ("• -3 °C", "-3 grados."),
])
def test_texto_hablado_guion_vineta_o_signo_menos(crudo, hablado):
    assert voz.texto_hablado(crudo) == hablado


@pytest.mark.parametrize("crudo", ["-", "- ", "---", "- -"])
def test_texto_hablado_solo_guiones_es_vacio(crudo):
    assert voz.texto_hablado(crudo) == ""


# ─── respuestas 200 que no son JSON ───────────────────────────────────────
@pytest.mark.parametrize("cuerpo", [b"esto no es json", b"<html>502</html>", b""])
def test_transcribir_200_sin_json_es_error_de_voz(cuerpo):
    c = cliente_falso(Eleven(stt=[(200, cuerpo)]))
    with pytest.raises(voz.ErrorVoz) as ei:
        correr(c.transcribir(AUDIO))
    assert type(ei.value) is voz.ErrorVoz                  # ni JSONDecodeError ni «no se entendió»


def test_transcribir_json_que_no_es_objeto_no_trae_palabras():
    with pytest.raises(voz.NoSeEntendio):
        correr(cliente_falso(Eleven(stt=[(200, ["hola"])])).transcribir(AUDIO))


@pytest.mark.parametrize("lista", [(200, b"esto no es json"), (200, b""), (200, ["voz-1"])])
def test_listado_de_voces_200_sin_json_cae_al_respaldo(lista):
    e = Eleven(lista=[lista])
    c = cliente_falso(e, voz_id=None)
    assert correr(c.sintetizar("hola")) == MP3
    assert c.voz_id == voz.VOZ_RESPALDO and c._chars_hoy == len("hola.")


def test_hablar_con_listado_roto_habla_igual():
    c = cliente_falso(Eleven(lista=[(200, b"no json")]), voz_id=None)
    assert correr(voz.hablar("hola", c)) == (MP3, "audio/mpeg", None)


# ─── tope diario de audios transcriptos ───────────────────────────────────
def test_tope_de_audios_por_defecto_y_por_entorno(monkeypatch):
    assert cliente_falso(Eleven()).max_audios_dia == voz.MAX_AUDIOS_DIA_DEFAULT == 400
    monkeypatch.setenv("VOZ_MAX_AUDIOS_DIA", "7")
    assert cliente_falso(Eleven()).max_audios_dia == 7


def test_tope_de_audios_y_reinicio_al_dia_siguiente(monkeypatch):
    e = Eleven()
    c = cliente_falso(e)
    c.max_audios_dia = 2
    correr(c.sintetizar("hola"))
    assert correr(c.transcribir(AUDIO)) == PREGUNTA and correr(c.transcribir(AUDIO)) == PREGUNTA
    with pytest.raises(voz.SinCreditos):
        correr(c.transcribir(AUDIO))
    assert len(e.transcripciones) == 2 and c._audios_hoy == 2      # el rechazado ni viaja ni cuenta
    pasar_al_dia_siguiente(monkeypatch)
    assert correr(c.transcribir(AUDIO)) == PREGUNTA
    # El día nuevo reinicia los dos contadores juntos.
    assert (c._audios_hoy, c._chars_hoy) == (1, 0) and len(e.transcripciones) == 3


def test_el_dia_nuevo_lo_puede_abrir_cualquiera_de_los_dos_contadores(monkeypatch):
    c = cliente_falso(Eleven())
    correr(c.transcribir(AUDIO))
    correr(c.sintetizar("hola"))
    pasar_al_dia_siguiente(monkeypatch)
    correr(c.sintetizar("chau"))
    assert (c._audios_hoy, c._chars_hoy) == (0, len("chau."))


def test_tope_de_audios_no_cuenta_lo_que_no_viaja():
    c = cliente_falso(Eleven())
    c.max_audios_dia = 1
    for audio in (b"", b"x" * 10, b"x" * (voz.MAX_BYTES_AUDIO + 1)):
        with pytest.raises(voz.ErrorVoz):
            correr(c.transcribir(audio))
    assert c._audios_hoy == 0
    assert correr(c.transcribir(AUDIO)) == PREGUNTA and c._audios_hoy == 1


def test_tope_de_audios_cuenta_los_que_no_se_entendieron():
    """Scribe cobra el audio aunque no traiga palabras: cuenta igual."""
    c = cliente_falso(Eleven(stt=[{"text": "(ruido)"}]))
    with pytest.raises(voz.NoSeEntendio):
        correr(c.transcribir(AUDIO))
    assert c._audios_hoy == 1


def test_tope_de_audios_no_afecta_a_la_sintesis():
    e = Eleven()
    c = cliente_falso(e)
    c.max_audios_dia = 0
    with pytest.raises(voz.SinCreditos):
        correr(c.transcribir(AUDIO))
    assert correr(c.sintetizar("hola")) == MP3 and e.transcripciones == []


def test_conversar_con_el_tope_de_audios_agotado(db):
    e, g = Eleven(), GeminiFalso()
    cl = cliente_falso(e)
    cl.max_audios_dia = 0
    c = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=cl, **deps(g)))
    assert (c.respuesta, c.texto, c.audio, c.error_voz) == (None, persona.SIN_OIDOS, None, "sin-creditos")
    assert e.pedidos == [] and g.prompts_clasificar == [] and db.query(Conversacion).count() == 0
    # Escribiendo se puede seguir charlando, con audio de vuelta.
    c = correr(voz.conversar(None, "", 42, db, texto="¿cómo estás?", voz=cl, **deps(g)))
    assert c.texto == "Soy Ruperto." and c.audio == MP3


# ─── los caracteres de una síntesis fallida se devuelven ──────────────────
@pytest.mark.parametrize("tts", [
    [err(500)], [err(402)], [err(401, "invalid_api_key")], [httpx.ConnectError("x")],
    [RuntimeError("inesperado")],
    [err(400, "invalid_text"), err(400, "invalid_text")],     # falla también el reintento sin idioma
])
def test_sintesis_fallida_devuelve_los_caracteres(tts):
    c = cliente_falso(Eleven(tts=tts))
    with pytest.raises(Exception):  # noqa: B017 - cualquier falla devuelve el cupo
        correr(c.sintetizar("hola"))
    assert c._chars_hoy == 0


def test_sintesis_fallida_devuelve_solo_lo_suyo():
    e = Eleven(tts=[MP3, err(500), MP3])
    c = cliente_falso(e)
    correr(c.sintetizar("hola"))
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("una frase bastante más larga"))
    assert c._chars_hoy == len("hola.")
    correr(c.sintetizar("chau"))
    assert c._chars_hoy == len("hola.") + len("chau.")       # lo dicho no se devuelve


def test_404_repetido_de_la_voz_devuelve_los_caracteres():
    e = Eleven(lista=[{"voices": [{"voice_id": "vieja"}]}], tts=[err(404, "voice_not_found")])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert c._chars_hoy == 0


def test_las_fallas_no_se_comen_el_tope_diario():
    """Con el cupo justo para una frase, cinco fallas antes no lo agotan."""
    e = Eleven(tts=[err(500)] * 5 + [MP3])
    c = cliente_falso(e, max_chars_dia=len("hola."))
    for _ in range(5):
        with pytest.raises(voz.ErrorVoz):
            correr(c.sintetizar("hola"))
    assert correr(c.sintetizar("hola")) == MP3 and c._chars_hoy == len("hola.")
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    assert c._chars_hoy == len("hola.") and len(e.sintesis) == 6   # el tope no se «devuelve» de más


def test_reintento_exitoso_cuenta_una_sola_vez():
    c = cliente_falso(Eleven(tts=[err(400, "unsupported_language"), MP3]))
    correr(c.sintetizar("hola"))
    assert c._chars_hoy == len("hola.")


def test_hablar_fallido_tampoco_gasta():
    c = cliente_falso(Eleven(tts=[err(500)]))
    assert correr(voz.hablar("hola", c))[0] is None and c._chars_hoy == 0


# ─── guion pegado al texto: también es viñeta ─────────────────────────────
@pytest.mark.parametrize("crudo, hablado", [
    ("-Tierra: húmeda", "Tierra: húmeda."),
    ("Datos:\n-Aire: 22 °C\n-Tierra: húmeda", "Datos: Aire: 22 grados. Tierra: húmeda."),
    ("-¡Hola!", "¡Hola!"),
    ("- 5 mV", "5 milivoltios."),                           # con espacio es viñeta, no signo
    ("-5 mV", "-5 milivoltios."),                           # sólo seguido de un dígito es un número
    ("-0,5 °C", "-0,5 grados."),
])
def test_texto_hablado_guion_pegado(crudo, hablado):
    assert voz.texto_hablado(crudo) == hablado


# ─── fuera de servicio por un rato (sin clave o sin créditos) ─────────────
SIN_CLAVE, SIN_SALDO, CUOTA = err(401, "invalid_api_key"), err(402), err(401, "quota_exceeded")


def reabrir(c, faltan=-1):
    """Mueve el fin de la pausa: por defecto ya venció; `faltan` segundos si no."""
    import time
    c._caida_hasta = time.monotonic() + faltan


def test_cliente_nuevo_esta_disponible():
    c = cliente_falso(Eleven())
    assert c.disponible is True and voz.PAUSA_SIN_VOZ_S == 600


@pytest.mark.parametrize("tts", [SIN_CLAVE, err(403, "forbidden"), SIN_SALDO, CUOTA,
                                 err(402, "insufficient_credits", clave="code")])
def test_sintetizar_sin_clave_o_sin_creditos_abre_la_pausa(tts):
    import time
    c = cliente_falso(Eleven(tts=[tts]))
    with pytest.raises((voz.SinVoz, voz.SinCreditos)):
        correr(c.sintetizar("hola"))
    assert c.disponible is False
    assert voz.PAUSA_SIN_VOZ_S - 5 < c._caida_hasta - time.monotonic() <= voz.PAUSA_SIN_VOZ_S


@pytest.mark.parametrize("stt", [SIN_CLAVE, err(403, "forbidden"), SIN_SALDO, CUOTA, err(400, "quota_exceeded")])
def test_transcribir_sin_clave_o_sin_creditos_abre_la_pausa(stt):
    c = cliente_falso(Eleven(stt=[stt]))
    with pytest.raises((voz.SinVoz, voz.SinCreditos)):
        correr(c.transcribir(AUDIO))
    assert c.disponible is False


def test_el_tope_diario_de_caracteres_abre_la_pausa():
    e = Eleven()
    c = cliente_falso(e, max_chars_dia=5)
    correr(c.sintetizar("hola"))
    assert c.disponible is True
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("chau"))
    assert c.disponible is False and len(e.sintesis) == 1


def test_el_tope_diario_de_audios_abre_la_pausa():
    c = cliente_falso(Eleven())
    c.max_audios_dia = 1
    correr(c.transcribir(AUDIO))
    assert c.disponible is True
    with pytest.raises(voz.SinCreditos):
        correr(c.transcribir(AUDIO))
    assert c.disponible is False


def test_elegir_voz_sin_creditos_abre_la_pausa():
    c = cliente_falso(Eleven(lista=[SIN_SALDO]), voz_id=None)
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    assert c.disponible is False and c._chars_hoy == 0


def test_reelegir_voz_sin_creditos_abre_la_pausa():
    e = Eleven(lista=[{"voices": [{"voice_id": "vieja"}]}, SIN_SALDO], tts=[err(404, "voice_not_found")])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    assert c.disponible is False and c._chars_hoy == 0


@pytest.mark.parametrize("tts", [
    [err(500)], [httpx.ConnectError("x")], [httpx.ReadTimeout("x")], [b""],
    [err(404, "voice_not_found")], [err(400, "invalid_text"), err(400, "invalid_text")],
    [RuntimeError("inesperado")], [(429, {"detail": {"status": "too_many_concurrent_requests"}})],
])
def test_otros_errores_de_sintesis_no_abren_la_pausa(tts):
    c = cliente_falso(Eleven(tts=tts))
    with pytest.raises(Exception):  # noqa: B017 - lo que importa es que sigue disponible
        correr(c.sintetizar("hola"))
    assert c.disponible is True and c._caida_hasta == 0.0


def test_404_repetido_de_una_voz_elegida_no_abre_la_pausa():
    e = Eleven(lista=[{"voices": [{"voice_id": "vieja"}]}], tts=[err(404, "voice_not_found")])
    c = cliente_falso(e, voz_id=None)
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert c.disponible is True


def test_nada_para_decir_o_formato_malo_no_abren_la_pausa():
    c = cliente_falso(Eleven())
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("🌱"))
    with pytest.raises(KeyError):
        correr(c.sintetizar("hola", "wav"))
    assert c.disponible is True


@pytest.mark.parametrize("stt", [
    err(500), httpx.ConnectError("x"), err(400, "invalid_audio"), err(422, "unprocessable"),
    {"text": "(ruido)"}, (200, b"no es json"), err(400, "invalid_model_id"),
])
def test_otros_errores_de_transcripcion_no_abren_la_pausa(stt):
    c = cliente_falso(Eleven(stt=[stt]))
    with pytest.raises(voz.ErrorVoz):
        correr(c.transcribir(AUDIO))
    assert c.disponible is True


def test_audio_corto_o_gigante_no_abre_la_pausa():
    c = cliente_falso(Eleven())
    for audio in (b"", b"x" * (voz.MAX_BYTES_AUDIO + 1)):
        with pytest.raises(voz.ErrorVoz):
            correr(c.transcribir(audio))
    assert c.disponible is True


def test_listado_de_voces_rechazado_no_abre_la_pausa_si_despues_habla():
    """Una clave sin permiso para listar voces cae a la de respaldo: no es una caída."""
    c = cliente_falso(Eleven(lista=[err(401, "missing_permissions")]), voz_id=None)
    assert correr(c.sintetizar("hola")) == MP3 and c.disponible is True


def test_la_pausa_se_cierra_sola():
    c = cliente_falso(Eleven(tts=[SIN_SALDO, MP3]))
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    c._caida_hasta -= voz.PAUSA_SIN_VOZ_S - 5              # pasaron 9 min 55 s
    assert c.disponible is False
    c._caida_hasta -= 6                                     # pasaron los 10 minutos
    assert c.disponible is True
    assert correr(c.sintetizar("hola")) == MP3 and c.disponible is True


def test_cada_caida_renueva_la_pausa():
    c = cliente_falso(Eleven(tts=[SIN_SALDO]))
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    reabrir(c)
    assert c.disponible is True
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    assert c.disponible is False


def test_un_error_comun_durante_la_pausa_no_la_acorta():
    c = cliente_falso(Eleven(tts=[SIN_SALDO, err(500)]))
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("hola"))
    hasta = c._caida_hasta
    with pytest.raises(voz.ErrorVoz):
        correr(c.sintetizar("hola"))
    assert c._caida_hasta == hasta and c.disponible is False


def test_el_cache_del_cliente_sigue_sirviendo_durante_la_pausa():
    """`disponible` lo miran el router y el bot; el cliente en sí no se bloquea:
    lo ya sintetizado no cuesta nada."""
    e = Eleven(tts=[MP3, SIN_SALDO])
    c = cliente_falso(e)
    correr(c.sintetizar(persona.SALUDO_VOZ, fijo=True))
    with pytest.raises(voz.SinCreditos):
        correr(c.sintetizar("otra cosa"))
    hasta = c._caida_hasta
    assert correr(c.sintetizar(persona.SALUDO_VOZ, fijo=True)) == MP3
    assert len(e.sintesis) == 2 and c._caida_hasta == hasta and c.disponible is False


def test_hablar_y_conversar_tambien_abren_la_pausa(db):
    c = cliente_falso(Eleven(tts=[SIN_SALDO]))
    assert correr(voz.hablar("hola", c)) == (None, None, "sin-creditos") and c.disponible is False
    c = cliente_falso(Eleven(stt=[SIN_CLAVE]))
    ch = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=c, **deps()))
    assert ch.error_voz == "sin-voz" and c.disponible is False
    c = cliente_falso(Eleven(tts=[err(500)]))
    ch = correr(voz.conversar(AUDIO, "audio/webm", 42, db, voz=c, **deps()))
    assert ch.error_voz == "error: _ErrorHttp" and c.disponible is True


# ---- clave de Gemini aparte para la voz (D224) ----

def test_gemini_para_voz_usa_la_clave_aparte(monkeypatch):
    from app.bot import gemini as modulo_gemini, recuperar, responder as r

    creados = []

    class Falso:
        def __init__(self, api_key=None, **_):
            creados.append(api_key)

        def embeber_consulta(self, _):
            return []

    monkeypatch.setattr(modulo_gemini, "ClienteGemini", Falso)
    monkeypatch.setattr(r, "_gemini", "el-de-siempre")
    monkeypatch.setattr(r, "_gemini_voz", None)
    monkeypatch.setattr(recuperar, "_embedder", lambda _: [])

    monkeypatch.delenv("GEMINI_API_KEY_VOZ", raising=False)
    assert r._gemini_para_voz() == "el-de-siempre" and creados == []

    monkeypatch.setenv("GEMINI_API_KEY_VOZ", "clave-voz")
    c = r._gemini_para_voz()
    assert isinstance(c, Falso) and creados == ["clave-voz"]
    assert r._gemini_para_voz() is c and creados == ["clave-voz"]     # uno solo por proceso
    assert r._gemini_default() == "el-de-siempre"                     # el texto no cambia
