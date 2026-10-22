import { Fragment, useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { enviarImagen } from "../api/cliente";
import type { AnalisisFoto as Resultado, Clase, MetodoAnalisis } from "../tipos";
import { Medidor } from "./Medidor";

/** Pestaña «Analizar foto»: se sube una foto del lirio y vuelve un puntaje de
 *  turgencia (cuánto están caídas las hojas y las flores) que mueve el medidor.
 *  Dos métodos: un modelo de IA mirando la foto (Gemini o Claude), o visión por
 *  computadora clásica. Es una
 *  consulta: no se guarda en la base ni cambia la etiqueta de la placa. */

const METODOS: { id: MetodoAnalisis; texto: string; descripcion: string }[] = [
  { id: "ia", texto: "IA",
    descripcion: "Un modelo de IA (Gemini o Claude, el que esté configurado) mira la foto y juzga cuánto están caídas las hojas y las flores." },
  { id: "vision", texto: "Visión clásica",
    descripcion: "Segmenta las hojas por color y mide su ángulo sobre la horizontal desde la base de la planta, sin IA generativa." },
];

const METRICAS: Record<string, string> = {
  angulo_hojas: "Ángulo medio de las hojas (°)",
  fraccion_colgando: "Follaje por debajo de la base",
  angulo_flores: "Ángulo de las espatas (°)",
  fraccion_verde: "Imagen ocupada por hojas",
};

const INFO: Record<Clase, { nombre: string; detalle: string }> = {
  saludable: { nombre: "Saludable", detalle: "Turgente: hojas firmes y erguidas, la espata bien arriba." },
  estresada: { nombre: "Estresada", detalle: "Marchitez transitoria: las hojas empiezan a ceder y la flor se inclina." },
  marchita: { nombre: "Marchita", detalle: "Marchitez franca: hojas caídas sobre la maceta. Necesita riego." },
};

// Lado mayor con el que se manda la foto: más resolución no mejora el
// diagnóstico y una foto de celular sin achicar pasa los 5 MB.
const LADO_MAX = 1568;

async function achicar(archivo: File): Promise<Blob> {
  const bmp = await createImageBitmap(archivo);
  const k = Math.min(1, LADO_MAX / Math.max(bmp.width, bmp.height));
  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(bmp.width * k);
  lienzo.height = Math.round(bmp.height * k);
  lienzo.getContext("2d")!.drawImage(bmp, 0, 0, lienzo.width, lienzo.height);
  bmp.close();
  return new Promise((ok, mal) =>
    lienzo.toBlob((b) => (b ? ok(b) : mal(new Error("No se pudo leer la imagen"))), "image/jpeg", 0.85));
}

export function AnalisisFoto() {
  const entrada = useRef<HTMLInputElement>(null);
  const [vista, setVista] = useState<string | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [metodo, setMetodo] = useState<MetodoAnalisis>("ia");
  const [archivo, setArchivo] = useState<File | null>(null);
  const analisis = useMutation<Resultado, Error, { archivo: File; metodo: MetodoAnalisis }>({
    mutationFn: async ({ archivo, metodo }) =>
      enviarImagen<Resultado>(`/analisis-foto?metodo=${metodo}`, await achicar(archivo)),
  });

  useEffect(() => () => { if (vista) URL.revokeObjectURL(vista); }, [vista]);

  const elegir = (archivo: File | undefined) => {
    if (!archivo || !archivo.type.startsWith("image/")) return;
    setVista(URL.createObjectURL(archivo));
    setArchivo(archivo);
    analisis.mutate({ archivo, metodo });
  };

  // Cambiar de método con una foto ya cargada la vuelve a analizar.
  const cambiarMetodo = (m: MetodoAnalisis) => {
    setMetodo(m);
    if (archivo) analisis.mutate({ archivo, metodo: m });
  };

  const r = analisis.data;
  const estado: Clase | "sin" = r?.estado ?? "sin";

  return (
    <>
    <div className="seccion__cab analisis__metodos">
      <h2>Método de análisis</h2>
      <div className="filtros">
        {METODOS.map((m) => (
          <button key={m.id} aria-pressed={metodo === m.id} title={m.descripcion}
                  disabled={analisis.isPending} onClick={() => cambiarMetodo(m.id)}>
            {m.texto}
          </button>
        ))}
      </div>
    </div>
    <section className={`analisis lirio--${estado}`} aria-live="polite">
      <div
        className={`analisis__caja analisis__subida${arrastrando ? " analisis__subida--sobre" : ""}`}
        role="button"
        tabIndex={0}
        aria-label="Elegir una foto de la planta"
        onClick={() => entrada.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); elegir(e.dataTransfer.files[0]); }}
      >
        {vista
          ? <img src={vista} alt="Foto de la planta a analizar" />
          : (
            <span className="analisis__invitacion">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" /></svg>
              Subí o arrastrá una foto del lirio
            </span>
          )}
        <input ref={entrada} type="file" accept="image/*" hidden
               onChange={(e) => { elegir(e.target.files?.[0]); e.target.value = ""; }} />
      </div>

      <div className="analisis__caja analisis__medidor">
        <Medidor puntaje={r?.puntaje ?? null} />
      </div>

      <div className="lirio__texto">
        <span className="lirio__et">
          {metodo === "ia" ? "Análisis de la foto con IA" : "Análisis por visión por computadora"}
        </span>
        {analisis.isPending && <p className="lirio__detalle">Mirando las hojas y las flores…</p>}
        {analisis.isError && <p className="lirio__detalle analisis__error">{analisis.error.message}</p>}
        {analisis.isIdle && (
          <p className="lirio__detalle">
            {METODOS.find((m) => m.id === metodo)!.descripcion} El resultado se ubica en el medidor: rojo es
            marchita, verde es turgente.
          </p>
        )}
        {r && !r.es_planta && (
          <p className="lirio__detalle">No se ve una planta en la foto. {r.explicacion}</p>
        )}
        {r?.estado && (
          <>
            <span className="lirio__nombre">
              <span className="lirio__punto" aria-hidden="true" />
              {INFO[r.estado].nombre}
            </span>
            <p className="lirio__detalle">{INFO[r.estado].detalle}</p>
            <dl className="analisis__detalle">
              <dt>Hojas</dt><dd>{r.hojas}</dd>
              <dt>Flores</dt><dd>{r.flores}</dd>
              <dt>Diagnóstico</dt><dd>{r.explicacion}</dd>
              {r.metricas && Object.entries(METRICAS).filter(([k]) => k in r.metricas!).map(([k, nombre]) => (
                <Fragment key={k}>
                  <dt>{nombre}</dt>
                  <dd>{k.startsWith("fraccion") ? `${(r.metricas![k] * 100).toFixed(0)} %` : r.metricas![k]}</dd>
                </Fragment>
              ))}
            </dl>
          </>
        )}
        {r && <span className="lirio__pie">Analizado por {r.modelo} · no se guarda en la base</span>}
      </div>
    </section>
    </>
  );
}
