import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { obtener } from "../api/cliente";
import { hace } from "../lib/formato";
import { recomendar, sustrato, type Sensores } from "../lib/recomendaciones";
import type { Clase, Medicion } from "../tipos";

/** Qué hacer: el estado de la foto cruzado con los sensores de la maceta. */

const ICONO = { accion: "!", atencion: "i", ok: "✓" } as const;
const SUSTRATO = { seco: "seco", intermedio: "intermedio", humedo: "húmedo" } as const;

// A 30 s por muestra, 800 filas son ~6,5 h: alcanza para el máximo de luz.
const RECIENTES = 800;
const SEIS_HORAS = 6 * 3600e3;

export function Recomendaciones({ estado, fotoDeAhora, setFotoDeAhora }: {
  estado: Clase;
  fotoDeAhora: boolean;
  setFotoDeAhora: (v: boolean) => void;
}) {
  const { data, isPending } = useQuery({
    queryKey: ["mediciones-recientes"],
    queryFn: () => obtener<Medicion[]>(`/mediciones?limit=${RECIENTES}`),
  });

  const { sensores, ultima } = useMemo(() => {
    if (!data?.length) return { sensores: null, ultima: null };
    const u = data[0];                        // /mediciones viene del más nuevo al más viejo
    const t0 = new Date(u.ts_servidor).getTime();
    const ultimo = <K extends keyof Medicion>(k: K) =>
      (data.find((m) => m[k] !== null)?.[k] ?? null) as Medicion[K] | null;
    // La sonda saturada (fuera del sustrato) no es una lectura: se usa la anterior.
    const suelo = data.find((m) => m.suelo_mv !== null && !(m.errores ?? []).includes("suelo_saturado"));
    const luces = data
      .filter((m) => t0 - new Date(m.ts_servidor).getTime() <= SEIS_HORAS && m.luz_mv !== null)
      .map((m) => m.luz_mv as number);
    const s: Sensores = {
      suelo_mv: suelo?.suelo_mv ?? null,
      temp_c: ultimo("temperatura_c"),
      hum_pct: ultimo("humedad_ambiente_pct"),
      luz_mv: u.luz_mv,
      luz_max_6h: luces.length ? Math.max(...luces) : null,
      edad_ms: Date.now() - t0,
    };
    return { sensores: s, ultima: u };
  }, [data]);

  if (isPending) return null;
  const recs = recomendar(estado, sensores, fotoDeAhora);
  const suelo = sustrato(sensores?.suelo_mv ?? null);

  return (
    <section className="panel recos">
      <div className="recos__cab">
        <span className="lirio__et">Qué hacer</span>
        <label className="recos__ahora">
          <input type="checkbox" role="switch" checked={fotoDeAhora}
                 onChange={(e) => setFotoDeAhora(e.target.checked)} />
          <span>La foto es de ahora: cruzarla con los sensores</span>
        </label>
        {fotoDeAhora && ultima && sensores && (
          <div className="recos__sensores">
            <span>Sustrato <b>{sensores.suelo_mv !== null ? `${Math.round(sensores.suelo_mv)} mV` : "—"}</b>
              {suelo && <em> {SUSTRATO[suelo]}</em>}</span>
            <span>Luz <b>{sensores.luz_mv !== null ? `${Math.round(sensores.luz_mv)} mV` : "—"}</b>
              {sensores.luz_max_6h !== null && <em> máx. 6 h {Math.round(sensores.luz_max_6h)}</em>}</span>
            <span>Aire <b>{sensores.temp_c ?? "—"} °C</b> · <b>{sensores.hum_pct ?? "—"} %</b></span>
            <span className="recos__edad">{hace(ultima.ts_servidor)}</span>
          </div>
        )}
      </div>
      <ul className="recos__lista">
        {recs.map((r) => (
          <li key={r.titulo} className={`recos__item recos--${r.nivel}`}>
            <span className="recos__icono" aria-hidden="true">{ICONO[r.nivel]}</span>
            <div>
              <strong>{r.titulo}</strong>
              <p>{r.detalle}</p>
              <span className="recos__porque">Por qué: {r.porque}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
