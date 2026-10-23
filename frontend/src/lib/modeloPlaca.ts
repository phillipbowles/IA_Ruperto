import type { Clase } from "../tipos";
import modelo from "../modelo_placa.json";

/** El árbol que corre en la placa, para dibujarlo en el panel.
 *
 *  Sale de `modelo_placa.json`, que GENERA ml/plantaia_ml/exportar_c.py junto
 *  con firmware/lib/plantaia_ml/modelo_plantaia.h: si se reentrena el modelo,
 *  el dibujo se actualiza solo. El panel avisa cuando la placa reporta otra
 *  `modelo_version` (la placa tiene flasheado otro modelo). */

export interface NodoPregunta { feature: string; umbral: number; si: number; no: number }
export interface NodoHoja { clase: Clase; proba: [number, number, number] }
export type Nodo = NodoPregunta | NodoHoja;

export const VERSION_ARBOL: string = modelo.version;
export const PROFUNDIDAD: number | null = modelo.profundidad;
export const FLASH_B: number = modelo.flash_B;
/** null si el modelo vigente no es un árbol. */
export const NODOS = modelo.nodos as Nodo[] | null;

export const esHoja = (n: Nodo): n is NodoHoja => "clase" in n;

/** Cómo se lee cada feature del contrato (docs/ENTREGA2.md §4) en el panel. */
export const FEATURE: Record<string, { texto: string; unidad: string; decimales: number }> = {
  suelo_mv: { texto: "sonda", unidad: "mV", decimales: 0 },
  suelo_delta_1h: { texto: "cambio del suelo en 1 h", unidad: "mV", decimales: 0 },
  temp_c: { texto: "temp. del aire", unidad: "°C", decimales: 1 },
  hum_aire_pct: { texto: "HR del aire", unidad: "%", decimales: 0 },
  vpd_kpa: { texto: "VPD", unidad: "kPa", decimales: 2 },
  luz_mv: { texto: "luz", unidad: "mV", decimales: 0 },
  luz_media_1h: { texto: "luz media 1 h", unidad: "mV", decimales: 0 },
  h_desde_riego: { texto: "h desde el riego", unidad: "h", decimales: 1 },
};

/** Ids de nodos desde la raíz hasta la hoja; null si falta un dato que el árbol mira. */
export function recorrido(valores: Record<string, number | null>): number[] | null {
  if (!NODOS) return null;
  const camino = [0];
  let n = NODOS[0];
  while (!esHoja(n)) {
    const v = valores[n.feature];
    if (v === null || v === undefined) return null;
    const sig = v <= n.umbral ? n.si : n.no;
    camino.push(sig);
    n = NODOS[sig];
  }
  return camino;
}

interface PuntoSensor {
  t: number;
  boot_id: number | null;
  suelo_mv: number | null;
  temperatura_c: number | null;
  humedad_ambiente_pct: number | null;
  luz_mv: number | null;
  errores: string[] | null;
}

const HORA_MS = 60 * 60e3;
// Mismos parámetros que la placa (features.h).
const RIEGO_CAIDA_MV = 250;
const RIEGO_TOPE_H = 96;

/** Las 8 features como las arma la placa con la serie que llegó a la base:
 *  último DHT11 válido, última sonda no saturada (con la sonda fuera del
 *  sustrato la placa repite la anterior), las ventanas de 1 h y las horas
 *  desde el último riego. */
export function featuresActuales(serie: PuntoSensor[]): Record<string, number | null> {
  const ultimo = <T,>(f: (p: PuntoSensor) => T | null): { v: T; t: number } | null => {
    for (let i = serie.length - 1; i >= 0; i--) {
      const v = f(serie[i]);
      if (v !== null) return { v, t: serie[i].t };
    }
    return null;
  };
  const sueloValido = (p: PuntoSensor) =>
    (p.errores ?? []).includes("suelo_saturado") ? null : p.suelo_mv;
  const suelo = ultimo(sueloValido);
  const temp = ultimo((p) => p.temperatura_c)?.v ?? null;
  const hum = ultimo((p) => p.humedad_ambiente_pct)?.v ?? null;
  const luz = ultimo((p) => p.luz_mv);

  let delta: number | null = null;
  if (suelo) {
    // La lectura más cercana a 1 h antes (dentro de 7,5 min); sin historia, 0 como en la placa.
    const antes = serie.filter((p) => sueloValido(p) !== null && Math.abs(p.t - (suelo.t - HORA_MS)) <= 7.5 * 60e3);
    delta = antes.length ? suelo.v - sueloValido(antes[antes.length - 1])! : 0;
  }
  let luzMedia: number | null = null;
  if (luz) {
    const ventana = serie.filter((p) => p.luz_mv !== null && p.t > luz.t - HORA_MS && p.t <= luz.t);
    luzMedia = ventana.reduce((s, p) => s + p.luz_mv!, 0) / ventana.length;
  }
  // Riego: la sonda cae ≥ 250 mV entre dos lecturas válidas seguidas, pasada la
  // primera hora del arranque (la placa no lo cuenta en warm-up). El riego
  // sobrevive a los reinicios, como en la placa (Preferences).
  let riegoT: number | null = null;
  let previa: number | null = null;
  let boot: number | null = null;
  let inicioBoot = 0;
  for (const p of serie) {
    if (p.boot_id !== boot) { boot = p.boot_id; inicioBoot = p.t; previa = null; }
    const v = sueloValido(p);
    if (v === null) continue;
    if (previa !== null && p.t - inicioBoot >= HORA_MS && previa - v >= RIEGO_CAIDA_MV) riegoT = p.t;
    previa = v;
  }
  const hRiego = riegoT !== null && suelo ? Math.min(RIEGO_TOPE_H, (suelo.t - riegoT) / HORA_MS) : RIEGO_TOPE_H;

  const vpd = temp !== null && hum !== null
    ? 0.6108 * Math.exp((17.27 * temp) / (temp + 237.3)) * (1 - hum / 100)
    : null;
  return {
    suelo_mv: suelo?.v ?? null, suelo_delta_1h: delta, temp_c: temp, hum_aire_pct: hum,
    vpd_kpa: vpd, luz_mv: luz?.v ?? null, luz_media_1h: luzMedia, h_desde_riego: hRiego,
  };
}
