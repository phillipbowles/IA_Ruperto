import type { Punto } from "../lib/analisis";
import { fechaHora, num } from "../lib/formato";

const C = (v: string | null) =>
  v === null ? <span className="vacio">—</span> : v;

export function TablaRegistros({ puntos, n = 25 }: { puntos: Punto[]; n?: number }) {
  const ultimos = [...puntos].slice(-n).reverse();
  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr>
            <th>Momento</th><th>#</th><th>Luz mV</th><th>Suelo %</th>
            <th>Suelo mV</th><th>T aire</th><th>HR</th><th>T NTC</th>
            <th>RSSI</th><th style={{ textAlign: "left" }}>Estado</th>
          </tr>
        </thead>
        <tbody>
          {ultimos.map((p) => (
            <tr key={p.id}>
              <td>{fechaHora(p.t)}</td>
              <td>{p.numero_muestra}</td>
              <td>{C(num(p.luz_mv, 0))}</td>
              <td>{C(num(p.suelo_pct_calc, 0))}</td>
              <td>{C(num(p.suelo_mv, 0))}</td>
              <td>{C(num(p.temperatura_c))}</td>
              <td>{C(num(p.humedad_ambiente_pct, 0))}</td>
              <td>{C(num(p.temp_ntc_c))}</td>
              <td>{C(num(p.wifi_rssi, 0))}</td>
              <td style={{ textAlign: "left" }}>
                {p.errores?.length
                  ? <span className="chip chip--alerta">{p.errores.length} aviso{p.errores.length > 1 ? "s" : ""}</span>
                  : <span className="vacio">ok</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
