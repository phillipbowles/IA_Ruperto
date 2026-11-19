"""Verifica la voz de Ruperto contra ElevenLabs de verdad (docs/ENTREGA3.md D223).

    ELEVENLABS_API_KEY=... python scripts/probar_voz.py            # desde backend/
    docker compose exec backend python scripts/probar_voz.py        # con el .env del compose
    railway run -s Backend python backend/scripts/probar_voz.py     # con las variables de Railway

Gasta unos 150 caracteres de créditos. Comprueba, en orden, todo lo que el
código da por cierto y que sin una clave real no se puede probar:

  1. la clave sirve y qué voces tiene la cuenta (y cuál se va a usar);
  2. texto → mp3 (lo que reproduce la pestaña «Hablar con Ruperto»);
  3. texto → opus, y que venga en contenedor Ogg (lo que Telegram exige para
     una nota de voz; si no, el bot manda mp3 como audio);
  4. ese mismo audio → texto: lo que se dijo se tiene que poder volver a oír.

Sale con 0 si todo anduvo. Con `--guardar DIR` deja los audios para escucharlos.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite://")     # voz.py importa responder → database

from app.bot import voz  # noqa: E402

FRASE = "Hola, soy Ruperto. Tengo la tierra húmeda y estoy a 21,4 °C, con 69 % de humedad."
CLAVES = ("ruperto", "tierra", "humeda", "grados")


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


async def main(guardar: Path | None) -> int:
    if not voz.configurada():
        print("✗ Falta ELEVENLABS_API_KEY en el entorno.")
        return 2
    c = voz.ClienteVoz()
    print(f"Modelos: TTS {c.modelo_tts} · STT {c.modelo_stt} · {c.url}")
    fallas = 0

    def paso(ok: bool, texto: str) -> None:
        nonlocal fallas
        fallas += not ok
        print(("✓ " if ok else "✗ ") + texto)

    # 1. clave y voces
    try:
        voces = (await c._pedir("GET", "/v1/voices")).json().get("voices") or []
        paso(True, f"La clave sirve: {len(voces)} voces en la cuenta")
        for v in voces[:12]:
            idiomas = (v.get("labels") or {}).get("language") or (v.get("labels") or {}).get("accent") or ""
            print(f"    {v.get('voice_id')}  {v.get('name')}  [{v.get('category')}] {idiomas}")
    except voz.SinVoz as e:
        if "missing_permissions" not in str(e):
            paso(False, f"La clave fue rechazada: {e}")
            return 1
        print(f"· La clave no puede listar voces ({e}); sigo con ELEVENLABS_VOZ_ID o la de respaldo.")
    except voz.ErrorVoz as e:
        paso(False, f"No se pudieron listar las voces: {e}")

    # 2. mp3
    mp3 = b""
    try:
        mp3 = await c.sintetizar(FRASE, "mp3")
        es_mp3 = mp3[:3] == b"ID3" or (len(mp3) > 2 and mp3[0] == 0xFF and mp3[1] & 0xE0 == 0xE0)
        paso(es_mp3 and len(mp3) > 5000, f"Texto → mp3: {len(mp3)} bytes con la voz {c.voz_id}"
             + ("" if es_mp3 else " (¡no parece un mp3!)"))
        print(f"    se leyó: «{voz.texto_hablado(FRASE)}» · language_code={'sí' if c._con_idioma else 'no'}")
    except voz.ErrorVoz as e:
        paso(False, f"Texto → mp3 falló: {type(e).__name__}: {e}")

    # 3. opus en Ogg
    opus = b""
    try:
        opus = await c.sintetizar(FRASE, "opus")
        if c.opus_es_ogg:
            paso(True, f"Texto → opus en Ogg: {len(opus)} bytes (Telegram lo muestra como nota de voz)")
        else:
            print(f"· El opus no viene en Ogg (empieza con {opus[:4]!r}): en Telegram el bot "
                  "manda mp3 como audio. Funciona, pero no se ve como nota de voz.")
    except voz.ErrorVoz as e:
        paso(False, f"Texto → opus falló: {type(e).__name__}: {e}")

    # 4. ida y vuelta: lo que dijo se tiene que entender
    for nombre, audio, mime in (("mp3", mp3, "audio/mpeg"), ("ogg", opus, "audio/ogg")):
        if not audio or (nombre == "ogg" and not c.opus_es_ogg):
            continue
        try:
            oido = await c.transcribir(audio, mime)
            faltan = [k for k in CLAVES if k not in _plano(oido)]
            paso(not faltan, f"Audio {nombre} → texto: «{oido}»" + (f" (faltan: {faltan})" if faltan else ""))
        except voz.ErrorVoz as e:
            paso(False, f"Audio {nombre} → texto falló: {type(e).__name__}: {e}")

    if guardar:
        guardar.mkdir(parents=True, exist_ok=True)
        for nombre, datos in (("ruperto.mp3", mp3), ("ruperto.ogg", opus)):
            if datos:
                (guardar / nombre).write_bytes(datos)
        print(f"Audios en {guardar}/")

    print("\nTodo en orden: Ruperto oye y habla." if not fallas else f"\n{fallas} comprobación(es) fallaron.")
    return 1 if fallas else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--guardar", type=Path, help="carpeta donde dejar los audios generados")
    sys.exit(asyncio.run(main(ap.parse_args().guardar)))
