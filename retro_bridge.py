import asyncio
import websockets
import json
import threading
import socket
import os
import sys
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

# Intentamos importar las librerías críticas
try:
    import vgamepad as vg
    import qrcode
except ImportError:
    print("Error: Faltan librerías. Si eres desarrollador ejecuta: pip install vgamepad qrcode websockets")
    input("Presiona ENTER para salir...")
    exit()

# ==============================================================================
# CÓDIGO DE LA APP MÓVIL (HTML + Javascript)
# ==============================================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>RetroBridge Gamepad</title>
    <style>
        body { background-color: #0f172a; color: #38bdf8; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; height: 100vh; margin: 0; overflow: hidden; text-align: center; }
        h1 { font-size: 2rem; margin-top: 20px; margin-bottom: 5px; }
        .status { padding: 10px 20px; border-radius: 50px; font-weight: bold; margin-top: 10px; transition: 0.3s; }
        .disconnected { background: #7f1d1d; color: #fca5a5; }
        .connected { background: #14532d; color: #86efac; }
        .btn-fs { margin-top: 15px; padding: 10px 20px; background: #0284c7; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .btn-fs:active { background: #0369a1; transform: translateY(2px); }
        .gamepads-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 20px; width: 100%; max-height: 50vh; overflow-y: auto; }
        .gamepad-box { padding: 15px; border: 2px dashed #38bdf8; border-radius: 15px; min-width: 250px; background: #1e293b; }
        .gamepad-box h3 { margin: 0 0 10px 0; color: #f8fafc; font-size: 1.1rem; }
        .hint { color: #94a3b8; font-size: 0.9rem; margin-top: auto; margin-bottom: 20px; padding: 0 20px; }
    </style>
</head>
<body>
    <h1>🎮 RetroBridge</h1>
    <p>Receptor de Baja Latencia</p>
    
    <div id="statusIndicator" class="status disconnected">Buscando PC...</div>
    
    <button class="btn-fs" onclick="toggleFullScreen()">📺 Pantalla Completa</button>
    
    <div id="gamepadsContainer" class="gamepads-container">
        <p>Empareja uno o más mandos Bluetooth y pulsa un botón.</p>
    </div>

    <p class="hint">Mantén la pantalla encendida mientras juegas y evita bloquear el teléfono.</p>

    <script>
        let ws;
        let lastState = "";
        const wsUrl = "ws://WS_HOST_IP:8765";
        const statusEl = document.getElementById('statusIndicator');
        const containerEl = document.getElementById('gamepadsContainer');

        function toggleFullScreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.log(`Error intentando entrar en pantalla completa: ${err.message}`);
                });
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        }

        function connect() {
            ws = new WebSocket(wsUrl);
            ws.onopen = () => { statusEl.className = 'status connected'; statusEl.innerText = '✅ Conectado a la PC'; };
            ws.onclose = () => { statusEl.className = 'status disconnected'; statusEl.innerText = '❌ Desconectado. Reintentando...'; setTimeout(connect, 2000); };
        }
        connect();

        function updateGamepad() {
            const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
            const activeGamepads = [];
            let htmlContent = "";

            for (let i = 0; i < gamepads.length; i++) {
                const gp = gamepads[i];
                if (gp) {
                    activeGamepads.push({
                        id: gp.index,
                        b: gp.buttons.map(btn => btn.value),
                        a: gp.axes.map(axis => axis)
                    });
                    
                    htmlContent += `
                        <div class="gamepad-box">
                            <h3>🎮 Jugador ${activeGamepads.length}</h3>
                            <small>${gp.id.substring(0, 25)}...</small>
                        </div>
                    `;
                }
            }

            if (activeGamepads.length > 0) {
                if (containerEl.innerHTML !== htmlContent) containerEl.innerHTML = htmlContent;
            } else {
                containerEl.innerHTML = "<p>Esperando mandos... toca un botón en cualquiera de ellos.</p>";
            }
            
            if (ws && ws.readyState === WebSocket.OPEN && activeGamepads.length > 0) {
                const stateStr = JSON.stringify(activeGamepads);
                if (stateStr !== lastState) {
                    ws.send(stateStr);
                    lastState = stateStr;
                }
            }
            
            requestAnimationFrame(updateGamepad);
        }
        
        requestAnimationFrame(updateGamepad);
    </script>
</body>
</html>
"""

# ==============================================================================
# LÓGICA DEL SERVIDOR WEB Y WEBSOCKET (PYTHON)
# ==============================================================================

def get_local_ip():
    """Descubre la IP local de la PC en la red (o el túnel USB)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        host = self.headers.get('Host').split(':')[0]
        html = HTML_PAGE.replace('WS_HOST_IP', host)
        self.wfile.write(html.encode('utf-8'))
        
    def log_message(self, format, *args):
        pass

def run_http_server(ip, port):
    server = HTTPServer(('0.0.0.0', port), AppHandler)
    server.serve_forever()

# Variables globales
connected_clients = {}

async def ws_handler(websocket):
    print(f"\n[+] DISPOSITIVO CONECTADO (IP: {websocket.remote_address[0]})")
    connected_clients[websocket] = {}
    try:
        async for message in websocket:
            data = json.loads(message)
            for gp_data in data:
                process_inputs(websocket, gp_data)
    except websockets.exceptions.ConnectionClosed:
        print(f"[-] Dispositivo desconectado (IP: {websocket.remote_address[0]}).")
    finally:
        if websocket in connected_clients:
            del connected_clients[websocket]

def process_inputs(ws, gp_data):
    """Traduce el JSON de la app web a comandos del driver de PS4"""
    gp_id = gp_data.get('id', 0)
    
    if gp_id not in connected_clients[ws]:
        try:
            connected_clients[ws][gp_id] = vg.VDS4Gamepad()
            print(f"[🎮] Nuevo mando detectado! Asignado al Jugador {len(connected_clients[ws])}")
        except Exception as e:
            print(f"Error creando mando: {e}")
            return

    gamepad = connected_clients[ws][gp_id]
    buttons = gp_data.get('b', [])
    axes = gp_data.get('a', [])
    
    def is_pressed(val): return float(val) > 0.5

    if len(buttons) >= 16:
        if is_pressed(buttons[0]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)

        if is_pressed(buttons[1]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)

        if is_pressed(buttons[2]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)

        if is_pressed(buttons[3]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)

        if is_pressed(buttons[4]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)

        if is_pressed(buttons[5]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)

        gamepad.left_trigger_float(value_float=float(buttons[6]))
        gamepad.right_trigger_float(value_float=float(buttons[7]))

        if is_pressed(buttons[8]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)

        if is_pressed(buttons[9]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)

        if is_pressed(buttons[10]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)

        if is_pressed(buttons[11]): gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
        else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)

        up = is_pressed(buttons[12])
        down = is_pressed(buttons[13])
        left = is_pressed(buttons[14])
        right = is_pressed(buttons[15])
        
        dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
        if up and right: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
        elif up and left: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
        elif down and right: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
        elif down and left: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
        elif up: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
        elif down: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
        elif left: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
        elif right: dpad_val = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
        
        gamepad.directional_pad(direction=dpad_val)
        
        if len(buttons) > 16:
            if is_pressed(buttons[16]): gamepad.press_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)
            else: gamepad.release_special_button(special_button=vg.DS4_SPECIAL_BUTTONS.DS4_SPECIAL_BUTTON_PS)

    if len(axes) >= 4:
        gamepad.left_joystick_float(x_value_float=float(axes[0]), y_value_float=-float(axes[1]))
        gamepad.right_joystick_float(x_value_float=float(axes[2]), y_value_float=-float(axes[3]))

    gamepad.update()

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("===================================================")
    print("          🎮 RETROBRIDGE MULTIJUGADOR 🎮          ")
    print("===================================================")
    
    # 1. Verificación e Instalación Automática del Driver
    try:
        _test_gamepad = vg.VDS4Gamepad()
        del _test_gamepad
        print("[OK] Driver detectado. Mando virtual listo.")
    except Exception as e:
        print(f"\n[AVISO] No se detectó el driver necesario en esta PC.")
        print("Buscando el instalador incluido...")
        installer_path = get_resource_path("ViGEmBus_Setup.exe")
        
        if os.path.exists(installer_path):
            print("\n[!] Iniciando instalación automática de ViGEmBus...")
            print("[!] Por favor, acepta los permisos de instalación (Siguiente > Siguiente).")
            try:
                subprocess.run([installer_path], check=True)
                print("\n[+] Instalación completada con éxito.")
                print("[!] IMPORTANTE: Por favor, CIERRA ESTA VENTANA Y VUELVE A ABRIRLA.")
            except Exception as inst_e:
                print(f"\n[-] La instalación fue cancelada o falló: {inst_e}")
        else:
            print("----> NO SE ENCONTRÓ EL INSTALADOR EMPAQUETADO.")
            print("----> Descárgalo desde: https://github.com/nefarius/ViGEmBus/releases")
        
        input("\nPresiona ENTER para salir...")
        return

    # 2. Configuración de Red
    local_ip = get_local_ip()
    http_port = 8080
    ws_port = 8765
    url = f"http://{local_ip}:{http_port}"

    # 3. Mostrar Código QR
    print("\n" + "="*50)
    print(" 📱 ¡CONEXIÓN RÁPIDA DETECTADA!")
    print(" Apunta la cámara de tu celular a este código:")
    print("="*50 + "\n")

    try:
        # Generamos el QR para la terminal
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        # invert=True suele verse mejor en las consolas negras de Windows
        qr.print_ascii(invert=True) 
    except Exception as e:
        print("[!] No se pudo generar el código QR visual.")

    print(f"\n 🌐 O entra manualmente en el navegador a: \n    {url}")
    print("="*50 + "\n")

    # 4. Iniciar Servidores
    threading.Thread(target=run_http_server, args=(local_ip, http_port), daemon=True).start()
    print(f"[*] Esperando conexiones... (Puedes minimizar esta ventana)")

    async with websockets.serve(ws_handler, "0.0.0.0", ws_port):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaliendo y apagando mandos virtuales...")
