"""El handler de notas de voz de Telegram (D222) con Update y mensajes falsos:
sin Telegram, sin red y con la base SQLite del fixture."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from conftest import GeminiFalso
from telegram.constants import ChatAction
from test_bot_voz import MP3, OGG, PREGUNTA, Eleven, cliente_falso, err

from app.bot import persona, prompt, recuperar, telegram_bot, voz
from app.bot import responder as responder_mod
from app.models import Conversacion

AUDIO = b"OggS" + b"v" * 2000         # la nota de voz que manda el usuario
CHAT = 4242


def correr(coro):
    return asyncio.run(coro)


class Adjunto:
    def __init__(self, datos=AUDIO, duration=5, file_size=None, mime_type="audio/ogg"):
        self.datos, self.duration = datos, duration
        self.file_size = len(datos) if file_size is None else file_size
        if mime_type is not None:           # un videomensaje no trae mime_type
            self.mime_type = mime_type
        self.descargas = 0

    async def get_file(self):
        adjunto = self

        class Archivo:
            async def download_as_bytearray(self):
                adjunto.descargas += 1
                return bytearray(adjunto.datos)
        return Archivo()


class Mensaje:
    def __init__(self, voice=None, audio=None, video_note=None, falla=()):
        self.voice, self.audio, self.video_note = voice, audio, video_note
        self.falla = set(falla)
        self.enviados: list[tuple] = []

    async def reply_text(self, texto):
        self.enviados.append(("texto", texto))

    async def reply_voice(self, archivo, **kw):
        if "voz" in self.falla:
            raise RuntimeError("Telegram rechazó la nota de voz")
        self.enviados.append(("voz", archivo.read()))

    async def reply_audio(self, archivo, **kw):
        if "audio" in self.falla:
            raise RuntimeError("Telegram rechazó el audio")
        self.enviados.append(("audio", archivo.read(), kw))


def update_con(mensaje, chat_id=CHAT):
    acciones = []

    async def send_action(accion):
        acciones.append(accion)
    return SimpleNamespace(effective_message=mensaje, acciones=acciones,
                           effective_chat=SimpleNamespace(id=chat_id, send_action=send_action))


@pytest.fixture
def tg(db, monkeypatch):
    for v in ("ELEVENLABS_VOZ_ID", "ELEVENLABS_MODELO_TTS", "ELEVENLABS_MODELO_STT", "ELEVENLABS_URL",
              "VOZ_MAX_CHARS_DIA", "VOZ_MAX_AUDIOS_DIA"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    eleven = Eleven(tts=[OGG])
    cliente = cliente_falso(eleven)
    monkeypatch.setattr(voz, "cliente", lambda: cliente)
    monkeypatch.setattr(voz, "configurada", lambda env=None: True)
    gemini = GeminiFalso()
    monkeypatch.setattr(responder_mod, "_gemini_default", lambda: gemini)
    monkeypatch.setattr(responder_mod, "_memoria", prompt.Memoria())
    monkeypatch.setattr(recuperar, "buscar", lambda *a, **k: [])
    monkeypatch.setattr(recuperar, "recientes", lambda *a, **k: [])

    @contextmanager
    def sesion():
        yield db
    monkeypatch.setattr(telegram_bot, "SessionLocal", sesion)
    voz.reiniciar()
    yield SimpleNamespace(db=db, eleven=eleven, voz=cliente, gemini=gemini, mp=monkeypatch)
    voz.reiniciar()


def nota(tg, mensaje=None):
    m = mensaje or Mensaje(voice=Adjunto())
    u = update_con(m)
    correr(telegram_bot._voz(u, None))
    return m, u


# ─── cuando no se llega a oír ─────────────────────────────────────────────
def test_sin_cliente_de_voz_avisa_que_esta_sordo(tg):
    tg.mp.setattr(voz, "configurada", lambda env=None: False)
    adj = Adjunto()
    m, u = nota(tg, Mensaje(voice=adj))
    assert m.enviados == [("texto", persona.SIN_OIDOS)]
    assert adj.descargas == 0 and u.acciones == [] and tg.eleven.pedidos == []
    assert tg.db.query(Conversacion).count() == 0


def test_si_el_cliente_no_se_puede_crear_avisa_igual(tg):
    def roto():
        raise voz.SinVoz("falta ELEVENLABS_API_KEY")
    tg.mp.setattr(voz, "cliente", roto)
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.SIN_OIDOS)]


@pytest.mark.parametrize("adjunto", [
    Adjunto(duration=telegram_bot.MAX_SEGUNDOS_VOZ + 1),
    Adjunto(file_size=voz.MAX_BYTES_AUDIO + 1),
])
def test_audio_demasiado_largo(tg, adjunto):
    m, u = nota(tg, Mensaje(voice=adjunto))
    assert m.enviados == [("texto", persona.AUDIO_LARGO)]
    assert adjunto.descargas == 0 and tg.eleven.pedidos == [] and u.acciones == []


def test_audio_en_el_borde_de_la_duracion_entra(tg):
    adj = Adjunto(duration=telegram_bot.MAX_SEGUNDOS_VOZ)
    m, _ = nota(tg, Mensaje(voice=adj))
    assert adj.descargas == 1 and m.enviados[-1] == ("voz", OGG)


def test_adjunto_sin_duracion_ni_tamanio(tg):
    m, _ = nota(tg, Mensaje(voice=Adjunto(duration=None, file_size=0)))
    assert [e[0] for e in m.enviados] == ["texto", "voz"]


# ─── camino feliz ─────────────────────────────────────────────────────────
def test_nota_de_voz_vuelve_en_texto_y_en_nota_de_voz(tg):
    adj = Adjunto()
    m, u = nota(tg, Mensaje(voice=adj))
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto."), ("voz", OGG)]
    assert u.acciones == [ChatAction.RECORD_VOICE] and adj.descargas == 1
    stt, tts = tg.eleven.pedidos
    assert AUDIO in stt.content and b'filename="audio.ogg"' in stt.content
    assert tts.url.params["output_format"] == "opus_48000_32"       # Ogg/Opus: nota de voz
    assert tg.voz.opus_es_ogg is True
    # Mismo `responder` que el texto: modo voz, logueado con el chat de Telegram.
    assert persona.NOTA_VOZ in tg.gemini.llamadas_generar[0][1][-1]["text"]
    fila = tg.db.query(Conversacion).one()
    assert (fila.chat_id, fila.pregunta, fila.respuesta) == (CHAT, PREGUNTA, "Soy Ruperto.")


def test_archivo_de_audio_usa_su_mime(tg):
    nota(tg, Mensaje(audio=Adjunto(mime_type="audio/mpeg")))
    stt = tg.eleven.transcripciones[0]
    assert b'filename="audio.mp3"' in stt.content and b"Content-Type: audio/mpeg\r\n" in stt.content


def test_videomensaje_va_como_video_mp4(tg):
    m, _ = nota(tg, Mensaje(video_note=Adjunto(mime_type=None)))
    stt = tg.eleven.transcripciones[0]
    assert b'filename="audio.mp4"' in stt.content and b"Content-Type: video/mp4\r\n" in stt.content
    assert [e[0] for e in m.enviados] == ["texto", "voz"]


def test_respuesta_larga_se_corta_al_limite_de_telegram(tg):
    tg.gemini.respuesta = "palabra " * 1000
    m, _ = nota(tg)
    assert len(m.enviados[0][1]) == telegram_bot.MAX_MENSAJE


# ─── el opus no viene en Ogg ──────────────────────────────────────────────
def test_opus_sin_ogg_se_pide_de_nuevo_en_mp3_y_va_como_audio(tg):
    tg.eleven.tts = [b"\x00opus-pelado", MP3]
    m, _ = nota(tg)
    assert m.enviados[0] == ("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto.")
    tipo, datos, kw = m.enviados[1]
    assert (tipo, datos) == ("audio", MP3) and kw["filename"] == "ruperto.mp3"
    assert len(m.enviados) == 2
    assert [p.url.params["output_format"] for p in tg.eleven.sintesis] == ["opus_48000_32", "mp3_44100_64"]
    assert tg.voz.opus_es_ogg is False
    assert tg.voz._frases == {}                             # una respuesta generada no se cachea


def test_una_vez_aprendido_pide_mp3_de_entrada_y_una_sola_vez(tg):
    """Sabiendo que el opus no viene en Ogg, la nota siguiente se sintetiza en
    mp3 directamente: una sola síntesis, no dos (créditos y latencia)."""
    tg.eleven.tts = [b"\x00opus-pelado", MP3]
    nota(tg)
    antes, gastado = len(tg.eleven.sintesis), tg.voz._chars_hoy
    m, _ = nota(tg)
    nuevas = tg.eleven.sintesis[antes:]
    assert [p.url.params["output_format"] for p in nuevas] == ["mp3_44100_64"]
    assert tg.voz._chars_hoy == gastado + len("Soy Ruperto.")
    assert [e[0] for e in m.enviados] == ["texto", "audio"] and m.enviados[1][1] == MP3


def test_opus_sin_ogg_y_el_mp3_tambien_falla_queda_el_texto(tg):
    tg.eleven.tts = [b"\x00opus-pelado", err(500)]
    m, _ = nota(tg)
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto.")]


# ─── cuando algo falla ────────────────────────────────────────────────────
@pytest.mark.parametrize("falla, tts", [("voz", [OGG]), ("audio", [b"\x00opus-pelado", MP3])])
def test_si_falla_el_envio_del_audio_no_levanta(tg, falla, tts):
    tg.eleven.tts = tts
    m, _ = nota(tg, Mensaje(voice=Adjunto(), falla={falla}))
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto.")]     # el texto ya había salido
    assert tg.db.query(Conversacion).count() == 1


@pytest.mark.parametrize("tts", [err(500), err(402), err(401, "invalid_api_key")])
def test_si_falla_la_sintesis_va_solo_el_texto(tg, tts):
    tg.eleven.tts = [tts]
    m, _ = nota(tg)
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto.")]


def test_no_se_entendio_va_sin_la_linea_del_microfono(tg):
    tg.eleven.stt = [{"text": "(ruido)"}]
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.NO_ENTENDI), ("voz", OGG)]
    assert tg.gemini.prompts_clasificar == [] and tg.db.query(Conversacion).count() == 0


def test_si_elevenlabs_no_oye_avisa_en_texto(tg):
    tg.eleven.stt = [err(402)]
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.SIN_OIDOS)]
    assert tg.eleven.sintesis == [] and tg.db.query(Conversacion).count() == 0


def test_fuera_de_dominio_tambien_se_dice(tg):
    tg.gemini.en_dominio, tg.gemini.intencion = False, "otro"
    m, _ = nota(tg)
    texto = m.enviados[0][1]
    assert texto.startswith(f"🎙️ «{PREGUNTA}»\n\n") and texto.split("\n\n", 1)[1] in persona.RECHAZOS
    assert m.enviados[1] == ("voz", OGG) and tg.gemini.llamadas_generar == []


def test_mandar_audio_sin_audio_no_manda_nada(tg):
    m = Mensaje(voice=Adjunto())
    c = voz.Charla("hola", None, "Soy Ruperto.", audio=None)
    correr(telegram_bot._mandar_audio(update_con(m), c, tg.voz))
    assert m.enviados == [] and tg.eleven.pedidos == []


# ─── el mp3 de respaldo de las frases fijas se cachea ─────────────────────
PELADO = b"\x00opus-pelado"


def test_respaldo_mp3_de_un_rechazo_se_cachea(tg):
    tg.mp.setattr(persona, "rechazo", lambda rng=None: persona.RECHAZOS[0])
    tg.gemini.en_dominio, tg.gemini.intencion = False, "otro"
    tg.eleven.tts = [PELADO, MP3]
    m, _ = nota(tg)
    assert m.enviados[1][:2] == ("audio", MP3)
    assert len(tg.eleven.sintesis) == 2 and len(tg.voz._frases) == 2     # el opus y el mp3
    gastado = tg.voz._chars_hoy
    # Aunque se vuelva a pedir opus (como si no se hubiera aprendido nada), el
    # rechazo sale entero del caché: ni una síntesis más.
    tg.voz.opus_es_ogg = None
    m, _ = nota(tg)
    assert m.enviados[1][:2] == ("audio", MP3)
    assert len(tg.eleven.sintesis) == 2 and tg.voz._chars_hoy == gastado


def test_respaldo_mp3_del_no_te_escuche_se_cachea(tg):
    tg.eleven.stt = [{"text": "(ruido)"}]
    tg.eleven.tts = [PELADO, MP3]
    for _ in range(2):
        tg.voz.opus_es_ogg = None
        m, _ = nota(tg)
        assert m.enviados == [("texto", persona.NO_ENTENDI), ("audio", MP3, m.enviados[1][2])]
    assert len(tg.eleven.sintesis) == 2 and len(tg.voz._frases) == 2


def test_respaldo_mp3_de_una_respuesta_generada_no_se_cachea(tg):
    tg.eleven.tts = [PELADO, MP3, PELADO, MP3]
    for _ in range(2):
        tg.voz.opus_es_ogg = None
        m, _ = nota(tg)
        assert m.enviados[1][:2] == ("audio", MP3)
    assert len(tg.eleven.sintesis) == 4 and tg.voz._frases == {}


@pytest.mark.parametrize("respuesta, fijo", [("rechazo", True), ("sin-aliento", True), (None, True),
                                             ("generada", False)])
def test_mandar_audio_pasa_fijo_segun_la_respuesta(tg, respuesta, fijo):
    from app.bot.responder import Respuesta
    texto = {"rechazo": persona.RECHAZOS[1], "sin-aliento": persona.SIN_ALIENTO, None: persona.NO_ENTENDI,
             "generada": "Tengo sed."}[respuesta]
    r = None if respuesta is None else Respuesta(texto=texto, en_dominio=True, intencion="estado")
    visto = {}

    async def hablar(t, cliente, formato="mp3", *, fijo=False):
        visto.update(texto=t, formato=formato, fijo=fijo)
        return MP3, "audio/mpeg", None
    tg.mp.setattr(voz, "hablar", hablar)
    m = Mensaje(voice=Adjunto())
    c = voz.Charla("hola", r, texto, audio=PELADO, audio_mime="audio/ogg")
    correr(telegram_bot._mandar_audio(update_con(m), c, tg.voz))
    assert visto == {"texto": texto, "formato": "mp3", "fijo": fijo}
    assert m.enviados[0][:2] == ("audio", MP3)


def test_tope_de_audios_agotado_en_telegram(tg):
    tg.voz.max_audios_dia = 0
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.SIN_OIDOS)] and tg.eleven.pedidos == []


# ─── voz fuera de servicio por un rato ────────────────────────────────────
def test_durante_la_pausa_avisa_que_esta_sordo_y_no_baja_el_audio(tg):
    tg.voz._anotar_caida(voz.SinCreditos("sin créditos"))
    adj = Adjunto()
    m, u = nota(tg, Mensaje(voice=adj))
    assert m.enviados == [("texto", persona.SIN_OIDOS)]
    assert adj.descargas == 0 and u.acciones == [] and tg.eleven.pedidos == []
    assert tg.db.query(Conversacion).count() == 0
    tg.voz._caida_hasta -= voz.PAUSA_SIN_VOZ_S + 1          # pasó la pausa
    m, _ = nota(tg)
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto."), ("voz", OGG)]


@pytest.mark.parametrize("cola, valor", [("tts", err(402)), ("tts", err(401, "invalid_api_key")),
                                         ("stt", err(402)), ("stt", err(401, "quota_exceeded"))])
def test_una_nota_sin_creditos_abre_la_pausa_para_la_siguiente(tg, cola, valor):
    setattr(tg.eleven, cola, [valor])
    nota(tg)
    antes = len(tg.eleven.pedidos)
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.SIN_OIDOS)] and len(tg.eleven.pedidos) == antes


@pytest.mark.parametrize("cola, valor", [("tts", err(500)), ("stt", err(500)), ("stt", {"text": "(ruido)"})])
def test_otros_errores_no_dejan_sordo_al_bot(tg, cola, valor):
    setattr(tg.eleven, cola, [valor])
    nota(tg)
    tg.eleven.stt, tg.eleven.tts = [{"text": PREGUNTA}], [OGG]
    m, _ = nota(tg)
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto."), ("voz", OGG)]


def test_el_tope_de_caracteres_deja_sordo_al_bot_por_la_pausa(tg):
    """Queda fijado lo que hace hoy: aunque oír todavía se podría, sin poder
    hablar el bot tampoco escucha hasta que pase la pausa."""
    tg.voz.max_chars_dia = 3
    m, _ = nota(tg)
    assert m.enviados == [("texto", f"🎙️ «{PREGUNTA}»\n\nSoy Ruperto.")]
    m, _ = nota(tg)
    assert m.enviados == [("texto", persona.SIN_OIDOS)] and len(tg.eleven.transcripciones) == 1
