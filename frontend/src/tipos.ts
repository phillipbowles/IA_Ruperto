/** Las 3 clases del clasificador. `sin_etiquetar` NO es una clase: es ausencia
 *  de etiqueta y se excluye del entrenamiento (ver CLAUDE.md). */
export type Clase = "saludable" | "estresada" | "marchita";

export type EtiquetaOrigen = "manual" | "propagada" | "corregida" | "desconocido";

export interface Medicion {
  id: number;
  dispositivo: string;
  numero_muestra: number;
  boot_id: number | null;
  firmware_version: string | null;
  /** Hora NTP de la placa, en UTC. Null si todavía no sincronizó. */
  ts_dispositivo: string | null;
  /** Hora de llegada al servidor: incluye retardo de red y reintentos. */
  ts_servidor: string;
  temperatura_c: number | null;
  humedad_ambiente_pct: number | null;
  luz_raw: number | null;
  luz_mv: number | null;
  luz_pct: number | null;
  suelo_raw: number | null;
  suelo_mv: number | null;
  suelo_pct: number | null;
  termistor_raw: number | null;
  termistor_mv: number | null;
  temp_ntc_c: number | null;
  condicion_codigo: number | null;
  condicion_etiqueta: Clase | "sin_etiquetar" | null;
  etiqueta_origen: EtiquetaOrigen | null;
  wifi_rssi: number | null;
  errores: string[] | null;
  /** Salida del modelo de la placa (firmware 2.0.0+, tabla `predicciones`).
   *  Null si la placa no predijo: firmware viejo o sin DHT11 válido. */
  prediccion_etiqueta: Clase | null;
  prediccion_proba: number | null;
  modelo_version: string | null;
}

/** Respuesta de POST /api/v1/analisis-foto (backend/app/schemas.py, AnalisisFotoOut). */
export interface AnalisisFoto {
  es_planta: boolean;
  estado: Clase | null;
  puntaje: number | null;   // 0 = hojas caídas, 100 = turgente
  hojas: string;
  flores: string;
  explicacion: string;
  metodo: MetodoAnalisis;
  modelo: string;
  /** Sólo visión clásica: las mediciones que dan el puntaje. */
  metricas: Record<string, number> | null;
}

/** ia = Claude mira la foto; vision = segmentación por color y ángulo de las
 *  hojas (backend/app/vision.py), sin IA generativa. */
export type MetodoAnalisis = "ia" | "vision";
