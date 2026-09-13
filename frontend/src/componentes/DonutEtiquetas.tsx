import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import type { Punto } from "../lib/analisis";

/* Las 3 clases del clasificador. sin_etiquetar NO es una clase: es ausencia de
   etiqueta, y por eso va en gris y no toma un slot del palette. */
const CLASES: Record<string, { color: string; texto: string }> = {
  saludable: { color: "var(--serie-3)", texto: "Saludable (turgente)" },
  estresada: { color: "var(--serie-4)", texto: "Estresada (marchitez transitoria)" },
  marchita:  { color: "var(--serie-2)", texto: "Marchita (marchitez franca)" },
  sin_etiquetar: { color: "var(--borde)", texto: "Sin etiquetar" },
};

export function DonutEtiquetas({ puntos }: { puntos: Punto[] }) {
  const cuenta = new Map<string, number>();
  for (const p of puntos) {
    const k = p.condicion_etiqueta ?? "sin_etiquetar";
    cuenta.set(k, (cuenta.get(k) ?? 0) + 1);
  }
  const total = puntos.length;
  const datos = ["saludable", "estresada", "marchita", "sin_etiquetar"]
    .map((k) => ({ k, n: cuenta.get(k) ?? 0, ...CLASES[k] }))
    .filter((d) => d.n > 0);

  if (!total) return <p className="vacio">Sin datos.</p>;

  return (
    <>
      <ResponsiveContainer width="100%" height={170}>
        <PieChart>
          <Pie data={datos} dataKey="n" nameKey="texto" cx="50%" cy="50%"
               innerRadius={48} outerRadius={72} paddingAngle={2}
               stroke="var(--panel)" strokeWidth={2} isAnimationActive={false}>
            {datos.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Pie>
          <Tooltip content={({ active, payload }: any) =>
            active && payload?.length ? (
              <div className="tt">
                <div className="tt__t">{payload[0].name}</div>
                <div className="tt__v">
                  <strong>{payload[0].value}</strong> ·{" "}
                  {((payload[0].value / total) * 100).toFixed(1)} %
                </div>
              </div>
            ) : null} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="leyenda">
        {datos.map((d) => (
          <li key={d.k}>
            <i style={{ background: d.color }} />
            <span>{d.texto}</span>
            <b>{d.n} · {((d.n / total) * 100).toFixed(1)} %</b>
          </li>
        ))}
      </ul>
    </>
  );
}
