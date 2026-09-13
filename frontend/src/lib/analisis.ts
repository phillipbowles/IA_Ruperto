import type { Medicion } from "../tipos";

/** Un hueco mayor a esto corta la serie: la placa dejó de reportar. */
const HUECO_MS = 5 * 60 * 1000;
/** Sin datos por más de esto, la placa se considera caída. */
export const LIMITE_OFFLINE_MS = 16 * 60 * 1000;

export interface Punto extends Medicion {
  t: number;            // epoch ms, para el eje
  hora: number;         // hora local 0-23
  suelo_pct_calc: number | null;
}

/** Calibración de la sonda resistiva (ver docs/CALIBRACION.md). Recalculamos
 *  suelo_pct acá porque el firmware dejó de mandarlo a partir del boot 20 y el
 *  96 % de las filas lo tiene vacío — pero suelo_mv está completo. */
const SUELO_MV_MOJADO = 1000;
const SUELO_MV_SECO = 2800;

function suelo_pct(mv: number | null): number | null {
  if (mv === null) return null;
  const p = ((SUELO_MV_SECO - mv) / (SUELO_MV_SECO - SUELO_MV_MOJADO)) * 100;
  return Math.max(0, Math.min(100, Math.round(p)));
}

export function prepararSerie(filas: Medicion[]): Punto[] {
  return filas
    .map((m) => {
      const d = new Date(m.ts_dispositivo ?? m.ts_servidor);
      return {
        ...m,
        t: d.getTime(),
        hora: d.getHours(),
        suelo_pct_calc: suelo_pct(m.suelo_mv),
      };
    })
    .sort((a, b) => a.t - b.t);
}

export interface Tramo { desde: number; hasta: number; n: number }

/** Corta la serie en tramos continuos. Sin esto, la línea une con una recta los
 *  dos lados de un hueco de 22 h y aparenta datos que no existen. */
export function tramos(puntos: Punto[]): Tramo[] {
  const out: Tramo[] = [];
  let ini = 0;
  for (let i = 1; i <= puntos.length; i++) {
    if (i === puntos.length || puntos[i].t - puntos[i - 1].t > HUECO_MS) {
      out.push({ desde: puntos[ini].t, hasta: puntos[i - 1].t, n: i - ini });
      ini = i;
    }
  }
  return out;
}

/** Bandas de noche, para sombrear los gráficos. Se derivan de la luz medida, no
 *  del reloj: el umbral sale del propio histograma bimodal del LDR. */
export function bandasNoche(puntos: Punto[], umbralMv = 600): Tramo[] {
  const out: Tramo[] = [];
  let ini: number | null = null;
  for (const p of puntos) {
    const oscuro = p.luz_mv !== null && p.luz_mv < umbralMv;
    if (oscuro && ini === null) ini = p.t;
    if (!oscuro && ini !== null) { out.push({ desde: ini, hasta: p.t, n: 0 }); ini = null; }
  }
  if (ini !== null) out.push({ desde: ini, hasta: puntos[puntos.length - 1].t, n: 0 });
  return out.filter((b) => b.hasta - b.desde > 20 * 60 * 1000);
}

export interface Resumen {
  total: number;
  desde: number;
  hasta: number;
  /** Tiempo efectivamente registrado: suma de los tramos continuos. Para un
   *  logger con huecos es la medida honesta — hasta-desde cuenta como "periodo"
   *  las horas en las que no hubo ni una muestra. */
  spanMs: number;
  intervaloMedianoS: number;
  boots: number;
  tramos: Tramo[];
  sinEtiquetar: number;
  pctSinEtiquetar: number;
  errores: { nombre: string; n: number }[];
  faltantes: { campo: string; pct: number }[];
  ntcSospechoso: boolean;
  correlacionNtcDht: number | null;
  ultima: Punto | null;
  offline: boolean;
}

function mediana(xs: number[]): number {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

function correlacion(a: number[], b: number[]): number | null {
  const n = a.length;
  if (n < 3) return null;
  const ma = a.reduce((s, x) => s + x, 0) / n;
  const mb = b.reduce((s, x) => s + x, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    num += (a[i] - ma) * (b[i] - mb);
    da += (a[i] - ma) ** 2;
    db += (b[i] - mb) ** 2;
  }
  return da && db ? num / Math.sqrt(da * db) : null;
}

export function resumir(puntos: Punto[]): Resumen {
  const total = puntos.length;
  const vacio: Resumen = {
    total: 0, desde: 0, hasta: 0, spanMs: 0, intervaloMedianoS: 0, boots: 0,
    tramos: [], sinEtiquetar: 0, pctSinEtiquetar: 0, errores: [], faltantes: [],
    ntcSospechoso: false, correlacionNtcDht: null, ultima: null, offline: false,
  };
  if (!total) return vacio;

  const difs: number[] = [];
  for (let i = 1; i < total; i++) difs.push((puntos[i].t - puntos[i - 1].t) / 1000);

  const cuenta = new Map<string, number>();
  for (const p of puntos)
    for (const e of p.errores ?? []) cuenta.set(e, (cuenta.get(e) ?? 0) + 1);

  const campos: (keyof Medicion)[] = [
    "temperatura_c", "humedad_ambiente_pct", "luz_mv", "suelo_mv", "temp_ntc_c", "ts_dispositivo",
  ];
  const faltantes = campos
    .map((c) => ({
      campo: String(c),
      pct: (puntos.filter((p) => p[c] === null || p[c] === undefined).length / total) * 100,
    }))
    .filter((f) => f.pct > 0)
    .sort((a, b) => b.pct - a.pct);

  const pares = puntos.filter((p) => p.temp_ntc_c !== null && p.temperatura_c !== null);
  const corr = correlacion(
    pares.map((p) => p.temp_ntc_c as number),
    pares.map((p) => p.temperatura_c as number),
  );

  const sinEtiquetar = puntos.filter(
    (p) => !p.condicion_etiqueta || p.condicion_etiqueta === "sin_etiquetar",
  ).length;

  const tr = tramos(puntos);
  const ultima = puntos[total - 1];
  return {
    total,
    desde: puntos[0].t,
    hasta: ultima.t,
    spanMs: tr.reduce((s, x) => s + (x.hasta - x.desde), 0),
    intervaloMedianoS: Math.round(mediana(difs)),
    boots: new Set(puntos.map((p) => p.boot_id)).size,
    tramos: tr,
    sinEtiquetar,
    pctSinEtiquetar: (sinEtiquetar / total) * 100,
    errores: [...cuenta.entries()]
      .map(([nombre, n]) => ({ nombre, n }))
      .sort((a, b) => b.n - a.n),
    faltantes,
    // Un termistor sano correlaciona POSITIVO con el DHT: los dos miden la misma
    // habitación. Negativo significa divisor invertido en la fórmula.
    ntcSospechoso: corr !== null && corr < 0,
    correlacionNtcDht: corr,
    ultima,
    offline: Date.now() - new Date(ultima.ts_servidor).getTime() > LIMITE_OFFLINE_MS,
  };
}

export function porHora(puntos: Punto[]): { hora: string; n: number }[] {
  const c = new Array(24).fill(0);
  for (const p of puntos) c[p.hora]++;
  return c.map((n, h) => ({ hora: String(h).padStart(2, "0"), n }));
}
