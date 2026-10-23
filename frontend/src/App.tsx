import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { obtener } from "./api/cliente";
import type { Medicion } from "./tipos";
import { prepararSerie, resumir, bandasNoche, porHora } from "./lib/analisis";
import { cadencia, duracion, fechaCorta, hace, num } from "./lib/formato";
import { Panel, Kpi } from "./componentes/Panel";
import { GraficoSerie } from "./componentes/GraficoSerie";
import { BarrasPorHora } from "./componentes/BarrasPorHora";
import { DonutErrores } from "./componentes/DonutErrores";
import { DonutEtiquetas } from "./componentes/DonutEtiquetas";
import { DispersionTemp } from "./componentes/DispersionTemp";
import { TablaRegistros } from "./componentes/TablaRegistros";
import { AvatarLirio } from "./componentes/AvatarLirio";
import { AnalisisFoto } from "./componentes/AnalisisFoto";
import { ArbolModelo } from "./componentes/ArbolModelo";
import { featuresActuales } from "./lib/modeloPlaca";

const RANGOS = [
  { id: "24h", texto: "24 h", ms: 24 * 3600e3 },
  { id: "7d", texto: "7 días", ms: 7 * 24 * 3600e3 },
  { id: "todo", texto: "Todo", ms: Infinity },
] as const;

const VISTAS = [
  { id: "panel", texto: "Panel de sensores" },
  { id: "foto", texto: "Analizar foto" },
] as const;
type Vista = (typeof VISTAS)[number]["id"];

// La vista vive en el hash (#foto) para que se pueda compartir el link y el
// botón «atrás» del navegador vuelva al panel. nginx ni se entera.
const vistaDelHash = (): Vista =>
  VISTAS.find((v) => v.id !== "panel" && location.hash === `#${v.id}`)?.id ?? "panel";

export function App() {
  const [vista, setVista] = useState<Vista>(vistaDelHash);

  useEffect(() => {
    const alCambiar = () => setVista(vistaDelHash());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);

  return (
    <main className="pagina">
      <nav className="filtros pestanas" aria-label="Secciones">
        {VISTAS.map((v) => (
          <button key={v.id} aria-pressed={vista === v.id}
                  onClick={() => { location.hash = v.id === "panel" ? "" : v.id; }}>
            {v.texto}
          </button>
        ))}
      </nav>
      {vista === "foto" ? <VistaFoto /> : <Tablero />}
    </main>
  );
}

function VistaFoto() {
  return (
    <>
      <header className="cabecera">
        <div>
          <h1>PlantaIa</h1>
          <p className="sub">Lirio de paz · diagnóstico a partir de una foto</p>
        </div>
      </header>
      <AnalisisFoto />
    </>
  );
}

function Tablero() {
  const [rango, setRango] = useState<string>("24h");

  const { data, isPending, error } = useQuery({
    queryKey: ["mediciones"],
    // Traemos la serie completa y agregamos en el cliente. Cuando el dataset
    // pase de unos pocos miles de filas, esto se mueve a un endpoint que
    // devuelva la serie ya agregada por ventana (ver docs/ARQUITECTURA.md §6).
    queryFn: () => obtener<Medicion[]>("/mediciones?limit=50000"),
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

  if (isPending) return <p className="cargando">Cargando mediciones…</p>;
  if (error) return <p className="error">{(error as Error).message}</p>;
  if (!res.total) return <p className="cargando">Todavía no hay mediciones.</p>;

  const u = res.ultima!;
  // Lo que mira el árbol de la placa, armado como lo arma la placa.
  const valoresArbol = featuresActuales(todos);
  const avisos = [
    res.ntcSospechoso && {
      nivel: "malo",
      chip: "termistor",
      texto: `El NTC correlaciona ${res.correlacionNtcDht?.toFixed(2)} con el DHT11. Los dos miden la misma habitación, así que debería ser positivo: la fórmula del divisor está invertida o el sensor está mal cableado.`,
    },
    res.tramos.length > 1 && {
      nivel: "alerta",
      chip: `${res.tramos.length} tramos`,
      texto: `La serie tiene ${res.tramos.length - 1} hueco${res.tramos.length > 2 ? "s" : ""} de más de 15 minutos (3 envíos seguidos sin llegar). Sin buffer en la placa, lo que pasa durante un corte de WiFi no se recupera.`,
    },
    res.intervaloMedianoS < 240 && {
      nivel: "alerta",
      chip: `cada ${res.intervaloMedianoS} s`,
      texto: `El protocolo pide una muestra cada 5 min y estos datos llegan cada ${res.intervaloMedianoS} s: la placa sigue con un firmware con INTERVALO_ENVIO más corto. Hay que volver a flashearla; mientras tanto los gráficos se promedian en ventanas de 5 min.`,
    },
    res.pctSinEtiquetar > 50 && {
      nivel: "alerta",
      chip: `${res.pctSinEtiquetar.toFixed(0)} % sin etiquetar`,
      texto: "El clasificador entrena solo con filas etiquetadas. El botón de la maceta es lo que las genera.",
    },
  ].filter(Boolean) as { nivel: string; chip: string; texto: string }[];

  return (
    <>
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

      {u.prediccion_etiqueta && u.modelo_version ? (
        <AvatarLirio
          estado={u.prediccion_etiqueta}
          fuente={{ tipo: "modelo", version: u.modelo_version, proba: u.prediccion_proba }}
          ts={u.ts_servidor}
        />
      ) : (
        <AvatarLirio
          estado={u.condicion_etiqueta === "sin_etiquetar" ? null : u.condicion_etiqueta}
          fuente={{ tipo: "boton", origen: u.etiqueta_origen }}
          ts={u.ts_servidor}
        />
      )}

      <div className="kpis">
        <Kpi etiqueta="Muestras" valor={res.total.toLocaleString("es-AR")}
             pie={`cada ${cadencia(res.intervaloMedianoS)}`} />
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

      <section className="seccion">
        <h2>Cómo decide el modelo de la placa</h2>
        <div className="panel">
          <p className="panel__nota">
            El árbol de decisión que corre en la ESP32. El punto recorre el camino que sigue la medición actual hasta
            la hoja que prende el LED.
          </p>
          <ArbolModelo valores={valoresArbol}
                       prediccion={u.prediccion_etiqueta} modeloVersion={u.modelo_version} />
        </div>
      </section>

      <footer className="pie-pagina">
        fw {u.firmware_version ?? "?"} · boot {u.boot_id ?? "?"} · muestra {u.numero_muestra} ·{" "}
        <a href="/api/v1/mediciones.csv">descargar CSV</a>
      </footer>
    </>
  );
}
