import type { Clase, EtiquetaOrigen } from "../tipos";
import { hace } from "../lib/formato";

/** Avatar del lirio de paz en la cabecera: la pose y la carita salen de la
 *  predicción del modelo de la placa en la última medición. Si la placa no
 *  predijo (firmware anterior al 2.0.0, o sin DHT11), cae a la
 *  `condicion_etiqueta` del botón y lo dice en el pie. Las transiciones entre estados
 *  son CSS (estilos.css, sección «avatar del lirio»): cada hoja rota en la
 *  base y la lámina rota en la punta del pecíolo, así se dobla en vez de girar
 *  entera. `null` = la última fila vino `sin_etiquetar`: pose neutra, sin
 *  inventar un estado. */

const INFO: Record<Clase | "sin", { nombre: string; detalle: string }> = {
  saludable: { nombre: "Saludable", detalle: "Turgente: hojas firmes y erguidas, la espata bien arriba." },
  estresada: { nombre: "Estresada", detalle: "Marchitez transitoria: las hojas empiezan a ceder y la flor se inclina." },
  marchita: { nombre: "Marchita", detalle: "Marchitez franca: hojas caídas sobre la maceta. Necesita riego." },
  sin: { nombre: "Sin etiqueta", detalle: "La última medición no trae observación. El botón de la maceta la registra." },
};

const ORIGEN: Record<EtiquetaOrigen, string> = {
  manual: "observación manual",
  propagada: "heredada de la última observación",
  corregida: "corregida desde el front",
  desconocido: "origen desconocido",
};

// Pecíolo desde la base (120,176) hasta la articulación `j`; la lámina sale de ahí.
// Orden de dibujo: de atrás (h3) hacia adelante (h1, h5).
const HOJAS = [
  { c: "h3", j: 110, lam: "M120,110 C103,92 103,56 120,32 C137,56 137,92 120,110 Z", n: "M120,108 L120,38" },
  { c: "h2", j: 120, lam: "M120,120 C104,102 104,68 120,46 C136,68 136,102 120,120 Z", n: "M120,118 L120,52" },
  { c: "h4", j: 122, lam: "M120,122 C104,104 104,70 120,48 C136,70 136,104 120,122 Z", n: "M120,120 L120,54" },
  { c: "h1", j: 138, lam: "M120,138 C104,120 104,86 120,64 C136,86 136,120 120,138 Z", n: "M120,136 L120,70" },
  { c: "h5", j: 140, lam: "M120,140 C104,122 104,88 120,66 C136,88 136,122 120,140 Z", n: "M120,138 L120,72" },
];

const ESTRELLA = (r: number) => {
  const k = r / 4;
  return `M0,-${r} L${k},-${k} L${r},0 L${k},${k} L0,${r} L-${k},${k} L-${r},0 L-${k},-${k} Z`;
};

function Hoja({ c, j, lam, n }: (typeof HOJAS)[number]) {
  return (
    <g className={`lirio-hoja ${c}`} style={{ transformOrigin: "120px 176px" }}>
      <path className="lirio-peciolo" d={`M120,176 L120,${j}`} />
      <g className="lirio-lam" style={{ transformOrigin: `120px ${j}px` }}>
        <path className="lirio-lam-forma" d={lam} />
        <path className="lirio-nervio" d={n} />
      </g>
    </g>
  );
}

export type FuenteEstado =
  | { tipo: "modelo"; version: string; proba: number | null }
  | { tipo: "boton"; origen: EtiquetaOrigen | null };

export function AvatarLirio({ estado, fuente, ts }: {
  estado: Clase | null;
  fuente: FuenteEstado;
  ts: string;
}) {
  const clave = estado ?? "sin";
  const { nombre, detalle } = INFO[clave];
  const [atras, ...frente] = HOJAS;

  return (
    <section className={`lirio lirio--${clave}`} aria-live="polite">
      <div className="lirio__escena">
        <svg viewBox="0 0 240 260" role="img" aria-label={`Lirio de paz: ${nombre.toLowerCase()}`}>
          <ellipse cx="120" cy="254" rx="66" ry="5" className="lirio-sombra" />
          <path d="M68,184 L172,184 L162,245 Q161,252 154,252 L86,252 Q79,252 78,245 Z" className="lirio-maceta" />
          <path d="M82,192 L90,244" className="lirio-nervio" />
          <rect x="60" y="168" width="120" height="20" rx="7" className="lirio-borde" />
          <ellipse cx="120" cy="174" rx="52" ry="6" className="lirio-tierra" />
          <g className="lirio-grietas">
            <path d="M94,174 l6,-2 l5,3" />
            <path d="M132,173 l5,2 l7,-2" />
          </g>

          <g className="lirio-cara lirio-cara--saludable">
            <circle className="lirio-ojo" cx="104" cy="212" r="4.5" />
            <circle className="lirio-ojo" cx="136" cy="212" r="4.5" />
            <circle className="lirio-brillo-ojo" cx="105.6" cy="210.4" r="1.4" />
            <circle className="lirio-brillo-ojo" cx="137.6" cy="210.4" r="1.4" />
            <path className="lirio-trazo" d="M111,224 Q120,233 129,224" />
            <ellipse className="lirio-mejilla" cx="94" cy="221" rx="5" ry="3" />
            <ellipse className="lirio-mejilla" cx="146" cy="221" rx="5" ry="3" />
          </g>
          <g className="lirio-cara lirio-cara--estresada">
            <circle className="lirio-ojo" cx="104" cy="213" r="3.8" />
            <circle className="lirio-ojo" cx="136" cy="213" r="3.8" />
            <path className="lirio-trazo" d="M97,206 L109,202" />
            <path className="lirio-trazo" d="M131,202 L143,206" />
            <path className="lirio-trazo" d="M111,228 Q115.5,224 120,228 Q124.5,232 129,228" />
            <g transform="translate(153,197)">
              <path className="lirio-gota" d="M0,-7 C3,-2 5,1 5,3 A5,5 0 0 1 -5,3 C-5,1 -3,-2 0,-7 Z" />
            </g>
          </g>
          <g className="lirio-cara lirio-cara--marchita">
            <path className="lirio-trazo" d="M98,214 Q104,209 110,214" />
            <path className="lirio-trazo" d="M130,214 Q136,209 142,214" />
            <path className="lirio-trazo" d="M111,232 Q120,223 129,232" />
          </g>
          <g className="lirio-cara lirio-cara--sin">
            <circle className="lirio-ojo" cx="104" cy="212" r="3.8" />
            <circle className="lirio-ojo" cx="136" cy="212" r="3.8" />
            <path className="lirio-trazo" d="M112,227 L128,227" />
          </g>

          <g className="lirio-planta" style={{ transformOrigin: "120px 176px" }}>
            <Hoja {...atras} />
            <g className="lirio-tallo" style={{ transformOrigin: "120px 176px" }}>
              <path className="lirio-peciolo" d="M120,176 C121,140 119,100 120,64" />
              <g className="lirio-espata" style={{ transformOrigin: "120px 64px" }}>
                <path className="lirio-espata-forma" d="M120,64 C102,56 99,30 120,8 C141,30 138,56 120,64 Z" />
                <path className="lirio-espata-nervio" d="M120,60 L120,16" />
                <ellipse className="lirio-espadice" cx="122" cy="44" rx="4" ry="12" />
              </g>
            </g>
            {frente.map((h) => <Hoja key={h.c} {...h} />)}
          </g>

          <g className="lirio-brillos">
            <g transform="translate(58,70)"><path className="lirio-estrella" d={ESTRELLA(7)} /></g>
            <g transform="translate(184,52)"><path className="lirio-estrella e2" d={ESTRELLA(6)} /></g>
            <g transform="translate(190,128)"><path className="lirio-estrella e3" d={ESTRELLA(5)} /></g>
          </g>
          <g className="lirio-caida">
            <g transform="translate(176,96)">
              <path className="lirio-hojita" d="M0,0 C-5,-4 -5,-12 0,-17 C5,-12 5,-4 0,0 Z" />
            </g>
          </g>
        </svg>
      </div>

      <div className="lirio__texto">
        <span className="lirio__et">Cómo está la planta ahora</span>
        <span className="lirio__nombre">
          <span className="lirio__punto" aria-hidden="true" />
          {nombre}
        </span>
        <p className="lirio__detalle">{detalle}</p>
        <span className="lirio__pie">
          {fuente.tipo === "modelo"
            ? `Predicción del modelo de la placa (${fuente.version}`
              + `${fuente.proba !== null ? `, p = ${fuente.proba.toFixed(2)}` : ""})`
            : `Sin predicción del modelo: etiqueta del botón`
              + `${fuente.origen && estado ? ` (${ORIGEN[fuente.origen]})` : ""}`}
          {" · "}{hace(ts)}
        </span>
      </div>
    </section>
  );
}
