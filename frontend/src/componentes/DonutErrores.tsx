import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";

/* Orden fijo del palette categórico validado: azul, naranja, aqua. El gris del
   "sin error" no es un slot: es el fondo contra el que se leen los otros. */
const COLORES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)"];
const GRIS = "var(--borde)";

const LEGIBLE: Record<string, string> = {
  luz_saturada: "Luz contra el riel del ADC",
  suelo_saturado: "Suelo contra el riel del ADC",
  hora_sin_sincronizar: "Reloj sin sincronizar (NTP)",
  dht_sin_respuesta: "DHT11 sin respuesta",
  ntc_fuera_de_rango: "Termistor fuera de rango",
};

export function DonutErrores({ errores, total }: {
  errores: { nombre: string; n: number }[]; total: number;
}) {
  // Solo los tres primeros llevan color: más slots no pasan el umbral de
  // separación para daltonismo en una forma donde todas las porciones se
  // comparan contra todas. El resto se pliega en "otros".
  const top = errores.slice(0, 3);
  const otros = errores.slice(3).reduce((s, e) => s + e.n, 0);
  const conError = errores.reduce((s, e) => s + e.n, 0);

  const datos = [
    ...top.map((e, i) => ({ ...e, color: COLORES[i] })),
    ...(otros ? [{ nombre: "otros", n: otros, color: "var(--serie-4)" }] : []),
    { nombre: "sin error", n: Math.max(0, total - conError), color: GRIS },
  ].filter((d) => d.n > 0);

  if (!total) return <p className="vacio">Sin datos.</p>;

  return (
    <>
      <ResponsiveContainer width="100%" height={170}>
        <PieChart>
          <Pie
            data={datos} dataKey="n" nameKey="nombre"
            cx="50%" cy="50%" innerRadius={48} outerRadius={72}
            paddingAngle={2} stroke="var(--panel)" strokeWidth={2}
            isAnimationActive={false}
          >
            {datos.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Pie>
          <Tooltip
            content={({ active, payload }: any) =>
              active && payload?.length ? (
                <div className="tt">
                  <div className="tt__t">{LEGIBLE[payload[0].name] ?? payload[0].name}</div>
                  <div className="tt__v">
                    <strong>{payload[0].value}</strong> muestras ·{" "}
                    {((payload[0].value / total) * 100).toFixed(1)} %
                  </div>
                </div>
              ) : null
            }
          />
        </PieChart>
      </ResponsiveContainer>
      {/* Etiquetas visibles al lado del color: la identidad nunca queda solo en
          el tono — hace falta para daltonismo y para impresión en gris. */}
      <ul className="leyenda">
        {datos.map((d) => (
          <li key={d.nombre}>
            <i style={{ background: d.color }} />
            <span>{LEGIBLE[d.nombre] ?? d.nombre}</span>
            <b>{d.n} · {((d.n / total) * 100).toFixed(1)} %</b>
          </li>
        ))}
      </ul>
    </>
  );
}
