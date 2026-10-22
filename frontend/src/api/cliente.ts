/** Cliente HTTP. Usa rutas relativas: en dev las resuelve el proxy de Vite,
 *  en prod nginx. Nunca una URL absoluta hardcodeada. */

export class ErrorApi extends Error {
  constructor(public readonly estado: number, mensaje: string) {
    super(mensaje);
  }
}

export async function obtener<T>(ruta: string): Promise<T> {
  const r = await fetch(`/api/v1${ruta}`, { headers: { Accept: "application/json" } });
  if (!r.ok) {
    throw new ErrorApi(
      r.status,
      r.status === 404 ? "Todavía no hay mediciones" : `La API respondió ${r.status}`,
    );
  }
  return r.json() as Promise<T>;
}

export async function enviarImagen<T>(ruta: string, imagen: Blob): Promise<T> {
  const r = await fetch(`/api/v1${ruta}`, {
    method: "POST",
    headers: { "Content-Type": imagen.type, Accept: "application/json" },
    body: imagen,
  });
  if (!r.ok) {
    // El backend explica el motivo en `detail` (503 sin clave, 413, 429…).
    const cuerpo = await r.json().catch(() => null);
    throw new ErrorApi(r.status, cuerpo?.detail ?? `La API respondió ${r.status}`);
  }
  return r.json() as Promise<T>;
}
