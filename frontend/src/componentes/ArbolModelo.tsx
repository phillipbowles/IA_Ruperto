import { useEffect, useRef } from "react";
import { FEATURE, FLASH_B, NODOS, PROFUNDIDAD, VERSION_ARBOL, esHoja, recorrido, type Nodo as NodoArbol } from "../lib/modeloPlaca";
import type { Clase } from "../tipos";

/** El árbol de decisión de la placa con el recorrido de la medición actual:
 *  un punto que pulsa baja de nodo en nodo hasta la hoja y vuelve a empezar.
 *  Mismo lenguaje visual que el avatar del lirio (estilos.css, «árbol»).
 *  La forma sale de `modelo_placa.json` (lib/modeloPlaca.ts): el layout se
 *  calcula, así que sirve para cualquier árbol que exporte el modelo. */

const NOMBRE: Record<Clase, string> = { saludable: "Saludable", estresada: "Estresada", marchita: "Marchita" };
const CLASES: Clase[] = ["saludable", "estresada", "marchita"];

// Geometría. Las hojas van en fila, separadas DX; cada nodo interno queda
// centrado sobre sus dos hijos; cada nivel baja DY.
const DX = 112;
const DY = 112;
const MARGEN_X = 70;
const Y0 = 50;
const NODO_MEDIO_ALTO = 28;
const NODO_ANCHO = 200;
const R_HOJA = 34;

interface Pos { x: number; y: number; hoja: boolean }

function layout(nodos: NodoArbol[]) {
  const pos: Pos[] = [];
  let hojas = 0;
  let prof = 0;
  const ubicar = (i: number, d: number): number => {
    const n = nodos[i];
    prof = Math.max(prof, d);
    if (esHoja(n)) {
      pos[i] = { x: MARGEN_X + hojas++ * DX, y: Y0 + d * DY + 16, hoja: true };
    } else {
      const xs = ubicar(n.si, d + 1);
      const xn = ubicar(n.no, d + 1);
      pos[i] = { x: (xs + xn) / 2, y: Y0 + d * DY, hoja: false };
    }
    return pos[i].x;
  };
  ubicar(0, 0);
  return { pos, ancho: 2 * MARGEN_X + (hojas - 1) * DX, alto: Y0 + prof * DY + R_HOJA + 70 };
}

const ARMADO = NODOS ? layout(NODOS) : null;

// Borde superior/inferior de un nodo o de una hoja.
const tope = (p: Pos) => p.y - (p.hoja ? R_HOJA : NODO_MEDIO_ALTO);
const base = (p: Pos) => p.y + NODO_MEDIO_ALTO;
const curva = (a: Pos, b: Pos) => {
  const y0 = base(a);
  const y1 = tope(b);
  const m = (y0 + y1) / 2;
  return `M${a.x},${y0} C${a.x},${m} ${b.x},${m} ${b.x},${y1}`;
};
const dentro = (a: Pos) => `M${a.x},${a.y - NODO_MEDIO_ALTO} L${a.x},${base(a)}`;

/** Tramos que recorre el punto: el paso por adentro de cada nodo y la rama al siguiente. */
function tramosDe(camino: number[], pos: Pos[]): string[] {
  const out: string[] = [];
  for (let k = 0; k < camino.length - 1; k++) {
    out.push(dentro(pos[camino[k]]), curva(pos[camino[k]], pos[camino[k + 1]]));
  }
  return out;
}

// Velocidad del punto y pausas (ms). Se para en cada nodo y más en la hoja.
const PX_POR_MS = 0.16;
const PAUSA_NODO = 650;
const PAUSA_HOJA = 1500;

function usarRecorrido(tramos: string[]) {
  const punto = useRef<SVGGElement>(null);
  const medidas = useRef<SVGPathElement[]>([]);
  const clave = tramos.join("|");
  useEffect(() => {
    const g = punto.current;
    if (!g || !tramos.length) return;
    // Sólo los tramos de este camino: la ref puede tener los de uno anterior.
    const paths = medidas.current.slice(0, tramos.length);
    const largos = paths.map((p) => p.getTotalLength());
    // Plan: [tramo, ms de viaje] intercalado con pausas.
    const plan: { tramo: number | null; ms: number }[] = [];
    largos.forEach((l, i) => {
      plan.push({ tramo: i, ms: l / PX_POR_MS });
      // Pausa al terminar el paso por adentro de un nodo (tramos pares).
      if (i % 2 === 0) plan.push({ tramo: null, ms: PAUSA_NODO });
    });
    plan.push({ tramo: null, ms: PAUSA_HOJA });
    const total = plan.reduce((s, p) => s + p.ms, 0);

    const quieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ubicar = (i: number, f: number) => {
      const p = paths[i].getPointAtLength(largos[i] * f);
      g.setAttribute("transform", `translate(${p.x},${p.y})`);
    };
    if (quieto) { ubicar(paths.length - 1, 1); return; }

    let raf = 0;
    const t0 = performance.now();
    const cuadro = (ahora: number) => {
      let t = (ahora - t0) % total;
      let ultimo = 0;
      for (const paso of plan) {
        if (t < paso.ms) {
          if (paso.tramo === null) ubicar(ultimo, 1);
          else ubicar(paso.tramo, t / paso.ms);
          break;
        }
        t -= paso.ms;
        if (paso.tramo !== null) ultimo = paso.tramo;
      }
      raf = requestAnimationFrame(cuadro);
    };
    raf = requestAnimationFrame(cuadro);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave]);
  return { punto, medidas };
}

/** Un lirio chiquito con la pose de cada clase, como el avatar. */
function MiniLirio({ clase }: { clase: Clase }) {
  const giro = { saludable: [-28, 0, 28], estresada: [-58, -6, 52], marchita: [-118, -25, 112] }[clase];
  const espata = { saludable: 0, estresada: 30, marchita: 95 }[clase];
  return (
    <g className={`arbol-lirio lirio--${clase}`}>
      <path className="lirio-maceta" d="M-15,6 L15,6 L12,24 Q11.5,26 9,26 L-9,26 Q-11.5,26 -12,24 Z" />
      <rect className="lirio-borde" x="-18" y="1" width="36" height="7" rx="3" />
      {giro.map((g, i) => (
        <g key={i} transform={`rotate(${g})`}>
          <path className="lirio-peciolo" d="M0,2 L0,-8" />
          <path className="lirio-lam-forma" d="M0,-6 C-6,-12 -6,-24 0,-32 C6,-24 6,-12 0,-6 Z" />
        </g>
      ))}
      <g transform={`rotate(${espata})`}>
        <path className="lirio-peciolo" d="M0,2 L0,-20" />
        <path className="lirio-espata-forma" d="M0,-20 C-6,-23 -7,-33 0,-40 C7,-33 6,-23 0,-20 Z" />
      </g>
    </g>
  );
}

const coma = (v: number, d: number) => v.toFixed(d).replace(".", ",");
const umbralTexto = (v: number) => coma(v, Number.isInteger(v) ? 0 : Number.isInteger(v * 10) ? 1 : 2);

function Pregunta({ p, feature, umbral, valor, activo }: {
  p: Pos; feature: string; umbral: number; valor: number | null; activo: boolean;
}) {
  const f = FEATURE[feature] ?? { texto: feature, unidad: "", decimales: 1 };
  return (
    <g className={`arbol-nodo${activo ? " arbol--activo" : ""}`} transform={`translate(${p.x},${p.y})`}>
      <rect x={-NODO_ANCHO / 2} y={-NODO_MEDIO_ALTO} width={NODO_ANCHO} height={NODO_MEDIO_ALTO * 2} rx="14" />
      <text y="-5" textAnchor="middle" className="arbol-pregunta">
        ¿{f.texto} ≤ {umbralTexto(umbral)} {f.unidad}?
      </text>
      <text y="15" textAnchor="middle" className="arbol-valor">
        {valor !== null ? `ahora: ${coma(valor, f.decimales)} ${f.unidad}` : "ahora: sin dato"}
      </text>
    </g>
  );
}

function HojaArbol({ p, clase, proba, activa }: { p: Pos; clase: Clase; proba: number[]; activa: boolean }) {
  const pr = proba[CLASES.indexOf(clase)];
  return (
    <g className={`arbol-hoja lirio--${clase}${activa ? " arbol--activo" : ""}`} transform={`translate(${p.x},${p.y})`}>
      <circle r={R_HOJA} className="arbol-hoja-fondo" />
      <g transform="translate(0,6) scale(0.85)"><MiniLirio clase={clase} /></g>
      <text y={R_HOJA + 17} textAnchor="middle" className="arbol-hoja-nombre">{NOMBRE[clase]}</text>
      <text y={R_HOJA + 32} textAnchor="middle" className="arbol-valor">p = {coma(pr, 2)}</text>
    </g>
  );
}

export function ArbolModelo({ valores, prediccion, modeloVersion }: {
  /** Las features de la medición actual (lib/modeloPlaca.featuresActuales). */
  valores: Record<string, number | null>;
  prediccion: Clase | null;
  modeloVersion: string | null;
}) {
  const camino = recorrido(valores);
  const tramos = camino && ARMADO ? tramosDe(camino, ARMADO.pos) : [];
  const { punto, medidas } = usarRecorrido(tramos);

  if (!NODOS || !ARMADO) {
    return <p className="lirio__pie arbol__pie">El modelo vigente ({VERSION_ARBOL}) no es un árbol: no hay nada que dibujar.</p>;
  }
  const { pos, ancho, alto } = ARMADO;
  const hojaFinal = camino ? NODOS[camino[camino.length - 1]] : null;
  const claseFinal = hojaFinal && esHoja(hojaFinal) ? hojaFinal.clase : null;
  const enCamino = (a: number, b: number) => {
    if (!camino) return false;
    const k = camino.indexOf(a);
    return k >= 0 && camino[k + 1] === b;
  };
  const faltan = NODOS.filter((n) => !esHoja(n) && (valores[n.feature] ?? null) === null)
    .map((n) => (esHoja(n) ? "" : FEATURE[n.feature]?.texto ?? n.feature));
  const otraVersion = modeloVersion !== null && modeloVersion !== VERSION_ARBOL;
  const preguntas = PROFUNDIDAD ?? 0;

  return (
    <div className="arbol">
      {/* Sin tope, un árbol angosto (pocas hojas) se estiraría al ancho del panel. */}
      <svg viewBox={`0 0 ${ancho} ${alto}`} role="img" style={{ maxWidth: Math.round(ancho * 1.25) }}
           aria-label={claseFinal ? `La medición actual cae en la hoja ${NOMBRE[claseFinal]}` : "Árbol de decisión de la placa"}>
        {NODOS.map((n, i) => esHoja(n) ? null : (
          <g key={`r${i}`}>
            {([["sí", n.si], ["no", n.no]] as const).map(([et, h]) => {
              const a = pos[i];
              const b = pos[h];
              const yEt = (base(a) + tope(b)) / 2 - 4;
              const xEt = (a.x + b.x) / 2 + (et === "sí" ? -12 : 12);
              return (
                <g key={et}>
                  <path d={curva(a, b)} className={`arbol-rama${enCamino(i, h) ? " arbol--activo" : ""}`} />
                  <text x={xEt} y={yEt} textAnchor="middle" className="arbol-rama-et">{et}</text>
                </g>
              );
            })}
          </g>
        ))}

        {NODOS.map((n, i) => esHoja(n)
          ? <HojaArbol key={i} p={pos[i]} clase={n.clase} proba={n.proba} activa={!!camino && camino[camino.length - 1] === i} />
          : <Pregunta key={i} p={pos[i]} feature={n.feature} umbral={n.umbral}
                      valor={valores[n.feature] ?? null} activo={!!camino?.includes(i)} />)}

        {/* Trayectos invisibles que sigue el punto. */}
        {tramos.map((d, i) => (
          <path key={`${camino!.join("-")}-${i}`} d={d} fill="none" stroke="none"
                ref={(el) => { if (el) medidas.current[i] = el; }} />
        ))}
        {tramos.length > 0 && (
          <g ref={punto} className="arbol-punto" transform={`translate(${pos[0].x},${pos[0].y - NODO_MEDIO_ALTO})`}>
            <circle r="13" className="arbol-punto-halo" />
            <circle r="6.5" className="arbol-punto-centro" />
          </g>
        )}
      </svg>
      <p className="lirio__pie arbol__pie">
        {claseFinal
          ? <>La medición actual cae en <b>{NOMBRE[claseFinal]}</b>.</>
          : <>Falta {[...new Set(faltan)].join(" y ")} para recorrer el árbol.</>}
        {prediccion && <> La placa predijo <b>{NOMBRE[prediccion]}</b>.</>}
        {" "}Modelo {VERSION_ARBOL}: profundidad {preguntas}, hasta {preguntas} preguntas por predicción, {FLASH_B} B en la flash.
        {otraVersion && <span className="arbol__aviso"> Ojo: la placa reporta {modeloVersion}; este dibujo es de {VERSION_ARBOL}. Hay que volver a flashearla.</span>}
      </p>
    </div>
  );
}
