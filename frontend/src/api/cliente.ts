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

/** POST con cabeceras extra y cuerpo JSON o binario (audio). El motivo de un
 *  error viene en `detail`, igual que en `enviarImagen`. */
export async function enviar<T>(ruta: string, cuerpo: Blob | object, cabeceras: Record<string, string> = {}): Promise<T> {
  const binario = cuerpo instanceof Blob;
  const r = await fetch(`/api/v1${ruta}`, {
    method: "POST",
    headers: {
      // Sin los parámetros (";codecs=opus"): el backend valida el tipo a secas.
      "Content-Type": binario ? (cuerpo.type.split(";")[0] || "audio/webm") : "application/json",
      Accept: "application/json",
      ...cabeceras,
    },
    body: binario ? cuerpo : JSON.stringify(cuerpo),
  });
  if (!r.ok) {
    const error = await r.json().catch(() => null);
    const detalle = typeof error?.detail === "string" ? error.detail : null;
    throw new ErrorApi(r.status, detalle ?? `La API respondió ${r.status}`);
  }
  return r.json() as Promise<T>;
}
