import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import type { Punto } from "../lib/analisis";

/** Cruce de los dos sensores de temperatura. Miden la misma habitación, así que
 *  los puntos deberían caer sobre la diagonal. Cuánto se despegan de ella es la
 *  forma más rápida de ver si el termistor está bien calibrado. */
export function DispersionTemp({ puntos }: { puntos: Punto[] }) {
  const datos = puntos
    .filter((p) => p.temperatura_c !== null && p.temp_ntc_c !== null)
    .map((p) => ({ dht: p.temperatura_c as number, ntc: p.temp_ntc_c as number }));

  if (!datos.length) return <p className="vacio">Sin pares de temperatura.</p>;

  const lo = Math.floor(Math.min(...datos.map((d) => Math.min(d.dht, d.ntc))) - 2);
  const hi = Math.ceil(Math.max(...datos.map((d) => Math.max(d.dht, d.ntc))) + 2);

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ScatterChart margin={{ top: 8, right: 14, left: 4, bottom: 8 }}>
        <CartesianGrid stroke="var(--grid)" />
        <XAxis type="number" dataKey="dht" domain={[lo, hi]} name="DHT11"
               stroke="var(--texto-3)" fontSize={11} tickLine={false}
               axisLine={{ stroke: "var(--grid)" }}
               label={{ value: "DHT11 (°C)", position: "insideBottom", offset: -2,
                        fill: "var(--texto-3)", fontSize: 11 }} />
        <YAxis type="number" dataKey="ntc" domain={[lo, hi]} name="Termistor"
               stroke="var(--texto-3)" fontSize={11} tickLine={false} axisLine={false} width={52}
               label={{ value: "NTC (°C)", angle: -90, position: "insideLeft",
                        fill: "var(--texto-3)", fontSize: 11 }} />
        {/* La diagonal: donde caerían los puntos si los dos coincidieran. */}
        <ReferenceLine segment={[{ x: lo, y: lo }, { x: hi, y: hi }]}
                       stroke="var(--texto-3)" strokeDasharray="4 4" />
        <Tooltip content={({ active, payload }: any) =>
          active && payload?.length ? (
            <div className="tt">
              <div className="tt__v">DHT <strong>{payload[0].payload.dht} °C</strong></div>
              <div className="tt__v">NTC <strong>{payload[0].payload.ntc} °C</strong></div>
            </div>
          ) : null} />
        <Scatter data={datos} fill="var(--serie-1)" fillOpacity={0.35}
                 isAnimationActive={false} shape="circle" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
