import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { enviar, obtener } from "../api/cliente";
import type { CharlaRuperto, Clase, EstadoRuperto, FraseRuperto } from "../tipos";
import { LirioSvg } from "./AvatarLirio";
import {
  Microfono, Parlante, desbloquearAudio, dictado, hayDictado, hayMicrofono, hayVozNavegador,
} from "../lib/voz";
import type { Dictado } from "../lib/voz";

/** Pestaña «Hablar con Ruperto»: se le habla al lirio y contesta en voz alta,
 *  con el mismo avatar del tablero moviendo la boca al ritmo del audio.
 *
 *  El cerebro es el del bot de Telegram (`/api/v1/ruperto/*` llama al mismo
 *  `responder`). La voz es ElevenLabs en el servidor; si no está configurado o
 *  se quedó sin créditos, se usa el dictado y la voz del navegador, y siempre
 *  se le puede escribir. Una vuelta: reposo → escuchando → pensando → hablando. */

type Fase = "reposo" | "escuchando" | "pensando" | "hablando";
type Turno = { id: number; quien: "vos" | "ruperto"; texto: string };

const NOMBRES: Record<Clase | "sin", string> = {
  saludable: "Saludable", estresada: "Estresado", marchita: "Marchito", sin: "Sin datos recientes",
};

const SUGERENCIAS = ["¿Cómo estás?", "¿Necesitás agua?", "¿Cuándo te regaron?", "¿Qué cuidados necesitás?"];

const ROTULO: Record<Fase, string> = {
  reposo: "Tocá el micrófono y hablale",
  escuchando: "Te escucho… tocá de nuevo cuando termines",
  pensando: "Pensando…",
  hablando: "Tocá para interrumpirlo",
};

const CLAVE_SESION = "ruperto-sesion";
let sesionEnMemoria: string | null = null;

/** Identifica la charla de este navegador (la memoria corta del bot va por
 *  chat). Si localStorage no está disponible, dura lo que dure la pestaña. */
function sesion(): string {
  const nueva = () => globalThis.crypto?.randomUUID?.() ?? `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  try {
    let s = localStorage.getItem(CLAVE_SESION);
    if (!s) {
      s = nueva();
      localStorage.setItem(CLAVE_SESION, s);
    }
    return s;
  } catch {
    return (sesionEnMemoria ??= nueva());
  }
}

function motivo(e: unknown): string {
  if (e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "SecurityError")) {
    return "Necesito permiso para usar el micrófono. Habilitalo en el navegador, o escribime acá abajo.";
  }
  if (e instanceof DOMException && e.name === "NotFoundError") {
    return "No encontré ningún micrófono. Podés escribirme acá abajo.";
  }
  if (e instanceof DOMException) return "No pude usar el micrófono (¿lo está usando otra aplicación?). Podés escribirme acá abajo.";
  if (e instanceof SyntaxError) return "El servidor contestó algo raro. Probá de nuevo en un rato.";
  if (e instanceof TypeError) return "No pude conectarme con el servidor. Revisá la conexión y probá de nuevo.";
  return e instanceof Error && e.message ? e.message : "Algo falló. Probá de nuevo.";
}

export function HablarRuperto() {
  const { data: info, error: errorInfo, refetch } = useQuery({
    queryKey: ["ruperto-estado"],
    queryFn: () => obtener<EstadoRuperto>("/ruperto/estado"),
    refetchInterval: 60_000,
  });

  const [fase, setFase] = useState<Fase>("reposo");
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [estadoVivo, setEstadoVivo] = useState<Clase | null | undefined>(undefined);
  const [cosquillas, setCosquillas] = useState(false);

  const escena = useRef<HTMLButtonElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const microfono = useRef<Microfono | null>(null);
  const dictando = useRef<Dictado | null>(null);
  const parlante = useRef<Parlante | null>(null);
  const ficha = useRef(0);        // invalida lo que quedó en vuelo de una vuelta anterior
  const toques = useRef(0);
  const proximoId = useRef(1);
  const preguntas = useRef(0);
  const ocupado = useRef(false);  // hay una pregunta en vuelo (el estado de React llega un render tarde)

  if (parlante.current === null) parlante.current = new Parlante();

  // El nivel del audio va derecho al estilo, sin pasar por React: cambia 60 veces por segundo.
  const boca = useCallback((n: number) => { escena.current?.style.setProperty("--boca", n.toFixed(3)); }, []);
  const oido = useCallback((n: number) => { boton.current?.style.setProperty("--oido", n.toFixed(3)); }, []);

  const agregar = useCallback((quien: Turno["quien"], t: string) => {
    setTurnos((ts) => [...ts, { id: proximoId.current++, quien, texto: t }].slice(-40));
  }, []);

  // Una medición nueva manda sobre el estado que vino con la última respuesta.
  useEffect(() => { setEstadoVivo(undefined); }, [info?.edad_min, info?.estado]);

  useEffect(() => () => {
    ficha.current += 1;
    microfono.current?.cancelar();
    dictando.current?.cancelar();
    parlante.current?.parar();
  }, []);

  async function decir(textoRespuesta: string, audio: string | null, mime: string | null, f: number) {
    setFase("hablando");
    if (audio) await parlante.current!.reproducir(audio, mime ?? "audio/mpeg", boca);
    else await parlante.current!.decir(textoRespuesta, boca);
    if (f === ficha.current) setFase("reposo");
  }

  async function preguntar(cuerpo: Blob | { texto: string; con_audio: boolean }) {
    const f = ++ficha.current;
    const mia = ++preguntas.current;
    // Se libera cuando ESTA pregunta termina, aunque otra cosa (unas cosquillas)
    // haya cambiado la ficha en el medio: si no, el chat quedaba trabado.
    const liberar = () => { if (mia === preguntas.current) ocupado.current = false; };
    ocupado.current = true;
    setFase("pensando");
    setAviso(null);
    try {
      const esAudio = cuerpo instanceof Blob;
      const c = await enviar<CharlaRuperto>(esAudio ? "/ruperto/hablar" : "/ruperto/mensaje", cuerpo,
                                            { "X-Ruperto-Sesion": sesion() });
      liberar();
      if (f !== ficha.current) return;
      if (c.error_voz !== "no-se-entendio") setEstadoVivo(c.estado);
      if (esAudio && c.pregunta) agregar("vos", c.pregunta);
      agregar("ruperto", c.respuesta);
      // El servidor se quedó sin voz a mitad de camino: que el front se entere.
      if (c.error_voz === "sin-voz" || c.error_voz === "sin-creditos") void refetch();
      await decir(c.respuesta, c.audio_b64, c.audio_mime, f);
    } catch (e) {
      liberar();
      if (f !== ficha.current) return;
      setAviso(motivo(e));
      setFase("reposo");
      void refetch();
    }
  }

  const conVozServidor = !!info?.voz && hayMicrofono();
  const puedeOir = !!info?.chat && (conVozServidor || hayDictado());

  async function alMicrofono() {
    desbloquearAudio();
    if (fase === "pensando" || ocupado.current) return;
    if (fase === "escuchando") {
      microfono.current?.terminar();
      dictando.current?.terminar();
      return;
    }
    if (fase === "hablando") {      // interrumpirlo: se calla y vuelve al reposo
      ficha.current += 1;
      parlante.current?.parar();
      setFase("reposo");
      return;
    }
    const f = ++ficha.current;
    setAviso(null);
    setFase("escuchando");
    try {
      if (conVozServidor) {
        const m = new Microfono();
        microfono.current = m;
        const fin = await m.grabar(oido);
        microfono.current = null;
        if (f !== ficha.current) return;
        if (fin.tipo === "audio") return await preguntar(fin.audio);
        if (fin.tipo === "silencio") setAviso("No escuché nada. Tocá el micrófono y hablame de cerca.");
      } else {
        const d = dictado();
        dictando.current = d;
        const oidoTexto = await d.texto;
        dictando.current = null;
        if (f !== ficha.current) return;
        if (oidoTexto) {
          agregar("vos", oidoTexto);
          return await preguntar({ texto: oidoTexto.slice(0, 400), con_audio: true });
        }
        setAviso("No escuché nada. Tocá el micrófono y hablame de cerca.");
      }
      setFase("reposo");
    } catch (e) {
      microfono.current = null;
      dictando.current = null;
      if (f !== ficha.current) return;
      setAviso(motivo(e));
      setFase("reposo");
    }
  }

  function mandarTexto(t: string) {
    const limpio = t.trim().slice(0, 400);
    if (!limpio || ocupado.current || fase === "pensando" || fase === "escuchando" || !info?.chat) return;
    desbloquearAudio();
    parlante.current?.parar();
    agregar("vos", limpio);
    setTexto("");
    void preguntar({ texto: limpio, con_audio: true });
  }

  function alEnviar(e: FormEvent) {
    e.preventDefault();
    mandarTexto(texto);
  }

  async function alTocarlo() {
    desbloquearAudio();
    if (fase !== "reposo" || ocupado.current) return;
    const f = ++ficha.current;
    setAviso(null);
    setCosquillas(true);
    window.setTimeout(() => setCosquillas(false), 950);
    try {
      const fr = await obtener<FraseRuperto>(`/ruperto/frase/cosquillas?n=${toques.current++}`);
      if (f !== ficha.current) return;
      agregar("ruperto", fr.texto);
      await decir(fr.texto, fr.audio_b64, fr.audio_mime, f);
    } catch {
      // Las cosquillas son un adorno: si fallan, no se le avisa a nadie.
      if (f === ficha.current) setFase("reposo");
    }
  }

  const estado = estadoVivo !== undefined ? estadoVivo : info?.estado ?? null;
  const clave = estado ?? "sin";
  const ultimo = [...turnos].reverse().find((t) => t.quien === "ruperto");
  const globo = fase === "pensando" ? null : ultimo?.texto ?? info?.saludo ?? "…";
  const datos = info && !info.sensores_caidos ? [
    info.tierra && `Tierra ${info.tierra}`,
    info.temperatura_c !== null && `${info.temperatura_c.toFixed(1).replace(".", ",")} °C`,
    info.humedad_pct !== null && `Humedad ${info.humedad_pct.toFixed(0)} %`,
    info.h_desde_riego !== null && `Último riego hace ${info.h_desde_riego.toFixed(0)} h`,
  ].filter(Boolean) as string[] : [];

  const clases = ["ruperto__escena", "lirio", `lirio--${clave}`, fase !== "reposo" && `lirio--${fase}`,
                  cosquillas && "lirio--cosquillas"].filter(Boolean).join(" ");

  return (
    <section className={`ruperto ruperto--${fase}`}>
      <div className="ruperto__avatar">
        <button type="button" className={clases} ref={escena} onClick={alTocarlo}
                aria-label="Hacerle cosquillas a Ruperto" title="Tocalo">
          <LirioSvg nombre={NOMBRES[clave]} />
        </button>
        <div className="ruperto__estado">
          <span className={`ruperto__pastilla lirio--${clave}`}>
            <span className="lirio__punto" aria-hidden="true" />
            {NOMBRES[clave]}
          </span>
          {datos.map((d) => <span key={d} className="ruperto__dato">{d}</span>)}
          {info?.sensores_caidos && (
            <span className="ruperto__dato">Sus sensores no reportan: habla de la última medición</span>
          )}
        </div>
      </div>

      <div className="ruperto__charla">
        <div className="ruperto__globo" aria-live="polite">
          {globo === null
            ? <span className="ruperto__puntos" role="status" aria-label="Ruperto está pensando"><i /><i /><i /></span>
            : globo.split("\n").map((linea, i) => <p key={i}>{linea}</p>)}
        </div>

        <div className="ruperto__controles">
          <button type="button" ref={boton} className="ruperto__mic" onClick={alMicrofono}
                  disabled={!puedeOir} aria-disabled={fase === "pensando"} aria-pressed={fase === "escuchando"}
                  aria-label={fase === "escuchando" ? "Terminar de hablar"
                    : fase === "hablando" ? "Interrumpir a Ruperto" : "Hablarle a Ruperto"}>
            {fase === "hablando" ? (
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2" /></svg>
            ) : (
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="9" y="3" width="6" height="12" rx="3" />
                <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
              </svg>
            )}
          </button>
          <span className="ruperto__rotulo">
            {!info ? "Buscando a Ruperto…"
              : !info.chat ? "Ruperto no puede contestar ahora"
              : !puedeOir ? "Este navegador no tiene micrófono: escribile"
              : ROTULO[fase]}
          </span>
        </div>

        {aviso && <p className="ruperto__aviso" role="alert">{aviso}</p>}
        {errorInfo && !info && <p className="ruperto__aviso" role="alert">No pude conectarme con Ruperto.</p>}

        <form className="ruperto__form" onSubmit={alEnviar}>
          <input type="text" value={texto} maxLength={400} onChange={(e) => setTexto(e.target.value)}
                 placeholder="O escribile acá…" aria-label="Escribirle a Ruperto" disabled={!info?.chat} />
          <button type="submit" disabled={!texto.trim() || fase === "pensando" || fase === "escuchando" || !info?.chat}>
            Enviar
          </button>
        </form>

        <div className="filtros ruperto__sugerencias">
          {SUGERENCIAS.map((s) => (
            <button key={s} type="button" onClick={() => mandarTexto(s)}
                    disabled={fase === "pensando" || fase === "escuchando" || !info?.chat}>
              {s}
            </button>
          ))}
        </div>

        {info && (
          <p className="ruperto__modo">
            {!info.chat
              ? "El servidor no tiene configurado Gemini (GEMINI_API_KEY), así que Ruperto no puede armar respuestas."
              : info.voz
                ? "Voz y oído: ElevenLabs. Contesta con sus sensores y su historial, igual que en Telegram."
                : `Voz del navegador${hayVozNavegador() ? "" : " (no disponible acá)"}: el servidor no tiene `
                  + "ElevenLabs disponible ahora (sin configurar o sin créditos). Contesta igual que en Telegram."}
          </p>
        )}

        {turnos.length > 1 && (
          <details className="ruperto__historial">
            <summary>La charla ({turnos.length} mensajes)</summary>
            <ol>
              {turnos.map((t) => (
                <li key={t.id} className={`ruperto__turno ruperto__turno--${t.quien}`}>
                  <b>{t.quien === "vos" ? "Vos" : "Ruperto"}</b>
                  <span>{t.texto}</span>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
    </section>
  );
}
