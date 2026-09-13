import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceArea,
} from "recharts";
import type { Punto, Tramo } from "../lib/analisis";
import { hora, fechaHora } from "../lib/formato";

interface Props {
  puntos: Punto[];
  campo: keyof Punto;
  color: string;
  unidad: string;
  noche?: Tramo[];
  dominio?: [number | "auto", number | "auto"];
}

function Tip({ active, payload, unidad, nombre }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="tt">
      <div className="tt__t">{fechaHora(p.payload.t)}</div>
      <div className="tt__v">
        {nombre}: <strong>{p.value === null ? "sin dato" : `${p.value} ${unidad}`}</strong>
      </div>
    </div>
  );
}

export function GraficoSerie({ puntos, campo, color, unidad, noche = [], dominio = ["auto", "auto"] }: Props) {
  // null en vez de undefined para que Recharts corte la línea en los huecos en
  // lugar de unir con una recta dos momentos separados por horas.
  const datos = puntos.map((p) => ({ t: p.t, v: (p[campo] as number | null) ?? null }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={datos} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        {noche.map((b, i) => (
          <ReferenceArea
            key={i} x1={b.desde} x2={b.hasta}
            fill="var(--noche)" fillOpacity={0.07} stroke="none"
            ifOverflow="hidden"
          />
        ))}
        <XAxis
          dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]}
          tickFormatter={hora} stroke="var(--texto-3)" fontSize={11}
          tickLine={false} axisLine={{ stroke: "var(--grid)" }} minTickGap={44}
        />
        <YAxis
          domain={dominio} stroke="var(--texto-3)" fontSize={11}
          tickLine={false} axisLine={false} width={52}
        />
        <Tooltip content={<Tip unidad={unidad} nombre={String(campo)} />} cursor={{ stroke: "var(--texto-3)", strokeWidth: 1 }} />
        <Line
          type="monotone" dataKey="v" stroke={color} strokeWidth={2}
          dot={false} isAnimationActive={false} connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
