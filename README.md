RetroBridge

Convierte cualquier teléfono celular en un receptor de mandos inalámbricos de ultra-baja latencia para tu PC.

RetroBridge es una herramienta de código abierto diseñada para la comunidad de emulación (RetroBat, RetroArch, etc.). Soluciona el problema común del input lag o las desconexiones que ocurren al conectar mandos directamente al Bluetooth de la PC. Utiliza tu teléfono móvil como un "puente" de alta velocidad, enviando las señales de los mandos hacia la PC a través de un cable USB (Anclaje de red) o Wi-Fi local.

Características

⚡ Cero Latencia (Modo Cable): Usa "Anclaje de red USB" en Android para lograr un tiempo de respuesta de < 1 ms.

🛜 Modo Inalámbrico: Funciona a través de tu red Wi-Fi local.

🚫 Sin Instalaciones en el Móvil: Funciona nativamente a través de una Web App local (HTML5 Gamepad API) desde tu navegador.

👥 Multijugador Real: Soporta la conexión de múltiples mandos simultáneos a uno o varios teléfonos.

🎮 Emulación Pura (DualShock 4): RetroBridge crea mandos virtuales a nivel de sistema operativo utilizando ViGEmBus.

Instalación:

Para Usuarios (Método Recomendado)

No necesitas instalar Python ni configurar entornos.

Ve a la pestaña de Releases en este repositorio.

Descarga el archivo retro_bridge.exe más reciente.

Ejecuta el archivo en tu PC.

Solo la primera vez que lo abras, si no tienes el driver de mandos virtuales en tu PC, el programa iniciará automáticamente el instalador de ViGEmBus.

Uso:

Haz doble clic en retro_bridge.exe en tu PC.

Conecta tu mando (PS4, Xbox, etc.) por Bluetooth a tu teléfono celular.

Conecta tu celular a la PC con un cable USB y activa el "Anclaje de red USB" (o asegúrate de que ambos estén en la misma red Wi-Fi).

En tu teléfono, abre el navegador web (Chrome/Safari) y entra a la dirección IP que te muestra la consola negra en la PC (Ej: http://192.168.1.50:8080).

Presiona un botón en el mando. ¡Tu PC lo detectará instantáneamente como un mando de PS4!

Soporte

Si encuentras algún error o tienes problemas para conectar tus mandos, por favor abre un Issue en la pestaña de Issues de GitHub proporcionando detalles sobre tu sistema operativo, el modelo de tu teléfono y el mando que estás utilizando.

Roadmap

[ ] Investigar la migración a VHF (Virtual HID Framework) para hacer el sistema a prueba de Anti-Cheats en juegos modernos.

[ ] Añadir soporte para vibración (Rumble) enviando la señal de vuelta al navegador.


Un agradecimiento gigantesco a Nefarius por el desarrollo y mantenimiento de la librería ViGEmBus, sin la cual este proyecto requeriría escribir un driver desde cero.

Gracias a las comunidades de r/Roms y RetroBat por la inspiración y el feedback.

Licencia

Este proyecto está licenciado bajo la Licencia MIT - consulta el archivo LICENSE en el repositorio para más detalles.

Estado del Proyecto

Activo y en desarrollo de su primera versión estable (v1.0.0).
