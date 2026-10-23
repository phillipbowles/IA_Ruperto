import type { Clase } from "../tipos";

/** El árbol que corre en la placa, para dibujarlo en el panel.
 *
 *  Copia de firmware/lib/plantaia_ml/modelo_plantaia.h, que es GENERADO por
 *  ml/plantaia_ml/exportar_c.py: si se reentrena el modelo hay que actualizar
 *  esto a mano. El panel avisa cuando la placa reporta otra `modelo_version`. */

export const VERSION_ARBOL = "arbol-p2-f012-58e644";

export const CORTE_TEMP_C = 10.25;     // nodo raíz: temp_c ≤ 10,25 → marchita
export const CORTE_SUELO_MV = 1821.5;  // segundo nodo: suelo_mv ≤ 1821,5 → saludable

/** Proporciones de cada hoja (saludable, estresada, marchita), con
 *  class_weight="balanced", tal como están en el header. */
export const HOJAS: Record<"frio" | "humedo" | "seco", { clase: Clase; proba: [number, number, number] }> = {
  frio:   { clase: "marchita",  proba: [0.0, 0.0, 1.0] },
  humedo: { clase: "saludable", proba: [0.448, 0.279, 0.273] },
  seco:   { clase: "estresada", proba: [0.03, 0.97, 0.0] },
};

export type Hoja = keyof typeof HOJAS;

/** Por qué hoja cae una medición; null si falta un dato que el árbol mira. */
export function recorrido(temp_c: number | null, suelo_mv: number | null): Hoja | null {
  if (temp_c === null) return null;
  if (temp_c <= CORTE_TEMP_C) return "frio";
  if (suelo_mv === null) return null;
  return suelo_mv <= CORTE_SUELO_MV ? "humedo" : "seco";
}
