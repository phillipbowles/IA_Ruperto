/** Medidor de turgencia: un semicírculo de rojo (hojas caídas) a verde
 *  (turgente) con una aguja que apunta al puntaje 0–100 del análisis. La aguja
 *  gira con una transición CSS (estilos.css, sección «análisis de foto»).
 *  `null` = todavía no hay resultado: aguja en reposo a la izquierda y apagada. */

const CX = 120;
const CY = 124;
const R_EXT = 104;
const R_INT = 78;
const FRANJAS = ["#8e2b24", "#c2452a", "#e48a3c", "#e9c13f", "#4eae45", "#2f8a3a"];
const HUECO = 1.6; // grados entre franjas

// 0 → izquierda (180°), 100 → derecha (0°); en SVG y crece hacia abajo.
const punto = (grados: number, r: number) => {
  const a = (grados * Math.PI) / 180;
  return `${(CX + r * Math.cos(a)).toFixed(2)},${(CY - r * Math.sin(a)).toFixed(2)}`;
};

function franja(i: number) {
  const paso = 180 / FRANJAS.length;
  const desde = 180 - i * paso - (i ? HUECO / 2 : 0);
  const hasta = 180 - (i + 1) * paso + (i < FRANJAS.length - 1 ? HUECO / 2 : 0);
  return `M${punto(desde, R_EXT)} A${R_EXT},${R_EXT} 0 0 1 ${punto(hasta, R_EXT)}`
    + ` L${punto(hasta, R_INT)} A${R_INT},${R_INT} 0 0 0 ${punto(desde, R_INT)} Z`;
}

export function Medidor({ puntaje }: { puntaje: number | null }) {
  const giro = puntaje === null ? -90 : -90 + (Math.max(0, Math.min(100, puntaje)) / 100) * 180;
  const marcas = Array.from({ length: 21 }, (_, i) => 180 - i * 9);

  return (
    <svg viewBox="0 0 240 150" role="img" className={`medidor${puntaje === null ? " medidor--vacio" : ""}`}
         aria-label={puntaje === null ? "Medidor de turgencia sin resultado" : `Turgencia ${puntaje} de 100`}>
      {FRANJAS.map((color, i) => <path key={i} d={franja(i)} fill={color} />)}
      <path id="medidor-arco" d={`M${punto(180, 50)} A50,50 0 0 1 ${punto(0, 50)}`} fill="none" />
      {marcas.map((g, i) => (
        <line key={g} className="medidor-marca"
              x1={punto(g, R_INT - 3).split(",")[0]} y1={punto(g, R_INT - 3).split(",")[1]}
              x2={punto(g, R_INT - (i % 5 ? 8 : 13)).split(",")[0]} y2={punto(g, R_INT - (i % 5 ? 8 : 13)).split(",")[1]} />
      ))}
      <text className="medidor-titulo">
        <textPath href="#medidor-arco" startOffset="50%" textAnchor="middle">TURGENCIA</textPath>
      </text>
      <g className="medidor-aguja" style={{ transform: `rotate(${giro}deg)`, transformOrigin: `${CX}px ${CY}px` }}>
        <path d={`M${CX - 5},${CY} L${CX},${CY - 92} L${CX + 5},${CY} Z`} />
      </g>
      <circle className="medidor-eje" cx={CX} cy={CY} r="13" />
      <text className="medidor-valor" x={CX} y={CY + 4} textAnchor="middle">{puntaje ?? "—"}</text>
    </svg>
  );
}
