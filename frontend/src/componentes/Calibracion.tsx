import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ErrorApi } from "../api/cliente";
import type { Clase } from "../tipos";
import { achicar } from "./AnalisisFoto";

/** Pestaña «Calibrar»: fotos de la planta con lo que una persona observó, para
 *  medir la visión clásica y mejorarla sin ajustarla a la última foto
 *  (docs/VISION_CLASICA.md §5). Todo pide la clave de calibración: las fotos
 *  pueden mostrar la casa o personas reflejadas. */

const CLASES: Clase[] = ["saludable", "estresada", "marchita"];
const NOMBRE: Record<Clase, string> = { saludable: "Saludable", estresada: "Estresada", marchita: "Marchita" };
const CLAVE_STORAGE = "plantaia.calibracion.token";

// Mismos cortes que el backend (app/routers/analisis.py).
const estadoDe = (p: number | null): Clase | null =>
  p === null ? null : p >= 67 ? "saludable" : p >= 34 ? "estresada" : "marchita";

interface Calibracion {
  id: number;
  creada_en: string;
  etiqueta: Clase;
  puntaje_humano: number | null;
  nota: string | null;
  autor: string | null;
  vision_version: string | null;
  vision_puntaje: number | null;
  ia_modelo: string | null;
  ia_puntaje: number | null;
  imagen_url: string;
}

interface Evaluacion {
  version: string;
  n: number;
  aciertos: number;
  exactitud: number | null;
  error_medio: number | null;
  matriz: Record<Clase, Record<Clase, number>>;
  filas: { id: number; puntaje: number | null; estado: Clase | null; acierto: boolean }[];
}

function leerClave(): string {
  try { return localStorage.getItem(CLAVE_STORAGE) ?? ""; } catch { return ""; }
}
function guardarClave(v: string) {
  try { v ? localStorage.setItem(CLAVE_STORAGE, v) : localStorage.removeItem(CLAVE_STORAGE); } catch { /* sin storage */ }
}

async function pedir<T>(clave: string, ruta: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`/api/v1${ruta}`, {
    ...init,
    headers: { ...(init.headers ?? {}), "X-Calibracion-Token": clave, Accept: "application/json" },
  });
  if (!r.ok) {
    const cuerpo = await r.json().catch(() => null);
    throw new ErrorApi(r.status, cuerpo?.detail ?? `La API respondió ${r.status}`);
  }
  return (r.status === 204 ? null : await r.json()) as T;
}

/** La imagen también pide la clave, así que no alcanza con un <img src>. */
function Miniatura({ clave, url }: { clave: string; url: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let vivo = true;
    let objeto: string | null = null;
    fetch(url, { headers: { "X-Calibracion-Token": clave } })
      .then((r) => (r.ok ? r.blob() : null))
      .then((b) => { if (b && vivo) { objeto = URL.createObjectURL(b); setSrc(objeto); } })
      .catch(() => {});
    return () => { vivo = false; if (objeto) URL.revokeObjectURL(objeto); };
  }, [clave, url]);
  return src ? <img src={src} alt="Foto de calibración" /> : <span className="calib__sin-img" />;
}

function Pastilla({ estado, puntaje }: { estado: Clase | null; puntaje: number | null }) {
  if (!estado) return <span className="calib__pastilla">—</span>;
  return (
    <span className={`calib__pastilla lirio--${estado}`}>
      <span className="lirio__punto" aria-hidden="true" />
      {NOMBRE[estado]}{puntaje !== null ? ` · ${puntaje}` : ""}
    </span>
  );
}

export function Calibracion() {
  const [clave, setClave] = useState(leerClave);
  const [borrador, setBorrador] = useState("");

  if (!clave) {
    return (
      <section className="panel calib__clave">
        <h2>Clave de calibración</h2>
        <p className="lirio__detalle">
          Las fotos de calibración se guardan en el bucket y pueden mostrar la casa, así que esta sección pide la
          clave que está en <code>CALIBRACION_TOKEN</code> del backend. Se guarda sólo en este navegador.
        </p>
        <form onSubmit={(e) => { e.preventDefault(); guardarClave(borrador.trim()); setClave(borrador.trim()); }}>
          <input type="password" value={borrador} onChange={(e) => setBorrador(e.target.value)}
                 placeholder="Clave" autoComplete="current-password" aria-label="Clave de calibración" />
          <button type="submit" disabled={!borrador.trim()}>Entrar</button>
        </form>
      </section>
    );
  }
  return <ConClave clave={clave} salir={() => { guardarClave(""); setClave(""); }} />;
}

function ConClave({ clave, salir }: { clave: string; salir: () => void }) {
  const qc = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [vista, setVista] = useState<string | null>(null);
  const [etiqueta, setEtiqueta] = useState<Clase | null>(null);
  const [conPuntaje, setConPuntaje] = useState(false);
  const [puntaje, setPuntaje] = useState(50);
  const [nota, setNota] = useState("");
  const [conIa, setConIa] = useState(false);
  const [aBorrar, setABorrar] = useState<number | null>(null);

  const lista = useQuery({
    queryKey: ["calibracion", clave],
    queryFn: () => pedir<Calibracion[]>(clave, "/calibracion"),
    refetchInterval: false,
    retry: false,
  });
  const evaluacion = useMutation({ mutationFn: () => pedir<Evaluacion>(clave, "/calibracion/evaluacion") });
  const guardar = useMutation({
    mutationFn: async () => {
      const q = new URLSearchParams({ etiqueta: etiqueta!, con_ia: String(conIa) });
      if (conPuntaje) q.set("puntaje_humano", String(puntaje));
      if (nota.trim()) q.set("nota", nota.trim());
      const imagen = await achicar(archivo!);
      return pedir<Calibracion>(clave, `/calibracion?${q}`, {
        method: "POST", headers: { "Content-Type": imagen.type }, body: imagen,
      });
    },
    onSuccess: () => {
      setArchivo(null); setVista(null); setEtiqueta(null); setNota(""); setConPuntaje(false);
      qc.invalidateQueries({ queryKey: ["calibracion"] });
      evaluacion.reset();
    },
  });
  const borrar = useMutation({
    mutationFn: (id: number) => pedir<null>(clave, `/calibracion/${id}`, { method: "DELETE" }),
    onSuccess: () => { setABorrar(null); qc.invalidateQueries({ queryKey: ["calibracion"] }); evaluacion.reset(); },
  });

  useEffect(() => () => { if (vista) URL.revokeObjectURL(vista); }, [vista]);
  // Clave rechazada: volver al formulario de la clave.
  useEffect(() => { if ((lista.error as ErrorApi | null)?.estado === 401) salir(); }, [lista.error, salir]);

  const elegir = (f: File | undefined) => {
    if (!f || !f.type.startsWith("image/")) return;
    setArchivo(f); setVista(URL.createObjectURL(f)); guardar.reset();
  };
  const filasEval = new Map((evaluacion.data?.filas ?? []).map((f) => [f.id, f]));

  return (
    <>
      <section className="analisis calib__alta">
        <div className="analisis__caja analisis__subida" role="button" tabIndex={0}
             aria-label="Elegir una foto para calibrar"
             onClick={() => entrada.current?.click()}
             onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
             onDragOver={(e) => e.preventDefault()}
             onDrop={(e) => { e.preventDefault(); elegir(e.dataTransfer.files[0]); }}>
          {vista ? <img src={vista} alt="Foto a calibrar" /> : (
            <span className="analisis__invitacion">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" /></svg>
              Subí una foto y marcá cómo ves la planta
            </span>
          )}
          <input ref={entrada} type="file" accept="image/*" hidden
                 onChange={(e) => { elegir(e.target.files?.[0]); e.target.value = ""; }} />
        </div>

        <div className="lirio__texto calib__form">
          <span className="lirio__et">¿Cómo la ves vos?</span>
          <div className="filtros">
            {CLASES.map((c) => (
              <button key={c} aria-pressed={etiqueta === c} onClick={() => setEtiqueta(c)}>{NOMBRE[c]}</button>
            ))}
          </div>
          <label className="calib__check">
            <input type="checkbox" checked={conPuntaje} onChange={(e) => setConPuntaje(e.target.checked)} />
            Agregar un puntaje de turgencia (0 = toda caída, 100 = turgente)
          </label>
          {conPuntaje && (
            <label className="calib__rango">
              <input type="range" min={0} max={100} value={puntaje} onChange={(e) => setPuntaje(+e.target.value)} />
              <span>{puntaje} · {NOMBRE[estadoDe(puntaje)!]}</span>
            </label>
          )}
          <input className="calib__nota" type="text" maxLength={500} value={nota} onChange={(e) => setNota(e.target.value)}
                 placeholder="Nota (opcional): por qué, qué se ve, cuándo se regó…" aria-label="Nota" />
          <label className="calib__check">
            <input type="checkbox" checked={conIa} onChange={(e) => setConIa(e.target.checked)} />
            También analizar con IA (gasta cuota del plan gratuito)
          </label>
          <div className="calib__acciones">
            <button className="calib__guardar" disabled={!archivo || !etiqueta || guardar.isPending}
                    onClick={() => guardar.mutate()}>
              {guardar.isPending ? "Guardando…" : "Guardar en la calibración"}
            </button>
            {guardar.isError && <span className="analisis__error">{guardar.error.message}</span>}
            {guardar.isSuccess && (
              <span className="lirio__pie">
                Guardada. Visión clásica: {guardar.data.vision_puntaje ?? "—"}
                {guardar.data.ia_puntaje !== null && ` · IA: ${guardar.data.ia_puntaje}`}
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="seccion">
        <div className="seccion__cab">
          <h2>Fotos de calibración {lista.data ? `(${lista.data.length})` : ""}</h2>
          <div className="filtros">
            <button onClick={() => evaluacion.mutate()} disabled={evaluacion.isPending || !lista.data?.length}>
              {evaluacion.isPending ? "Evaluando…" : "Re-evaluar con la versión actual"}
            </button>
            <button onClick={salir}>Salir</button>
          </div>
        </div>

        {evaluacion.isError && <p className="analisis__error">{evaluacion.error.message}</p>}
        {evaluacion.data && <Resumen e={evaluacion.data} />}

        {lista.isPending && <p className="cargando">Cargando…</p>}
        {lista.isError && (lista.error as ErrorApi).estado !== 401 && <p className="error">{lista.error.message}</p>}
        {lista.data?.length === 0 && (
          <p className="lirio__detalle">Todavía no hay fotos. Cada foto que suban con su etiqueta es un caso de prueba más.</p>
        )}
        <div className="calib__grilla">
          {lista.data?.map((c) => {
            const ev = filasEval.get(c.id);
            return (
              <article key={c.id} className={`panel calib__tarjeta${ev ? (ev.acierto ? " calib--ok" : " calib--mal") : ""}`}>
                <div className="calib__img"><Miniatura clave={clave} url={c.imagen_url} /></div>
                <dl>
                  <dt>Ustedes</dt><dd><Pastilla estado={c.etiqueta} puntaje={c.puntaje_humano} /></dd>
                  <dt>Visión</dt><dd><Pastilla estado={estadoDe(c.vision_puntaje)} puntaje={c.vision_puntaje} /></dd>
                  {ev && <><dt>Visión hoy</dt><dd><Pastilla estado={ev.estado} puntaje={ev.puntaje} /></dd></>}
                  {c.ia_modelo && <><dt>IA</dt><dd><Pastilla estado={estadoDe(c.ia_puntaje)} puntaje={c.ia_puntaje} /></dd></>}
                </dl>
                {c.nota && <p className="calib__nota-txt">{c.nota}</p>}
                <div className="calib__pie">
                  <span>#{c.id} · {new Date(c.creada_en).toLocaleDateString("es-UY")} · {c.vision_version}</span>
                  {aBorrar === c.id ? (
                    <span>
                      <button className="calib__borrar" onClick={() => borrar.mutate(c.id)}>Sí, borrar</button>
                      <button className="calib__link" onClick={() => setABorrar(null)}>No</button>
                    </span>
                  ) : (
                    <button className="calib__link" onClick={() => setABorrar(c.id)}>Borrar</button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}

function Resumen({ e }: { e: Evaluacion }) {
  return (
    <div className="panel calib__resumen">
      <div className="calib__kpis">
        <div><span className="lirio__et">Versión</span><strong>{e.version}</strong></div>
        <div><span className="lirio__et">Aciertos</span><strong>{e.aciertos} / {e.n}</strong></div>
        <div><span className="lirio__et">Exactitud</span>
          <strong>{e.exactitud !== null ? `${Math.round(e.exactitud * 100)} %` : "—"}</strong></div>
        <div><span className="lirio__et">Error medio del puntaje</span>
          <strong>{e.error_medio ?? "—"}</strong></div>
      </div>
      <table className="calib__matriz">
        <caption>Filas: lo que vieron ustedes · columnas: lo que dice la visión clásica hoy</caption>
        <thead><tr><th />{CLASES.map((c) => <th key={c}>{NOMBRE[c]}</th>)}</tr></thead>
        <tbody>
          {CLASES.map((h) => (
            <tr key={h}>
              <th>{NOMBRE[h]}</th>
              {CLASES.map((p) => (
                <td key={p} className={e.matriz[h][p] ? (h === p ? "calib--ok" : "calib--mal") : ""}>{e.matriz[h][p]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
