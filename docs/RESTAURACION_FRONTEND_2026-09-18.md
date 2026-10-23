# Restauración del frontend — 18 de septiembre de 2026

Se restauró en Railway el dashboard con gráficas que estaba activo antes del
17 de septiembre. Las horas de este documento corresponden a Montevideo (UTC−3).

## Qué ocurrió

- **13/09, 19:00:** se publicó por CLI `Feat: dashboard con graficos`, despliegue
  `3d4854e0-1a2d-4170-bfc4-81aef28741f1`. Su fuente no aparece en el historial,
  reflog ni objetos recuperables de este repositorio.
- **17/09, 18:57–18:58:** los commits `331af12` y `438e840` quitaron la tarjeta
  de temperatura NTC y sus campos del tipo `Medicion` en el frontend básico.
- **17/09, 18:58:** el despliegue desde GitHub `4b54876c-0c33-4585-a97e-a3f0ac87592a`
  reemplazó el dashboard publicado por CLI por el frontend básico del repositorio.
- **17/09, 19:03:** `c75cc8a` revirtió la eliminación de NTC. Esto no recuperó
  las gráficas, porque no estaban en Git.
- **17/09, 19:09–19:32:** hubo varios despliegues y reintentos. A las 19:20 se
  reconstruyó temporalmente el dashboard por CLI; luego se volvió a publicar
  el frontend básico desde GitHub. El último commit, `3e66216`, es vacío y solo
  disparó otro despliegue.

Los árboles `HEAD:frontend`, `dc8984f:frontend`, `9bf73e6:frontend` y
`c75cc8a:frontend` son idénticos:
`e8c54eba5d733529de59d1fbba763c0d65018a58`.
Por eso revertir el commit vacío o restaurar archivos desde el 12/09 no
recuperaba el dashboard.

## Restauración realizada

- Proyecto: `IA-Ruperto`; entorno: `production`; servicio: `Frontend`.
- Operación: `deploymentRollback` del despliegue del 13/09.
- Nuevo despliegue: `6e9bfd2b-e57e-4dc6-bb5d-4e049d2ec7d4`.
- Estado verificado: `SUCCESS`, instancia `RUNNING`.
- Imagen restaurada, idéntica a la del 13/09:
  `sha256:e7f6ec651824c63e584f7805940ca1018e585d36619aba146fcd83603f2f6474`.
- URL: https://frontend-production-a3ff.up.railway.app/

La operación afectó solo al servicio Frontend. No se modificaron el backend,
el firmware ni la base de datos.

## Verificación

- HTML, JavaScript y CSS publicados responden correctamente por HTTP.
- El JavaScript restaurado incluye Recharts, cuatro series temporales (luz,
  suelo, temperatura y humedad del aire), distribuciones de etiquetas y avisos,
  cobertura por hora y comparación de termómetros; filtros de 24 h, 7 días y Todo.
- La consulta real del dashboard, `GET /api/v1/mediciones?limit=20000`, devuelve
  3.011 mediciones con los campos usados por las gráficas.
- `GET /api/v1/mediciones/ultima` responde correctamente. La última medición
  disponible tiene fecha de servidor `2026-09-17T18:59:11.388663Z`.
- El backend conserva su despliegue anterior y sigue en `SUCCESS`/`RUNNING`.
- No se pudo realizar una comprobación visual: no había navegador conectado
  disponible para la herramienta de UI. Se verificaron el artefacto exacto y la API.

## Copia recuperada y limitación de Git

`outputs/frontend-recuperado-2026-09-13.zip` contiene el HTML, JavaScript y CSS
publicados, junto con sus sumas SHA-256. Es una copia del build compilado, no
del código fuente TypeScript/React. No contiene mediciones ni credenciales.

La restauración de producción no cambia `frontend/src`: las fuentes originales
del dashboard siguen ausentes del repositorio. Un futuro despliegue de este
frontend desde GitHub volvería a publicar el panel básico. Antes de hacerlo,
hay que recuperar e incorporar la fuente original del dashboard. No se cambió
la configuración de despliegues automáticos.

Railway permite restaurar la imagen y variables de un despliegue anterior,
pero no encontré una opción pública de CLI/API para exportar su archivo fuente.
Referencia: [acciones de despliegue de Railway](https://docs.railway.com/deployments/deployment-actions).
