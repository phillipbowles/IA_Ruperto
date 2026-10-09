const TZ = "America/Argentina/Buenos_Aires";

export const hora = (t: number) =>
  new Date(t).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const fechaHora = (t: number) =>
  new Date(t).toLocaleString("es-AR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: TZ,
  });

export const fechaCorta = (t: number) =>
  new Date(t).toLocaleDateString("es-AR", { day: "2-digit", month: "short", timeZone: TZ });

/** Duración legible: "13 h 7 min", "45 min", "12 d 3 h". */
export function duracion(ms: number): string {
  const min = Math.round(ms / 60000);
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return min % 60 ? `${h} h ${min % 60} min` : `${h} h`;
  const d = Math.floor(h / 24);
  return h % 24 ? `${d} d ${h % 24} h` : `${d} d`;
}

export const hace = (iso: string) => {
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "recién";
  if (min < 60) return `hace ${min} min`;
  return `hace ${duracion(min * 60000)}`;
};

/** Celda vacía cuando el sensor falló: nunca un 0, que se lee como medición. */
export const num = (v: number | null | undefined, dec = 1) =>
  v === null || v === undefined ? null : v.toFixed(dec);

/** Intervalo entre muestras: "30 s", "5 min". */
export const cadencia = (s: number) =>
  s < 90 ? `${s} s` : `${Math.round(s / 60)} min`;
