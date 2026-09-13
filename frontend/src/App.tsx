import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { obtener } from "./api/cliente";
import type { Medicion } from "./tipos";
import { prepararSerie, resumir, bandasNoche, porHora } from "./lib/analisis";
import { duracion, fechaCorta, hace, num } from "./lib/formato";
import { Panel, Kpi } from "./componentes/Panel";
import { GraficoSerie } from "./componentes/GraficoSerie";
import { BarrasPorHora } from "./componentes/BarrasPorHora";
import { DonutErrores } from "./componentes/DonutErrores";
import { DonutEtiquetas } from "./componentes/DonutEtiquetas";
import { DispersionTemp } from "./componentes/DispersionTemp";
import { TablaRegistros } from "./componentes/TablaRegistros";

const RANGOS = [
  { id: "24h", texto: "24 h", ms: 24 * 3600e3 },
  { id: "7d", texto: "7 días", ms: 7 * 24 * 3600e3 },
  { id: "todo", texto: "Todo", ms: Infinity },
] as const;

export function App() {
  const [rango, setRango] = useState<string>("24h");

  const { data, isPending, error } = useQuery({
    queryKey: ["mediciones"],
    // Traemos la serie completa y agregamos en el cliente. Cuando el dataset
    // pase de unos pocos miles de filas, esto se mueve a un endpoint que
    // devuelva la serie ya agregada por ventana (ver docs/ARQUITECTURA.md §6).
    queryFn: () => obtener<Medicion[]>("/mediciones?limit=20000"),
  });

  const todos = useMemo(() => prepararSerie(data ?? []), [data]);

  const puntos = useMemo(() => {
    const r = RANGOS.find((x) => x.id === rango)!;
    if (!isFinite(r.ms) || !todos.length) return todos;
    const corte = todos[todos.length - 1].t - r.ms;
    return todos.filter((p) => p.t >= corte);
  }, [todos, rango]);

  const res = useMemo(() => resumir(puntos), [puntos]);
  const noche = useMemo(() => bandasNoche(puntos), [puntos]);
  const horas = useMemo(() => porHora(puntos), [puntos]);

  if (isPending) return <main className="pagina"><p className="cargando">Cargando mediciones…</p></main>;
  if (error) return <main className="pagina"><p className="error">{(error as Error).message}</p></main>;
  if (!res.total) return <main className="pagina"><p className="cargando">Todavía no hay mediciones.</p></main>;

  const u = res.ultima!;
  const avisos = [
    res.ntcSospechoso && {
      nivel: "malo",
      chip: "termistor",
      texto: `El NTC correlaciona ${res.correlacionNtcDht?.toFixed(2)} con el DHT11. Los dos miden la misma habitación, así que debería ser positivo: la fórmula del divisor está invertida o el sensor está mal cableado.`,
    },
    res.tramos.length > 1 && {
      nivel: "alerta",
      chip: `${res.tramos.length} tramos`,
      texto: `La serie tiene ${res.tramos.length - 1} hueco${res.tramos.length > 2 ? "s" : ""} de más de 5 minutos. Sin buffer en la placa, lo que pasa durante un corte de WiFi no se recupera.`,
    },
    res.pctSinEtiquetar > 50 && {
      nivel: "alerta",
      chip: `${res.pctSinEtiquetar.toFixed(0)} % sin etiquetar`,
      texto: "El clasificador entrena solo con filas etiquetadas. El botón de la maceta es lo que las genera.",
    },
  ].filter(Boolean) as { nivel: string; chip: string; texto: string }[];

  return (
    <main className="pagina">
      <header className="cabecera">
        <div>
          <h1>PlantaIa</h1>
          <p className="sub">
            Lirio de paz · {u.dispositivo} · {fechaCorta(res.desde)} – {fechaCorta(res.hasta)}
          </p>
        </div>
        <div className={`estado-placa${res.offline ? " estado-placa--off" : ""}`}>
          <span className={`punto${res.offline ? " punto--off" : ""}`} aria-hidden="true" />
          <span>
            {res.offline ? "Sin reportar" : "En línea"} · {hace(u.ts_servidor)}
            {u.ts_dispositivo === null && " · reloj sin sincronizar"}
          </span>
        </div>
      </header>

      <div className="kpis">
        <Kpi etiqueta="Muestras" valor={res.total.toLocaleString("es-AR")}
             pie={`cada ${res.intervaloMedianoS} s`} />
        <Kpi etiqueta="Período" valor={duracion(res.spanMs)}
             pie={`${res.tramos.length} tramo${res.tramos.length > 1 ? "s" : ""} continuo${res.tramos.length > 1 ? "s" : ""}`} />
        <Kpi etiqueta="Suelo" valor={num(u.suelo_pct_calc, 0) ?? "—"} unidad="%"
             pie={`${num(u.suelo_mv, 0) ?? "—"} mV crudos`} />
        <Kpi etiqueta="Temp. aire" valor={num(u.temperatura_c) ?? "—"} unidad="°C"
             pie={`HR ${num(u.humedad_ambiente_pct, 0) ?? "—"} %`} />
        <Kpi etiqueta="Reinicios" valor={res.boots} pie={`boot actual ${u.boot_id ?? "—"}`} />
        <Kpi etiqueta="Etiquetadas"
             valor={(res.total - res.sinEtiquetar).toLocaleString("es-AR")}
             pie={`${(100 - res.pctSinEtiquetar).toFixed(1)} % del total`}
             alerta={res.pctSinEtiquetar > 50} />
      </div>

      <section className="seccion">
        <div className="seccion__cab">
          <h2>Series temporales</h2>
          <div className="filtros">
            {RANGOS.map((r) => (
              <button key={r.id} aria-pressed={rango === r.id} onClick={() => setRango(r.id)}>
                {r.texto}
              </button>
            ))}
          </div>
        </div>
        <div className="grilla">
          <Panel titulo="Luz" valor={`${num(u.luz_mv, 0) ?? "—"} mV`}
                 nota="Las bandas sombreadas son la noche, derivadas de la propia lectura del LDR.">
            <GraficoSerie puntos={puntos} campo="luz_mv" color="var(--serie-1)" unidad="mV" noche={noche} />
          </Panel>
          <Panel titulo="Humedad de suelo" valor={`${num(u.suelo_pct_calc, 0) ?? "—"} %`}
                 nota="Recalculado desde suelo_mv con la calibración de docs/CALIBRACION.md.">
            <GraficoSerie puntos={puntos} campo="suelo_pct_calc" color="var(--serie-2)" unidad="%" noche={noche} dominio={[0, 100]} />
          </Panel>
          <Panel titulo="Temperatura del aire" valor={`${num(u.temperatura_c) ?? "—"} °C`}>
            <GraficoSerie puntos={puntos} campo="temperatura_c" color="var(--serie-2)" unidad="°C" noche={noche} />
          </Panel>
          <Panel titulo="Humedad del aire" valor={`${num(u.humedad_ambiente_pct, 0) ?? "—"} %`}>
            <GraficoSerie puntos={puntos} campo="humedad_ambiente_pct" color="var(--serie-3)" unidad="%" noche={noche} dominio={[0, 100]} />
          </Panel>
        </div>
      </section>

      <section className="seccion">
        <h2>Distribuciones</h2>
        <div className="grilla">
          <Panel titulo="Etiquetas" nota="Las 3 clases del clasificador. «Sin etiquetar» no es una clase: se excluye del entrenamiento.">
            <DonutEtiquetas puntos={puntos} />
          </Panel>
          <Panel titulo="Avisos de los sensores" nota="Qué reportó la placa en cada muestra.">
            <DonutErrores errores={res.errores} total={res.total} />
          </Panel>
          <Panel titulo="Cobertura por hora" nota="Muestras recibidas en cada hora del día. Los valles son huecos de captura.">
            <BarrasPorHora datos={horas} />
          </Panel>
          <Panel titulo="Los dos termómetros"
                 valor={res.correlacionNtcDht !== null ? `r = ${res.correlacionNtcDht.toFixed(2)}` : undefined}
                 nota="Miden la misma habitación: deberían caer sobre la diagonal.">
            <DispersionTemp puntos={puntos} />
          </Panel>
        </div>
      </section>

      {avisos.length > 0 && (
        <section className="seccion">
          <h2>Diagnóstico</h2>
          <div className="aviso">
            <ul>
              {avisos.map((a, i) => (
                <li key={i}>
                  <span className={`chip chip--${a.nivel}`}>{a.chip}</span>
                  <span>{a.texto}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <section className="seccion">
        <h2>Últimos registros</h2>
        <div className="panel">
          <TablaRegistros puntos={puntos} />
        </div>
      </section>

      <footer className="pie-pagina">
        fw {u.firmware_version ?? "?"} · boot {u.boot_id ?? "?"} · muestra {u.numero_muestra} ·{" "}
        <a href="/api/v1/mediciones.csv">descargar CSV</a>
      </footer>
    </main>
  );
}
