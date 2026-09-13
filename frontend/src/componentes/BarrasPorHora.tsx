import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";

/** Cobertura por hora del día. Sequential de un solo tono: la barra dice
 *  magnitud, no identidad — más alta es más oscura, y los huecos se ven solos. */
export function BarrasPorHora({ datos }: { datos: { hora: string; n: number }[] }) {
  const max = Math.max(...datos.map((d) => d.n), 1);
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={datos} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey="hora" stroke="var(--texto-3)" fontSize={11}
               tickLine={false} axisLine={{ stroke: "var(--grid)" }} interval={2} />
        <YAxis stroke="var(--texto-3)" fontSize={11} tickLine={false} axisLine={false} width={52} />
        <Tooltip
          cursor={{ fill: "var(--panel-alt)" }}
          content={({ active, payload, label }: any) =>
            active && payload?.length ? (
              <div className="tt">
                <div className="tt__t">{label}:00 – {label}:59</div>
                <div className="tt__v"><strong>{payload[0].value}</strong> muestras</div>
              </div>
            ) : null
          }
        />
        <Bar dataKey="n" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {datos.map((d, i) => (
            <Cell key={i} fill="var(--serie-1)" fillOpacity={d.n ? 0.35 + 0.65 * (d.n / max) : 0.12} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
