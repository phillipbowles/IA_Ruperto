import type { ReactNode } from "react";

export function Panel({ titulo, valor, nota, children }: {
  titulo: string; valor?: ReactNode; nota?: string; children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel__cab">
        <span className="panel__tit">{titulo}</span>
        {valor && <span className="panel__val">{valor}</span>}
      </div>
      {nota && <p className="panel__nota">{nota}</p>}
      <div className="panel__gr">{children}</div>
    </section>
  );
}

export function Kpi({ etiqueta, valor, unidad, pie, alerta }: {
  etiqueta: string; valor: ReactNode; unidad?: string; pie?: string; alerta?: boolean;
}) {
  return (
    <div className={`kpi${alerta ? " kpi--alerta" : ""}`}>
      <span className="kpi__et">{etiqueta}</span>
      <span className="kpi__v">{valor}{unidad && <small>{unidad}</small>}</span>
      {pie && <span className="kpi__pie">{pie}</span>}
    </div>
  );
}
