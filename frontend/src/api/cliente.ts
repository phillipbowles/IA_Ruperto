/** Cliente HTTP. Usa rutas relativas: en dev las resuelve el proxy de Vite,
 *  en prod las resuelve nginx. Nunca una URL absoluta hardcodeada. */

export class ErrorApi extends Error {
  constructor(public readonly estado: number, mensaje: string) {
    super(mensaje);
  }
}

export async function obtener<T>(ruta: string): Promise<T> {
  const r = await fetch(`/api/v1${ruta}`, {
    headers: { Accept: "application/json" },
  });
  if (!r.ok) {
    throw new ErrorApi(
      r.status,
      r.status === 404 ? "Todavía no hay mediciones" : `La API respondió ${r.status}`,
    );
  }
  return r.json() as Promise<T>;
}
