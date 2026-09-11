import { useQuery } from "@tanstack/react-query";
import { obtener } from "./api/cliente";
import type { Medicion } from "./tipos";

/** Cuánto tiempo sin datos antes de considerar que la placa se cayó.
 *  Tres intervalos de envío de 5 min, más margen. */
const LIMITE_OFFLINE_MS = 16 * 60 * 1000;

function hace(iso: string | null): string {
  if (!iso) return "—";
  const minutos = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutos < 1) return "recién";
  if (minutos < 60) return `hace ${minutos} min`;
  return `hace ${Math.floor(minutos / 60)} h ${minutos % 60} min`;
}

function Dato({ etiqueta, valor, unidad, crudo }: {
  etiqueta: string; valor: number | null; unidad: string; crudo?: number | null;
}) {
  return (
    <div className="dato">
      <span className="dato__etiqueta">{etiqueta}</span>
      <span className="dato__valor">
        {valor === null ? <em className="vacio">sin dato</em> : <>{valor}<small>{unidad}</small></>}
      </span>
      {crudo != null && <span className="dato__crudo">raw {crudo}</span>}
    </div>
  );
}

export function App() {
  const { data, isPending, error } = useQuery({
    queryKey: ["ultima"],
    queryFn: () => obtener<Medicion>("/mediciones/ultima"),
  });

  const offline = data?.ts_servidor
    ? Date.now() - new Date(data.ts_servidor).getTime() > LIMITE_OFFLINE_MS
    : false;

  return (
    <main className="pagina">
      <header className="cabecera">
        <h1>PlantaIa</h1>
        <p className="subtitulo">Lirio de paz · maceta-01</p>
      </header>

      {isPending && <p className="aviso">Cargando…</p>}
      {error && <p className="aviso aviso--error">{(error as Error).message}</p>}

      {data && (
        <>
          <section className={`estado ${offline ? "estado--offline" : ""}`}>
            <span className="estado__punto" aria-hidden="true" />
            <div>
              <strong>{offline ? "Placa sin reportar" : "Placa en línea"}</strong>
              <p>
                Última muestra #{data.numero_muestra} · {hace(data.ts_servidor)}
                {data.ts_dispositivo === null && (
                  <> · <span className="alerta">reloj de la placa sin sincronizar</span></>
                )}
              </p>
            </div>
          </section>

          <section className="grilla">
            <Dato etiqueta="Suelo"      valor={data.suelo_pct}           unidad="%"  crudo={data.suelo_raw} />
            <Dato etiqueta="Luz"        valor={data.luz_pct}             unidad="%"  crudo={data.luz_raw} />
            <Dato etiqueta="Temp aire"  valor={data.temperatura_c}       unidad="°C" />
            <Dato etiqueta="Humedad"    valor={data.humedad_ambiente_pct} unidad="%" />
            <Dato etiqueta="Temp NTC"   valor={data.temp_ntc_c}          unidad="°C" crudo={data.termistor_raw} />
            <Dato etiqueta="RSSI"       valor={data.wifi_rssi}           unidad="dBm" />
          </section>

          <section className="etiqueta-actual">
            <span className="dato__etiqueta">Etiqueta</span>
            <strong>{data.condicion_etiqueta ?? "—"}</strong>
            {data.etiqueta_origen && <span className="pill">{data.etiqueta_origen}</span>}
          </section>

          {data.errores && data.errores.length > 0 && (
            <section className="errores">
              <span className="dato__etiqueta">Errores reportados</span>
              <ul>{data.errores.map((e) => <li key={e}>{e}</li>)}</ul>
            </section>
          )}

          <footer className="pie">
            fw {data.firmware_version ?? "?"} · boot {data.boot_id ?? "?"}
          </footer>
        </>
      )}
    </main>
  );
}
