import { useEffect, useRef } from "react";
import { CORTE_SUELO_MV, CORTE_TEMP_C, HOJAS, VERSION_ARBOL, recorrido, type Hoja } from "../lib/modeloPlaca";
import type { Clase } from "../tipos";

/** El árbol de decisión de la placa con el recorrido de la medición actual:
 *  un punto que pulsa baja de nodo en nodo hasta la hoja y vuelve a empezar.
 *  Mismo lenguaje visual que el avatar del lirio (estilos.css, «árbol»). */

const NOMBRE: Record<Clase, string> = { saludable: "Saludable", estresada: "Estresada", marchita: "Marchita" };

// Geometría (viewBox 760 × 400). Nodos: centro y medio alto de la tarjeta.
const RAIZ = { x: 380, y: 62 };
const SUELO = { x: 560, y: 176 };
const NODO_MEDIO_ALTO = 32;
const POS_HOJA: Record<Hoja, { x: number; y: number }> = {
  frio: { x: 160, y: 286 },
  humedo: { x: 450, y: 296 },
  seco: { x: 670, y: 296 },
};
const R_HOJA = 40;

const abajo = (n: { x: number; y: number }) => `${n.x},${n.y + NODO_MEDIO_ALTO}`;
const arriba = (n: { x: number; y: number }, dy: number) => `${n.x},${n.y - dy}`;
const curva = (a: { x: number; y: number }, b: { x: number; y: number }, dyB: number) => {
  const y0 = a.y + NODO_MEDIO_ALTO;
  const y1 = b.y - dyB;
  const m = (y0 + y1) / 2;
  return `M${abajo(a)} C${a.x},${m} ${b.x},${m} ${arriba(b, dyB)}`;
};

// Las cuatro ramas del árbol.
const RAMAS = {
  raizFrio: curva(RAIZ, POS_HOJA.frio, R_HOJA),
  raizSuelo: curva(RAIZ, SUELO, NODO_MEDIO_ALTO),
  sueloHumedo: curva(SUELO, POS_HOJA.humedo, R_HOJA),
  sueloSeco: curva(SUELO, POS_HOJA.seco, R_HOJA),
};

// Tramos que recorre el punto para cada hoja (el paso por adentro del nodo del
// suelo es una recta de arriba hacia abajo de la tarjeta).
const DENTRO_SUELO = `M${arriba(SUELO, NODO_MEDIO_ALTO)} L${abajo(SUELO)}`;
const DENTRO_RAIZ = `M${RAIZ.x},${RAIZ.y - NODO_MEDIO_ALTO} L${abajo(RAIZ)}`;
const TRAMOS: Record<Hoja, string[]> = {
  frio: [DENTRO_RAIZ, RAMAS.raizFrio],
  humedo: [DENTRO_RAIZ, RAMAS.raizSuelo, DENTRO_SUELO, RAMAS.sueloHumedo],
  seco: [DENTRO_RAIZ, RAMAS.raizSuelo, DENTRO_SUELO, RAMAS.sueloSeco],
};

// Velocidad del punto y pausas (ms). Se para en cada nodo y más en la hoja.
const PX_POR_MS = 0.16;
const PAUSA_NODO = 650;
const PAUSA_HOJA = 1500;

function usarRecorrido(hoja: Hoja | null) {
  const punto = useRef<SVGGElement>(null);
  const medidas = useRef<SVGPathElement[]>([]);
  useEffect(() => {
    const g = punto.current;
    if (!g || !hoja) return;
    // Sólo los tramos de esta hoja: la ref puede tener los de una hoja anterior.
    const tramos = medidas.current.slice(0, TRAMOS[hoja].length);
    const largos = tramos.map((p) => p.getTotalLength());
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
      const p = tramos[i].getPointAtLength(largos[i] * f);
      g.setAttribute("transform", `translate(${p.x},${p.y})`);
    };
    if (quieto) { ubicar(tramos.length - 1, 1); return; }

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
  }, [hoja]);
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

function Nodo({ x, y, pregunta, valor, activo }: {
  x: number; y: number; pregunta: string; valor: string; activo: boolean;
}) {
  return (
    <g className={`arbol-nodo${activo ? " arbol--activo" : ""}`} transform={`translate(${x},${y})`}>
      <rect x="-118" y={-NODO_MEDIO_ALTO} width="236" height={NODO_MEDIO_ALTO * 2} rx="14" />
      <text y="-6" textAnchor="middle" className="arbol-pregunta">{pregunta}</text>
      <text y="16" textAnchor="middle" className="arbol-valor">{valor}</text>
    </g>
  );
}

function HojaArbol({ hoja, activa }: { hoja: Hoja; activa: boolean }) {
  const { x, y } = POS_HOJA[hoja];
  const { clase, proba } = HOJAS[hoja];
  const p = proba[["saludable", "estresada", "marchita"].indexOf(clase)];
  return (
    <g className={`arbol-hoja lirio--${clase}${activa ? " arbol--activo" : ""}`} transform={`translate(${x},${y})`}>
      <circle r={R_HOJA} className="arbol-hoja-fondo" />
      <g transform="translate(0,6)"><MiniLirio clase={clase} /></g>
      <text y={R_HOJA + 18} textAnchor="middle" className="arbol-hoja-nombre">{NOMBRE[clase]}</text>
      <text y={R_HOJA + 34} textAnchor="middle" className="arbol-valor">p = {p.toFixed(2).replace(".", ",")}</text>
    </g>
  );
}

const etiquetaRama = (texto: string, x: number, y: number) => (
  <text x={x} y={y} textAnchor="middle" className="arbol-rama-et">{texto}</text>
);

export function ArbolModelo({ temp_c, suelo_mv, prediccion, modeloVersion }: {
  temp_c: number | null;
  suelo_mv: number | null;
  prediccion: Clase | null;
  modeloVersion: string | null;
}) {
  const hoja = recorrido(temp_c, suelo_mv);
  const { punto, medidas } = usarRecorrido(hoja);
  const enCamino = (rama: keyof typeof RAMAS) =>
    hoja !== null && (
      (rama === "raizFrio" && hoja === "frio")
      || (rama === "raizSuelo" && hoja !== "frio")
      || (rama === "sueloHumedo" && hoja === "humedo")
      || (rama === "sueloSeco" && hoja === "seco"));
  const coma = (v: number, d: number) => v.toFixed(d).replace(".", ",");
  const otraVersion = modeloVersion !== null && modeloVersion !== VERSION_ARBOL;

  return (
    <div className="arbol">
      <svg viewBox="0 0 760 400" role="img"
           aria-label={hoja ? `La medición actual cae en la hoja ${NOMBRE[HOJAS[hoja].clase]}` : "Árbol de decisión de la placa"}>
        {Object.entries(RAMAS).map(([k, d]) => (
          <path key={k} d={d} className={`arbol-rama${enCamino(k as keyof typeof RAMAS) ? " arbol--activo" : ""}`} />
        ))}
        {etiquetaRama("sí", 236, 160)}
        {etiquetaRama("no", 490, 112)}
        {etiquetaRama("sí", 482, 238)}
        {etiquetaRama("no", 642, 238)}

        <Nodo x={RAIZ.x} y={RAIZ.y} pregunta={`¿temp. del aire ≤ ${coma(CORTE_TEMP_C, 2)} °C?`}
              valor={temp_c !== null ? `ahora: ${coma(temp_c, 1)} °C` : "ahora: sin dato"} activo={hoja !== null} />
        <Nodo x={SUELO.x} y={SUELO.y} pregunta={`¿sonda de suelo ≤ ${coma(CORTE_SUELO_MV, 1)} mV?`}
              valor={suelo_mv !== null ? `ahora: ${Math.round(suelo_mv)} mV` : "ahora: sin dato"}
              activo={hoja === "humedo" || hoja === "seco"} />
        {(Object.keys(POS_HOJA) as Hoja[]).map((h) => <HojaArbol key={h} hoja={h} activa={h === hoja} />)}

        {/* Trayectos invisibles que sigue el punto. */}
        {hoja && TRAMOS[hoja].map((d, i) => (
          <path key={`${hoja}-${i}`} d={d} fill="none" stroke="none"
                ref={(el) => { if (el) medidas.current[i] = el; }} />
        ))}
        {hoja && (
          <g ref={punto} className="arbol-punto" transform={`translate(${RAIZ.x},${RAIZ.y - NODO_MEDIO_ALTO})`}>
            <circle r="13" className="arbol-punto-halo" />
            <circle r="6.5" className="arbol-punto-centro" />
          </g>
        )}
      </svg>
      <p className="lirio__pie arbol__pie">
        {hoja
          ? <>La medición actual cae en <b>{NOMBRE[HOJAS[hoja].clase]}</b>.</>
          : <>Falta {temp_c === null ? "la temperatura del aire" : "la lectura de la sonda"} para recorrer el árbol.</>}
        {prediccion && <> La placa predijo <b>{NOMBRE[prediccion]}</b>.</>}
        {" "}Modelo {VERSION_ARBOL}: profundidad 2, dos preguntas por predicción, 81 B en la flash.
        {otraVersion && <span className="arbol__aviso"> Ojo: la placa reporta {modeloVersion}; este dibujo es de {VERSION_ARBOL}.</span>}
      </p>
    </div>
  );
}
