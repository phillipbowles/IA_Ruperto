/** Audio de la pestaña «Hablar con Ruperto»: micrófono, parlante y la voz del
 *  navegador como respaldo.
 *
 *  - `Microfono` graba con MediaRecorder y corta solo cuando la persona deja de
 *    hablar (el nivel sale de un AnalyserNode sobre el mismo stream).
 *  - `Parlante` reproduce el audio de ElevenLabs por Web Audio y va informando
 *    el nivel, que es lo que abre la boca del avatar. Si no hay audio del
 *    servidor, lee el texto con `speechSynthesis` y simula el nivel.
 *  - `dictado()` es el reconocimiento de voz del navegador, para cuando el
 *    servidor no tiene ElevenLabs configurado.
 *
 *  Nada de esto toca React: el componente le pasa callbacks. */

export type AlNivel = (nivel: number) => void;

const SILENCIO_MS = 1300;      // callado este rato después de hablar = terminó
const ESPERA_MS = 7000;        // si en este rato no dijo nada, se cancela
const MAXIMO_MS = 20000;       // tope de una pregunta
// Umbral de voz (RMS): se ajusta al ruido del ambiente medido al empezar, entre
// estos dos límites. Fijo y alto, a quien habla bajito no se lo escucharía.
const UMBRAL_MIN = 0.012;
const UMBRAL_MAX = 0.045;
const CALIBRAR_MS = 350;
const MIN_VOZ_MS = 180;        // un golpe o un click no es voz

let contexto: AudioContext | null = null;

/** El AudioContext compartido. Hay que llamarlo dentro de un gesto del usuario
 *  (click/tap): los navegadores no dejan sonar nada antes. */
export function desbloquearAudio(): AudioContext | null {
  try {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    contexto ??= new Ctor();
    if (contexto.state === "suspended") void contexto.resume();
    return contexto;
  } catch {
    return null;
  }
}

function rms(analizador: AnalyserNode, muestras: Float32Array<ArrayBuffer>): number {
  analizador.getFloatTimeDomainData(muestras);
  let suma = 0;
  for (let i = 0; i < muestras.length; i++) suma += muestras[i] * muestras[i];
  return Math.sqrt(suma / muestras.length);
}

// ─── micrófono ────────────────────────────────────────────────────────────
export const hayMicrofono = (): boolean =>
  typeof MediaRecorder !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

function tipoGrabacion(): string {
  const candidatos = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  return candidatos.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

export type FinGrabacion =
  | { tipo: "audio"; audio: Blob }
  | { tipo: "silencio" }          // no dijo nada
  | { tipo: "cancelado" };

export class Microfono {
  private stream: MediaStream | null = null;
  private grabador: MediaRecorder | null = null;
  private fuente: MediaStreamAudioSourceNode | null = null;
  private cuadro = 0;
  private cancelado = false;
  private hablo = false;
  private cortarAlEmpezar = false;
  private resolver: ((f: FinGrabacion) => void) | null = null;

  /** Empieza a grabar. La promesa se resuelve cuando termina: sola (por
   *  silencio o por tiempo) o porque se llamó a `terminar()` / `cancelar()`.
   *  Rechaza si no hay permiso de micrófono. */
  async grabar(alNivel: AlNivel): Promise<FinGrabacion> {
    const ctx = desbloquearAudio();
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const tipo = tipoGrabacion();
    const grabador = new MediaRecorder(this.stream, tipo ? { mimeType: tipo, audioBitsPerSecond: 32000 } : undefined);
    this.grabador = grabador;
    const trozos: Blob[] = [];
    grabador.ondataavailable = (e) => { if (e.data.size) trozos.push(e.data); };

    const fin = new Promise<FinGrabacion>((resolve) => { this.resolver = resolve; });
    grabador.onstop = () => {
      this.soltar();
      alNivel(0);
      const r = this.resolver;
      this.resolver = null;
      if (this.cancelado) r?.({ tipo: "cancelado" });
      else if (!this.hablo) r?.({ tipo: "silencio" });
      else r?.({ tipo: "audio", audio: new Blob(trozos, { type: grabador.mimeType || tipo || "audio/webm" }) });
    };
    grabador.start(250);
    if (this.cancelado || this.cortarAlEmpezar) {
      // Tocó de nuevo (o se fue de la pestaña) mientras el navegador pedía permiso.
      this.cancelado = true;
      grabador.stop();
      return fin;
    }

    const inicio = performance.now();
    if (ctx) {
      this.fuente = ctx.createMediaStreamSource(this.stream);
      const analizador = ctx.createAnalyser();
      analizador.fftSize = 1024;
      this.fuente.connect(analizador);
      const muestras = new Float32Array(analizador.fftSize);
      let vozDesde = 0;
      let ultimaVoz = 0;
      let piso = Infinity;      // el nivel más bajo visto: el ruido de fondo
      const mirar = () => {
        if (grabador.state !== "recording") return;
        const ahora = performance.now();
        const nivel = rms(analizador, muestras);
        alNivel(Math.min(1, nivel * 6));
        if (nivel > 0) piso = Math.min(piso, nivel);
        const umbral = Math.min(UMBRAL_MAX, Math.max(UMBRAL_MIN, (isFinite(piso) ? piso : 0) * 3.5));
        if (ahora - inicio < CALIBRAR_MS) {
          // Todavía midiendo el ambiente; el click del botón tampoco es voz.
        } else if (nivel > umbral) {
          // MIN_VOZ_MS filtra sólo el arranque (un golpe no es voz). Una vez que
          // habló, cualquier cuadro con voz corre el silencio: si no, las pausas
          // entre sílabas lo cortaban a mitad de la frase.
          vozDesde ||= ahora;
          if (this.hablo || ahora - vozDesde >= MIN_VOZ_MS) { this.hablo = true; ultimaVoz = ahora; }
        } else {
          vozDesde = 0;
        }
        const transcurrido = ahora - inicio;
        if ((this.hablo && ahora - ultimaVoz > SILENCIO_MS)
            || (!this.hablo && transcurrido > ESPERA_MS) || transcurrido > MAXIMO_MS) {
          grabador.stop();
          return;
        }
        this.cuadro = requestAnimationFrame(mirar);
      };
      this.cuadro = requestAnimationFrame(mirar);
      // requestAnimationFrame se frena con la pestaña en segundo plano: el tope va aparte.
      window.setTimeout(() => { if (grabador.state === "recording") grabador.stop(); }, MAXIMO_MS + 500);
    } else {
      // Sin Web Audio no se puede medir el silencio: se graba hasta que la
      // persona toque de nuevo, con el tope de tiempo.
      this.hablo = true;
      window.setTimeout(() => { if (grabador.state === "recording") grabador.stop(); }, MAXIMO_MS);
    }
    return fin;
  }

  /** Corta ya y manda lo grabado (la persona tocó el botón de nuevo). */
  terminar(): void {
    // Si tocó para cortar, lo que haya dicho vale aunque el detector dude.
    this.hablo = true;
    if (this.grabador?.state === "recording") this.grabador.stop();
    else if (!this.grabador) this.cortarAlEmpezar = true;
  }

  cancelar(): void {
    this.cancelado = true;
    if (this.grabador?.state === "recording") this.grabador.stop();
    else if (this.grabador) this.soltar();
  }

  private soltar(): void {
    cancelAnimationFrame(this.cuadro);
    this.fuente?.disconnect();
    this.fuente = null;
    this.stream?.getTracks().forEach((t) => t.stop());   // apaga el indicador del micrófono
    this.stream = null;
  }
}

// ─── parlante ─────────────────────────────────────────────────────────────
export const hayVozNavegador = (): boolean => "speechSynthesis" in window;

function vozEnEspanol(): SpeechSynthesisVoice | null {
  const voces = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("es"));
  const orden = ["es-ar", "es-uy", "es-419", "es-us", "es-mx", "es-es"];
  for (const lang of orden) {
    const v = voces.find((x) => x.lang.toLowerCase().replace("_", "-") === lang);
    if (v) return v;
  }
  return voces[0] ?? null;
}

function base64ABuffer(b64: string): ArrayBuffer {
  const binario = atob(b64);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return bytes.buffer;
}

export class Parlante {
  private nodo: AudioBufferSourceNode | null = null;
  private elemento: HTMLAudioElement | null = null;
  private cuadro = 0;
  private temporizador = 0;
  private vuelta = 0;       // cambia con cada parar(): descarta lo que quedó decodificando
  private alTerminar: (() => void) | null = null;

  /** Reproduce el audio del servidor. Resuelve cuando termina (o lo paran). */
  async reproducir(b64: string, mime: string, alNivel: AlNivel): Promise<void> {
    this.parar();
    const vuelta = this.vuelta;
    const ctx = desbloquearAudio();
    if (!ctx) return this.conElemento(b64, mime, alNivel);
    let buffer: AudioBuffer;
    try {
      buffer = await ctx.decodeAudioData(base64ABuffer(b64));
    } catch {
      if (vuelta !== this.vuelta) return;
      return this.conElemento(b64, mime, alNivel);
    }
    if (vuelta !== this.vuelta) return;     // lo pararon mientras se decodificaba
    const nodo = ctx.createBufferSource();
    nodo.buffer = buffer;
    const analizador = ctx.createAnalyser();
    analizador.fftSize = 512;
    nodo.connect(analizador);
    analizador.connect(ctx.destination);
    this.nodo = nodo;
    const muestras = new Float32Array(analizador.fftSize);
    let suave = 0;
    const mirar = () => {
      // Sube rápido y baja lento: así la boca no tiembla entre sílabas.
      const nivel = Math.min(1, rms(analizador, muestras) * 5);
      suave = nivel > suave ? nivel : suave * 0.78 + nivel * 0.22;
      alNivel(suave);
      this.cuadro = requestAnimationFrame(mirar);
    };
    return new Promise<void>((resolve) => {
      this.alTerminar = () => { cancelAnimationFrame(this.cuadro); alNivel(0); resolve(); };
      nodo.onended = () => { if (this.nodo === nodo) { this.nodo = null; this.terminar(); } };
      nodo.start();
      this.cuadro = requestAnimationFrame(mirar);
    });
  }

  /** Respaldo sin Web Audio: un <audio> y la boca simulada. */
  private conElemento(b64: string, mime: string, alNivel: AlNivel): Promise<void> {
    const audio = new Audio(`data:${mime};base64,${b64}`);
    this.elemento = audio;
    return new Promise<void>((resolve) => {
      this.alTerminar = () => { this.dejarDeSimular(); alNivel(0); resolve(); };
      audio.onended = audio.onerror = () => { if (this.elemento === audio) { this.elemento = null; this.terminar(); } };
      this.simular(alNivel);
      audio.play().catch(() => { this.elemento = null; this.terminar(); });
    });
  }

  /** Lee el texto con la voz del navegador (sin ElevenLabs, o sin créditos). */
  decir(texto: string, alNivel: AlNivel): Promise<void> {
    this.parar();
    if (!hayVozNavegador() || !texto.trim()) return Promise.resolve();
    const frase = new SpeechSynthesisUtterance(texto.replace(/📚[^\n]*/g, "").replace(/[•*_]/g, " "));
    const voz = vozEnEspanol();
    if (voz) frase.voice = voz;
    frase.lang = voz?.lang ?? "es-AR";
    frase.rate = 1.02;
    frase.pitch = 0.95;
    return new Promise<void>((resolve) => {
      const fin = () => { this.dejarDeSimular(); alNivel(0); resolve(); };
      this.alTerminar = fin;
      frase.onend = frase.onerror = () => { if (this.alTerminar === fin) this.terminar(); };
      this.simular(alNivel);
      speechSynthesis.cancel();
      speechSynthesis.speak(frase);
      // Chrome a veces no dispara onend: no dejar la boca abierta para siempre.
      const tope = Math.max(4000, texto.length * 110);
      window.setTimeout(() => { if (this.alTerminar === fin && !speechSynthesis.speaking) this.terminar(); }, tope);
    });
  }

  /** Sin analizador (voz del navegador) la boca se mueve con un ritmo de sílabas. */
  private simular(alNivel: AlNivel): void {
    let fase = 0;
    this.temporizador = window.setInterval(() => {
      fase += 1;
      alNivel(fase % 4 === 3 ? 0.08 : 0.3 + Math.random() * 0.6);
    }, 95);
  }

  private dejarDeSimular(): void {
    window.clearInterval(this.temporizador);
    this.temporizador = 0;
  }

  private terminar(): void {
    const f = this.alTerminar;
    this.alTerminar = null;
    f?.();
  }

  get sonando(): boolean {
    return this.alTerminar !== null;
  }

  parar(): void {
    this.vuelta += 1;
    const nodo = this.nodo;
    this.nodo = null;
    try { nodo?.stop(); } catch { /* ya había terminado */ }
    if (this.elemento) { this.elemento.pause(); this.elemento = null; }
    if (hayVozNavegador()) speechSynthesis.cancel();
    this.terminar();
  }
}

// ─── dictado del navegador (respaldo sin ElevenLabs) ──────────────────────
type Reconocedor = {
  lang: string; interimResults: boolean; maxAlternatives: number; continuous: boolean;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
};

function ctorReconocedor(): (new () => Reconocedor) | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Reconocedor) | null;
}

export const hayDictado = (): boolean => ctorReconocedor() !== null;

export type Dictado = { texto: Promise<string>; terminar(): void; cancelar(): void };

/** Una frase dictada con el reconocimiento del navegador. `texto` resuelve con
 *  lo que se entendió ("" si nada) y rechaza si no hay permiso. */
export function dictado(): Dictado {
  const Ctor = ctorReconocedor();
  if (!Ctor) throw new Error("Este navegador no tiene reconocimiento de voz");
  const r = new Ctor();
  r.lang = "es-AR";
  r.interimResults = false;
  r.maxAlternatives = 1;
  r.continuous = false;
  let oido = "";
  let cancelado = false;
  const texto = new Promise<string>((resolve, reject) => {
    r.onresult = (e) => { oido = Array.from(e.results).map((x) => x[0].transcript).join(" ").trim(); };
    r.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        reject(new DOMException("Sin permiso de micrófono", "NotAllowedError"));
      }
    };
    r.onend = () => resolve(cancelado ? "" : oido);
    r.start();
    // Hay navegadores donde el servicio no contesta nunca: no quedarse escuchando.
    window.setTimeout(() => { try { r.abort(); } catch { /* ya terminó */ } resolve(oido); }, 12000);
  });
  return { texto, terminar: () => r.stop(), cancelar: () => { cancelado = true; r.abort(); } };
}
