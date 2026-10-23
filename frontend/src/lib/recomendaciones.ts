import type { Clase } from "../tipos";

/** Qué hacer con la planta: cruza el estado que dio la foto con la última
 *  lectura de los sensores. Son reglas a la vista, no un modelo: cada umbral
 *  sale de lo medido en maceta-01 (data/README.md) y cada recomendación dice
 *  qué dato la disparó. */

// Sonda resistiva: más mV = más seco. Octubre: recién regado ~1400–1500 mV,
// saludable ~1450–1600, marchita ~1940–1960, lo más seco ~1980; el árbol de la
// placa (modelo_placa.json) corta en 1716,5 y 1936,5. La escala se corre con
// la corrosión (CALIBRACION.md).
export const SUELO_SECO_MV = 1800;
export const SUELO_HUMEDO_MV = 1550;
// LDR: lámpara ~1780 mV, sol directo de septiembre hasta ~2900.
export const LUZ_FUERTE_MV = 2300;
// La única marchita fría fue el ep. 1 (~8,5 °C); el radiador del 15–16/09
// llevó la maceta a 28–36 °C.
export const TEMP_FRIO_C = 12;
export const TEMP_CALOR_C = 28;
export const HR_SECA_PCT = 35;
export const VPD_ALTO_KPA = 2;
// Sensores más viejos que esto no describen la planta de la foto.
export const SENSORES_VIEJOS_MS = 60 * 60e3;

export interface Sensores {
  suelo_mv: number | null;
  temp_c: number | null;
  hum_pct: number | null;
  luz_mv: number | null;
  /** Máximo de luz de las últimas 6 h: de noche la lectura actual no dice si
   *  la planta pasó la tarde al sol. */
  luz_max_6h: number | null;
  edad_ms: number | null;
}

export type Nivel = "accion" | "atencion" | "ok";
export interface Recomendacion { nivel: Nivel; titulo: string; detalle: string; porque: string }

export type Sustrato = "seco" | "intermedio" | "humedo" | null;
export const sustrato = (mv: number | null): Sustrato =>
  mv === null ? null : mv >= SUELO_SECO_MV ? "seco" : mv <= SUELO_HUMEDO_MV ? "humedo" : "intermedio";

export function vpd(t: number | null, hr: number | null): number | null {
  if (t === null || hr === null) return null;
  return 0.6108 * Math.exp((17.27 * t) / (t + 237.3)) * (1 - hr / 100);
}

const fmt = (v: number, d = 0) => v.toLocaleString("es-UY", { maximumFractionDigits: d });

/** `s = null` cuando la foto no es de ahora: cruzarla con los sensores de hoy
 *  sería recomendar sobre una planta que ya no está así. */
export function recomendar(estado: Clase, s: Sensores | null, fotoDeAhora: boolean): Recomendacion[] {
  const recs: Recomendacion[] = [];
  const sinSensores = !fotoDeAhora || !s || s.edad_ms === null || s.edad_ms > SENSORES_VIEJOS_MS;
  const caida = estado !== "saludable";
  const motivo = !fotoDeAhora
    ? "la foto no está marcada como de ahora, así que no se cruza con los sensores"
    : "los sensores no reportan hace más de una hora";

  if (sinSensores) {
    recs.push(caida
      ? { nivel: "accion", titulo: "Tocá el sustrato antes de decidir",
          detalle: "Si está seco a 2–3 cm, regá hasta que drene por abajo. Si está húmedo, no riegues: corré la maceta "
            + "a un lugar con luz indirecta y lejos de fuentes de calor.",
          porque: `La foto muestra la planta caída; ${motivo}.` }
      : { nivel: "ok", titulo: "No hace falta hacer nada",
          detalle: "La planta se ve turgente.",
          porque: `Sólo la foto: ${motivo}.` });
    return recs;
  }

  const suelo = sustrato(s.suelo_mv);
  const luzFuerte = s.luz_max_6h !== null && s.luz_max_6h >= LUZ_FUERTE_MV;
  const frio = s.temp_c !== null && s.temp_c <= TEMP_FRIO_C;
  const v = vpd(s.temp_c, s.hum_pct);
  const calor = (s.temp_c !== null && s.temp_c >= TEMP_CALOR_C) || (v !== null && v >= VPD_ALTO_KPA);
  const sueloTxt = s.suelo_mv !== null ? `${fmt(s.suelo_mv)} mV` : "";

  if (caida) {
    if (frio) {
      recs.push({ nivel: "accion", titulo: "Llevala a un lugar más templado",
        detalle: "Por debajo de ~12 °C el lirio de paz se marchita aunque tenga agua. No la riegues hasta que se "
          + "recupere: con frío el sustrato tarda en secarse y las raíces se pudren.",
        porque: `La foto la muestra caída y el aire está a ${fmt(s.temp_c!, 1)} °C.` });
    }
    if (suelo === "seco") {
      recs.push({ nivel: "accion", titulo: "Regala",
        detalle: "Riego abundante hasta que salga agua por abajo, y tirá lo que quede en el plato. Las hojas "
          + "deberían levantarse en 2 a 6 horas.",
        porque: `La foto la muestra caída y la sonda marca el sustrato seco (${sueloTxt}).` });
    }
    if (suelo !== "seco" && luzFuerte) {
      recs.push({ nivel: "accion", titulo: "Correla a un lugar más cubierto",
        detalle: "Luz indirecta: a un par de metros de la ventana o detrás de una cortina. Con sol directo "
          + "transpira más de lo que las raíces alcanzan a absorber, aunque tenga agua.",
        porque: `Está caída con el sustrato ${suelo === "humedo" ? "húmedo" : "todavía con agua"} (${sueloTxt}) `
          + `y en las últimas 6 h la luz llegó a ${fmt(s.luz_max_6h!)} mV (sol directo).` });
    }
    if (calor) {
      recs.push({ nivel: "accion", titulo: "Alejala del calor",
        detalle: "Lejos de radiadores, estufas y aire caliente. Si el aire está seco, pulverizá las hojas o poné "
          + "la maceta sobre un plato con piedras y agua.",
        porque: `Temperatura ${s.temp_c !== null ? `${fmt(s.temp_c, 1)} °C` : "—"}`
          + `${v !== null ? `, déficit de presión de vapor ${fmt(v, 1)} kPa` : ""}: el aire le saca agua rápido.` });
    }
    if (suelo === "humedo" && !luzFuerte && !calor && !frio) {
      recs.push({ nivel: "atencion", titulo: "No la riegues: el sustrato está húmedo",
        detalle: "Con el sustrato mojado y sin calor ni sol fuerte, el decaimiento puede venir del exceso de agua. "
          + "Fijate que la maceta drene y que no quede agua en el plato; si sigue así, revisá las raíces.",
        porque: `La foto la muestra caída pero la sonda marca húmedo (${sueloTxt}).` });
    }
    if (recs.length === 0) {
      recs.push({ nivel: "atencion", titulo: "Revisala en unas horas",
        detalle: "Ningún sensor explica el decaimiento. Puede ser un cambio reciente (riego, traslado); "
          + "volvé a sacarle una foto más tarde.",
        porque: `Sustrato ${suelo ?? "sin dato"}, sin sol fuerte, frío ni calor.` });
    }
  } else {
    if (suelo === "seco") {
      recs.push({ nivel: "atencion", titulo: "Va a necesitar riego pronto",
        detalle: "Todavía está turgente, pero el sustrato ya está seco: regala hoy o mañana.",
        porque: `La sonda marca ${sueloTxt}.` });
    }
    if (luzFuerte) {
      recs.push({ nivel: "atencion", titulo: "Vigilá el sol directo",
        detalle: "Por ahora lo aguanta; si las hojas se ponen amarillas o con bordes secos, correla.",
        porque: `En las últimas 6 h la luz llegó a ${fmt(s.luz_max_6h!)} mV.` });
    }
    if (recs.length === 0) {
      recs.push({ nivel: "ok", titulo: "No hace falta hacer nada",
        detalle: "Turgente, con el sustrato en rango y sin sol directo, frío ni calor.",
        porque: `Sustrato ${sueloTxt || "sin dato"}${s.temp_c !== null ? `, ${fmt(s.temp_c, 1)} °C` : ""}.` });
    }
  }

  if (s.hum_pct !== null && s.hum_pct < HR_SECA_PCT && !calor) {
    recs.push({ nivel: "atencion", titulo: "El aire está seco",
      detalle: "El lirio de paz prefiere humedad alta: pulverizá las hojas o agrupala con otras plantas.",
      porque: `Humedad del aire ${fmt(s.hum_pct)} %.` });
  }
  return recs;
}
