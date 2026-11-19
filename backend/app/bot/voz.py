"""La voz de Ruperto (docs/ENTREGA3.md D219–D223): oír y hablar con ElevenLabs.

    texto  = await voz.transcribir(audio, "audio/webm")      # speech-to-text
    audio  = await voz.sintetizar("Tengo sed.", "mp3")        # text-to-speech
    charla = await conversar(audio, mime, chat_id, db, ...)   # oír → responder → hablar

La voz es una capa por fuera de `responder.responder`: el guardrail, el RAG y
el log en `conversaciones` son los mismos para el texto de Telegram, la nota de
voz de Telegram y la pestaña «Hablar con Ruperto» del front. Si ElevenLabs
falla o no tiene créditos, la respuesta en texto sale igual (`audio = None`).

HTTP directo con httpx (ya es dependencia de python-telegram-bot y de
google-genai): son dos endpoints y no justifican otro SDK. El cliente HTTP se
inyecta para testear sin red.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from . import persona
from .responder import Respuesta, responder

log = logging.getLogger("ruperto.voz")

URL_DEFAULT = "https://api.elevenlabs.io"
# La voz se elige con ELEVENLABS_VOZ_ID. Si no está, se le pregunta a la cuenta
# qué voces tiene (`GET /v1/voices`) y se usa la primera de PREFERIDAS que
# exista, o la primera de la lista: las voces prefabricadas cambian de id con
# el tiempo y dependen de la cuenta, así que un id fijo en el código se rompe.
# VOZ_RESPALDO sólo se usa si la clave no tiene permiso para listar voces.
PREFERIDAS = ("6WwXjDDEMyNmFG95zycZ", "JBFqnCBsd6RMkjVDRZzb",    # Eldrin / George
              "8dEUmyPMdDdK91vboYih", "nPczCjzI2devNBz1zQrb",    # Sawyer / Brian
              "fnYMz3F5gMEDGMWcH1ex", "onwK4e9ZLuTAKqWW03F9")    # Finley / Daniel
VOZ_RESPALDO = "JBFqnCBsd6RMkjVDRZzb"
# Flash v2.5: el de menor latencia y medio crédito por carácter; acepta
# `language_code`, así los números y las abreviaturas se leen en español.
MODELO_TTS_DEFAULT = "eleven_flash_v2_5"
MODELO_STT_DEFAULT = "scribe_v2"
# Formatos de salida: mp3 para el navegador, Ogg/Opus para la nota de voz de Telegram.
FORMATOS = {
    "mp3": ("mp3_44100_64", "audio/mpeg"),
    "opus": ("opus_48000_32", "audio/ogg"),
}
# multilingual_v2 no acepta `language_code`; el resto sí (y si alguno lo
# rechaza, se reintenta sin el campo y no se vuelve a mandar).
MODELOS_SIN_IDIOMA = ("eleven_multilingual_v2", "eleven_monolingual_v1", "eleven_multilingual_v1")

MAX_CHARS_TTS = 900            # ~1 minuto hablando; más que eso no es una charla
MAX_BYTES_AUDIO = 3 * 1024 * 1024
MIN_BYTES_AUDIO = 800          # menos que esto es un toque accidental al micrófono
TIMEOUT_S = 40.0
# Tope diario de caracteres sintetizados, por proceso: el front es público y los
# créditos de ElevenLabs son finitos. Pasado el tope se responde sólo en texto.
MAX_CHARS_DIA_DEFAULT = 20000
# Lo mismo para oír: Scribe cobra por minuto de audio y un pedido no dice
# cuánto dura hasta que se transcribe, así que se cuentan los audios.
MAX_AUDIOS_DIA_DEFAULT = 400
PAUSA_SIN_VOZ_S = 600          # sin créditos o sin clave: no insistir por 10 minutos
CACHE_FRASES = 64              # audios de textos fijos (saludo, cosquillas, rechazos)


class ErrorVoz(Exception):
    """ElevenLabs no pudo oír o hablar; el texto de la respuesta no depende de esto."""


class SinVoz(ErrorVoz):
    """Falta ELEVENLABS_API_KEY, o la clave fue rechazada."""


class SinCreditos(ErrorVoz):
    """Se acabaron los créditos (de ElevenLabs o el tope diario propio)."""


class TopeDiario(SinCreditos):
    """Se alcanzó el tope diario propio (caracteres o audios): vuelve a medianoche UTC."""


class NoSeEntendio(ErrorVoz):
    """El audio no trae palabras (silencio, ruido) o no se pudo leer."""


def configurada(env: dict[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("ELEVENLABS_API_KEY", "").strip())


# ─── texto para ser escuchado ─────────────────────────────────────────────
_PIE_FUENTE = re.compile(r"\n+\s*📚[^\n]*", re.S)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF️‍⚪]")
_REEMPLAZOS = (
    (re.compile(r"(\d)\s*°\s*C\b"), r"\1 grados"),
    (re.compile(r"°\s*C\b"), "grados"),
    (re.compile(r"(\d)\s*mV\b"), r"\1 milivoltios"),
    (re.compile(r"\bmV\b"), "milivoltios"),
    (re.compile(r"(\d)\s*kPa\b"), r"\1 kilopascales"),
    (re.compile(r"(\d)\s*%"), r"\1 por ciento"),
    (re.compile(r"(?<![\d.,])1\s*h\b"), "1 hora"),      # «3,1 h» no es singular
    (re.compile(r"(\d)\s*h\b"), r"\1 horas"),
    (re.compile(r"(?<![\d.,])1\s*min\b"), "1 minuto"),
    (re.compile(r"(\d)\s*min\b"), r"\1 minutos"),
    (re.compile(r"(\d)\s*cm\b"), r"\1 centímetros"),
    (re.compile(r"\bHR\b"), "humedad"),
    (re.compile(r"\bVPD\b"), "déficit de presión de vapor"),
    (re.compile(r"\bESP32\b"), "E S P 32"),
    (re.compile(r"/(start|estado|riego|silencio|ayuda)\b"), r"\1"),
    (re.compile(r"(\d)\s*[–—]\s*(\d)"), r"\1 a \2"),
)


def texto_hablado(texto: str, max_chars: int = MAX_CHARS_TTS) -> str:
    """Deja el texto de una respuesta como para leerlo en voz alta: sin el pie
    de fuentes, emojis ni viñetas, con las unidades en palabras, y cortado en
    el final de una oración si es muy largo."""
    t = _PIE_FUENTE.sub("", texto)
    t = _EMOJI.sub("", t)
    lineas = []
    for linea in t.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        # Viñeta → oración. El guion sólo si no le sigue un dígito: "-5 mV" es un número.
        if linea[0] in "•*·" or (linea[0] == "-" and not linea[1:2].isdigit()):
            linea = linea[1:].strip()
        linea = linea.replace(" · ", ", ")
        if linea and linea[-1] not in ".!?:…":
            linea += "."
        lineas.append(linea)
    t = " ".join(lineas)
    for patron, por in _REEMPLAZOS:
        t = patron.sub(por, t)
    t = re.sub(r"[*_`#\[\]()«»]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not re.search(r"\w", t):        # sólo quedaron signos: no hay nada para decir
        return ""
    if len(t) > max_chars:
        corte = max(t.rfind(". ", 0, max_chars), t.rfind("! ", 0, max_chars),
                    t.rfind("? ", 0, max_chars))
        t = t[:corte + 1] if corte > max_chars // 3 else t[:max_chars].rsplit(" ", 1)[0] + "."
    return t


# ─── cliente de ElevenLabs ────────────────────────────────────────────────
def _detalle(r: httpx.Response) -> tuple[str, str]:
    """(código, mensaje) del cuerpo de error de ElevenLabs. `detail` viene como
    objeto ({"code"|"status", "message"}), como lista (422) o como texto."""
    try:
        d = r.json().get("detail")
    except Exception:
        return "", r.text[:200]
    if isinstance(d, dict):
        codigo = " ".join(str(d[k]) for k in ("code", "status", "type") if d.get(k))
        return codigo, str(d.get("message") or "")[:200]
    return "", str(d)[:200]


class _ErrorHttp(ErrorVoz):
    """Error de ElevenLabs sin una traducción más precisa; guarda el estado."""

    def __init__(self, texto: str, estado: int, codigo: str):
        super().__init__(texto)
        self.estado, self.codigo = estado, codigo


def _traducir(r: httpx.Response) -> ErrorVoz:
    codigo, mensaje = _detalle(r)
    texto = f"ElevenLabs {r.status_code} {codigo}: {mensaje}".strip()
    # Sin créditos llega como 402 `insufficient_credits` o, en el formato
    # anterior, como 400/401 con status `quota_exceeded`: se mira antes que el 401.
    if r.status_code == 402 or "quota" in codigo or "insufficient_credits" in codigo:
        return SinCreditos(texto)
    if r.status_code in (401, 403):
        return SinVoz(texto)
    return _ErrorHttp(texto, r.status_code, codigo)


class ClienteVoz:
    def __init__(self, api_key: str | None = None, *, voz_id: str | None = None,
                 modelo_tts: str | None = None, modelo_stt: str | None = None,
                 url: str | None = None, http: httpx.AsyncClient | None = None,
                 max_chars_dia: int | None = None):
        self.api_key = (api_key or os.getenv("ELEVENLABS_API_KEY", "")).strip()
        if not self.api_key:
            raise SinVoz("falta ELEVENLABS_API_KEY")
        self.voz_id: str | None = voz_id or os.getenv("ELEVENLABS_VOZ_ID") or None
        self._voz_fija = self.voz_id is not None
        self._con_idioma = True
        self.opus_es_ogg: bool | None = None       # se aprende con el primer audio
        self.modelo_tts = modelo_tts or os.getenv("ELEVENLABS_MODELO_TTS") or MODELO_TTS_DEFAULT
        self.modelo_stt = modelo_stt or os.getenv("ELEVENLABS_MODELO_STT") or MODELO_STT_DEFAULT
        self.url = (url or os.getenv("ELEVENLABS_URL") or URL_DEFAULT).rstrip("/")
        self._http = http or httpx.AsyncClient(timeout=TIMEOUT_S)
        self.max_chars_dia = (max_chars_dia if max_chars_dia is not None
                              else int(os.getenv("VOZ_MAX_CHARS_DIA") or MAX_CHARS_DIA_DEFAULT))
        self.max_audios_dia = int(os.getenv("VOZ_MAX_AUDIOS_DIA") or MAX_AUDIOS_DIA_DEFAULT)
        self._dia: str = ""
        self._chars_hoy = 0
        self._audios_hoy = 0
        self._frases: OrderedDict[str, bytes] = OrderedDict()
        self._caida_hasta = 0.0

    # — fuera de servicio —
    @property
    def disponible(self) -> bool:
        """False durante un rato después de que ElevenLabs rechazó la clave o
        se acabaron los créditos: así el front se entera (`/estado` dice
        `voz: false`) y pasa a la voz del navegador en vez de insistir."""
        return time.monotonic() >= self._caida_hasta

    def _anotar_caida(self, e: Exception) -> None:
        if isinstance(e, TopeDiario):
            # El tope propio no se levanta hasta el día siguiente (UTC): reabrir
            # cada 10 minutos sólo le avisaría al front de una voz que no volvió.
            ahora = datetime.now(UTC)
            manana = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            self._caida_hasta = time.monotonic() + (manana - ahora).total_seconds()
        elif isinstance(e, (SinVoz, SinCreditos)):
            self._caida_hasta = time.monotonic() + PAUSA_SIN_VOZ_S

    # — cupo propio —
    def _hoy(self) -> None:
        hoy = datetime.now(UTC).date().isoformat()
        if hoy != self._dia:
            self._dia, self._chars_hoy, self._audios_hoy = hoy, 0, 0

    def _gastar(self, n: int) -> None:
        self._hoy()
        if self._chars_hoy + n > self.max_chars_dia:
            raise TopeDiario(f"tope diario de voz alcanzado ({self.max_chars_dia} caracteres)")
        self._chars_hoy += n

    def _gastar_audio(self) -> None:
        self._hoy()
        if self._audios_hoy >= self.max_audios_dia:
            raise TopeDiario(f"tope diario de audios alcanzado ({self.max_audios_dia})")
        self._audios_hoy += 1

    @staticmethod
    def _json(r: httpx.Response) -> dict:
        try:
            d = r.json()
        except ValueError as e:
            raise ErrorVoz("ElevenLabs respondió algo que no es JSON") from e
        return d if isinstance(d, dict) else {}

    async def _pedir(self, metodo: str, ruta: str, **kw) -> httpx.Response:
        try:
            r = await self._http.request(metodo, f"{self.url}{ruta}",
                                         headers={"xi-api-key": self.api_key}, **kw)
        except httpx.HTTPError as e:
            raise ErrorVoz(f"ElevenLabs no respondió: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise _traducir(r)
        return r

    async def _post(self, ruta: str, **kw) -> httpx.Response:
        return await self._pedir("POST", ruta, **kw)

    async def _elegir_voz(self) -> str:
        """La voz a usar cuando no hay ELEVENLABS_VOZ_ID: una de las que la
        cuenta tiene de verdad."""
        try:
            voces = self._json(await self._pedir("GET", "/v1/voices")).get("voices") or []
            ids = [v.get("voice_id") for v in voces if v.get("voice_id")]
        except SinCreditos:
            raise
        except ErrorVoz as e:
            log.warning("no se pudieron listar las voces (%s): uso la de respaldo", e)
            ids = []
        elegida = next((v for v in PREFERIDAS if v in ids), ids[0] if ids else VOZ_RESPALDO)
        log.info("voz de Ruperto: %s (%d voces en la cuenta)", elegida, len(ids))
        return elegida

    async def transcribir(self, audio: bytes, mime: str = "audio/webm") -> str:
        """Audio → texto en español. `NoSeEntendio` si no hay palabras."""
        if len(audio) < MIN_BYTES_AUDIO:
            raise NoSeEntendio("audio vacío o demasiado corto")
        if len(audio) > MAX_BYTES_AUDIO:
            raise ErrorVoz("el audio supera el tamaño permitido")
        mime = (mime or "audio/webm").split(";", 1)[0].strip().lower()
        ext = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3",
               "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac",
               "video/webm": "webm", "video/mp4": "mp4"}.get(mime, "bin")
        try:
            self._gastar_audio()
            r = await self._post(
                "/v1/speech-to-text",
                data={"model_id": self.modelo_stt, "language_code": "es",
                      "tag_audio_events": "false", "diarize": "false"},
                files={"file": (f"audio.{ext}", audio, mime)})
        except _ErrorHttp as e:
            if e.estado in (400, 422) and "model" not in e.codigo:   # archivo ilegible para Scribe
                raise NoSeEntendio(str(e)) from e
            raise
        except (SinVoz, SinCreditos) as e:
            self._anotar_caida(e)
            raise
        texto = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", self._json(r).get("text") or "")   # (risas), [música]
        texto = re.sub(r"\s+", " ", texto).strip()
        if not re.search(r"[a-záéíóúñ]{2}", texto, re.I):
            raise NoSeEntendio("no se distinguen palabras")
        return texto[:600]

    async def _tts(self, salida: str, cuerpo: dict) -> httpx.Response:
        return await self._post(f"/v1/text-to-speech/{self.voz_id}",
                                params={"output_format": salida}, json=cuerpo)

    async def sintetizar(self, texto: str, formato: str = "mp3", *, fijo: bool = False) -> bytes:
        """Texto → audio (`formato` ∈ FORMATOS). `fijo=True` cachea el audio: para
        los textos que no cambian (saludo, cosquillas, rechazos) no se gastan
        créditos dos veces."""
        hablado = texto_hablado(texto)
        if not hablado:
            raise ErrorVoz("no hay nada para decir")
        salida, _ = FORMATOS[formato]
        clave = hashlib.sha1(f"{self.modelo_tts}|{salida}|{hablado}".encode()).hexdigest()
        if fijo and clave in self._frases:
            self._frases.move_to_end(clave)
            return self._frases[clave]
        try:
            if self.voz_id is None:
                self.voz_id = await self._elegir_voz()
            self._gastar(len(hablado))
        except (SinVoz, SinCreditos) as e:
            self._anotar_caida(e)
            raise
        cuerpo: dict = {"text": hablado, "model_id": self.modelo_tts,
                        "voice_settings": {"stability": 0.4, "similarity_boost": 0.75,
                                           "style": 0.35, "use_speaker_boost": True}}
        if self._con_idioma and self.modelo_tts not in MODELOS_SIN_IDIOMA:
            cuerpo["language_code"] = "es"
        try:
            r = await self._sintetizar_con_reintento(salida, cuerpo)
        except Exception as e:
            self._chars_hoy = max(0, self._chars_hoy - len(hablado))   # lo que no se dijo no cuenta
            self._anotar_caida(e)
            raise
        audio = r.content
        if not audio:
            raise ErrorVoz("ElevenLabs devolvió un audio vacío")
        if formato == "opus":
            # Telegram sólo acepta notas de voz en Ogg/Opus: se mira el contenedor
            # en vez de suponerlo (lo usa telegram_bot para elegir cómo mandarlo).
            self.opus_es_ogg = audio[:4] == b"OggS"
        if fijo:
            self._frases[clave] = audio
            while len(self._frases) > CACHE_FRASES:
                self._frases.popitem(last=False)
        return audio

    async def _sintetizar_con_reintento(self, salida: str, cuerpo: dict) -> httpx.Response:
        sin_idioma = False
        try:
            r = await self._tts(salida, cuerpo)
        except _ErrorHttp as e:
            if e.estado == 404 and not self._voz_fija and "model" not in e.codigo:
                # La voz elegida ya no existe en la cuenta: se elige de nuevo, una vez.
                self.voz_id = await self._elegir_voz()
            elif e.estado in (400, 422) and "language_code" in cuerpo:
                sin_idioma = True
                del cuerpo["language_code"]
            else:
                raise
            r = await self._tts(salida, cuerpo)
            if sin_idioma:
                # Recién ahora se sabe que el 400 era por el idioma: si el
                # reintento también falla, el motivo era otro y no se apaga.
                self._con_idioma = False
        return r


_cliente: ClienteVoz | None = None


def cliente() -> ClienteVoz:
    """El cliente del proceso (uno solo: lleva el tope diario y el caché)."""
    global _cliente
    if _cliente is None:
        _cliente = ClienteVoz()
    return _cliente


def reiniciar() -> None:
    """Olvida el cliente del proceso (tests, o si cambió la clave)."""
    global _cliente
    _cliente = None


# ─── charla completa: oír → responder → hablar ────────────────────────────
@dataclass
class Charla:
    pregunta: str                 # lo que se entendió (o lo que se escribió)
    respuesta: Respuesta | None   # None si no se llegó a responder (no se entendió)
    texto: str                    # lo que dice Ruperto
    audio: bytes | None = None
    audio_mime: str | None = None
    error_voz: str | None = None  # por qué no hay audio, o por qué no se entendió
    ms_oir: int = 0
    ms_hablar: int = 0


async def hablar(texto: str, voz: ClienteVoz | None, formato: str = "mp3", *,
                 fijo: bool = False) -> tuple[bytes | None, str | None, str | None]:
    """(audio, mime, error). Nunca levanta: sin voz, la charla sigue en texto."""
    if voz is None:
        return None, None, "sin-voz"
    try:
        return await voz.sintetizar(texto, formato, fijo=fijo), FORMATOS[formato][1], None
    except SinCreditos as e:
        log.warning("voz sin créditos: %s", e)
        return None, None, "sin-creditos"
    except SinVoz as e:
        log.error("ElevenLabs rechazó la clave: %s", e)
        return None, None, "sin-voz"
    except Exception as e:
        log.exception("no se pudo sintetizar la voz")
        return None, None, f"error: {type(e).__name__}"


def _es_fijo(r: Respuesta) -> bool:
    return r.texto in persona.RECHAZOS or r.texto in (persona.SIN_ALIENTO, persona.ERROR)


async def conversar(audio: bytes | None, mime: str, chat_id: int, db: Session, *,
                    texto: str | None = None, voz: ClienteVoz | None = None,
                    formato: str = "mp3", con_audio: bool = True, **kw) -> Charla:
    """Una vuelta de charla. Entra audio (se transcribe) o `texto`; sale la
    respuesta de siempre (`responder`, con `voz=True` para que sea corta y sin
    símbolos) y, si se puede, su audio. `kw` va a `responder` (gemini, buscar,
    ahora, memoria: para los tests)."""
    t0 = time.perf_counter()
    if texto is None:
        if voz is None:
            return Charla("", None, persona.SIN_OIDOS, error_voz="sin-voz")
        try:
            texto = await voz.transcribir(audio or b"", mime)
        except NoSeEntendio as e:
            log.info("chat %s: no se entendió el audio (%s)", chat_id, e)
            a, m, _ = await hablar(persona.NO_ENTENDI, voz if con_audio else None, formato, fijo=True)
            return Charla("", None, persona.NO_ENTENDI, a, m, "no-se-entendio",
                          ms_oir=int((time.perf_counter() - t0) * 1000))
        except (SinVoz, SinCreditos) as e:
            log.warning("chat %s: no puedo oír (%s)", chat_id, e)
            return Charla("", None, persona.SIN_OIDOS,
                          error_voz="sin-creditos" if isinstance(e, SinCreditos) else "sin-voz")
        except Exception as e:
            log.exception("chat %s: falló la transcripción", chat_id)
            return Charla("", None, persona.SIN_OIDOS, error_voz=f"error: {type(e).__name__}")
    ms_oir = int((time.perf_counter() - t0) * 1000)
    r = await responder(texto, chat_id, db, voz=True, **kw)
    t1 = time.perf_counter()
    a, m, err = (await hablar(r.texto, voz, formato, fijo=_es_fijo(r))
                 if con_audio else (None, None, None))
    return Charla(texto, r, r.texto, a, m, err, ms_oir=ms_oir,
                  ms_hablar=int((time.perf_counter() - t1) * 1000))


__all__ = ["Charla", "ClienteVoz", "ErrorVoz", "NoSeEntendio", "SinCreditos", "SinVoz",
           "cliente", "configurada", "conversar", "hablar", "reiniciar", "texto_hablado"]
