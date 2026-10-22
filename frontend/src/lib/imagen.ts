/** Preparación de fotos antes de mandarlas al backend. */

// Lado mayor con el que se manda la foto: más resolución no mejora el
// diagnóstico y una foto de celular sin achicar pasa los 5 MB.
const LADO_MAX = 1568;

export async function achicar(archivo: File): Promise<Blob> {
  const bmp = await createImageBitmap(archivo);
  const k = Math.min(1, LADO_MAX / Math.max(bmp.width, bmp.height));
  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(bmp.width * k);
  lienzo.height = Math.round(bmp.height * k);
  lienzo.getContext("2d")!.drawImage(bmp, 0, 0, lienzo.width, lienzo.height);
  bmp.close();
  return new Promise((ok, mal) =>
    lienzo.toBlob((b) => (b ? ok(b) : mal(new Error("No se pudo leer la imagen"))), "image/jpeg", 0.85));
}
