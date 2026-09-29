# ESP32-CAM — guía para Manuel

Esta placa funciona de manera independiente. Una vez que el programa se carga
una sola vez, no necesita quedar conectada a una computadora: al recibir
corriente se conecta al Wi-Fi, toma una foto inmediatamente y la sube a
Railway. Después repite el proceso cada 5 minutos.

## Antes de empezar

- Placa: **AI-Thinker ESP32-CAM** con cámara OV2640.
- Alimentación: **5 V estables y al menos 1 A**. No alimentar la cámara desde
  el pin 3V3.
- En Arduino IDE instalar el paquete de placas **esp32 by Espressif Systems**.
- Seleccionar **Tools > Board > esp32 > AI Thinker ESP32-CAM**.
- Seleccionar **Upload Speed > 115200**.
- Las redes Wi-Fi y la dirección de Railway se guardan en `secrets.h`. Ese
  archivo es privado y no se sube a GitHub.

## Opción A: placa con base programadora ESP32-CAM-MB

1. Insertar la ESP32-CAM en la base, haciendo coincidir correctamente todos los
   pines.
2. Conectar la base a la computadora con un cable USB que transmita datos.
3. En Arduino IDE, abrir `firmware/camera/camera.ino`.
4. Elegir el puerto USB que aparece al conectar la placa.
5. Presionar **Upload**.
6. Si queda detenido en `Connecting...`, mantener presionado **IO0/BOOT**,
   pulsar brevemente **RST** y soltar **IO0/BOOT** cuando comience la carga.

## Opción B: placa sin base, usando adaptador USB-TTL

Con la alimentación desconectada, hacer este cableado:

| USB-TTL | ESP32-CAM |
| --- | --- |
| 5V | 5V |
| GND | GND |
| TX | U0R |
| RX | U0T |
| — | GPIO0 unido a GND solamente para programar |

Importante: TX y RX van cruzados. El adaptador debe entregar 5 V suficientes;
si no puede alimentar la placa de forma estable, usar una fuente externa de
5 V compartiendo el GND.

Luego:

1. Abrir `firmware/camera/camera.ino` en Arduino IDE.
2. Seleccionar **AI Thinker ESP32-CAM**, velocidad **115200** y el puerto del
   adaptador USB-TTL.
3. Presionar **Upload**.
4. Si queda en `Connecting...`, pulsar brevemente el botón **RST**.
5. Cuando Arduino IDE indique que terminó, desconectar la alimentación.
6. **Quitar el puente entre GPIO0 y GND.** Si queda colocado, la placa vuelve a
   entrar en modo programación y el programa no arranca.
7. Volver a alimentar la placa o pulsar **RST**.

## Primera prueba

1. Abrir el **Serial Monitor** de Arduino IDE a **115200 baud**.
2. Reiniciar la placa.
3. Verificar que informa conexión a una de las redes configuradas.
4. Esperar el mensaje de captura y una respuesta exitosa de Railway.
5. Comprobar la nueva foto en la web/API del proyecto.

Si al principio aparecen símbolos extraños, confirmar que el monitor está en
115200 baud y reiniciar la placa.

## Instalación definitiva

Después de comprobar que la primera foto llegó correctamente:

1. Desconectar la ESP32-CAM de la computadora.
2. Colocarla apuntando a la planta, evitando que encuadre personas, pantallas o
   documentos.
3. Conectarla a un cargador USB de **5 V y al menos 1 A**.
4. No hay que abrir Arduino IDE ni ejecutar nada más.

Cada vez que se enchufa, la placa hace automáticamente lo siguiente:

1. Busca las redes Wi-Fi conocidas y se conecta a una disponible.
2. Toma una foto inmediatamente.
3. La envía al backend alojado en Railway.
4. Espera 5 minutos y vuelve a tomar otra foto.
5. Si pierde Wi-Fi o falla un envío, espera y vuelve a intentarlo sin intervención
   manual.

## Qué revisar si no sube fotos

- Confirmar que la fuente sea de 5 V y al menos 1 A.
- Confirmar que GPIO0 **no** esté conectado a GND durante el uso normal.
- Revisar en el Monitor Serie, a 115200 baud, si se conectó al Wi-Fi y qué código
  HTTP devolvió Railway.
- Acercar la placa al punto de acceso: la ESP32-CAM solo usa Wi-Fi de 2.4 GHz.
- Si aparece un error de cámara o reinicios, revisar que el módulo OV2640 esté
  bien insertado y que la alimentación sea estable.

## Desarrollo opcional con PlatformIO

Desde `firmware/camera` se puede compilar y cargar con:

```bash
cp include/secrets.example.h include/secrets.h
# completar include/secrets.h sin publicar las contraseñas
pio run
pio run -t upload
pio device monitor
```
