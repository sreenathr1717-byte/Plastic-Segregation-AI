"""
Raspberry Pi Relay Server
Receives arm commands from laptop over WiFi (TCP) and forwards to ESP8266 via USB serial.

Run on Raspberry Pi:
    python3 rpi_relay.py
    python3 rpi_relay.py --port /dev/ttyUSB0 --listen-port 5000
"""

import socket
import threading
import time
import argparse
import serial


class RelayServer:
    def __init__(self, serial_port, baudrate, listen_port):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.listen_port = listen_port
        self.ser = None
        self.running = False

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=2)
            time.sleep(2)
            response = self.ser.readline().decode().strip()
            print(f"[Serial] Connected to ESP8266: {response}")
            return True
        except serial.SerialException as e:
            print(f"[Serial] Failed: {e}")
            print(f"[Serial] Check: ls /dev/ttyUSB* or ls /dev/ttyACM*")
            return False

    def handle_client(self, conn, addr):
        print(f"[TCP] Laptop connected: {addr}")
        conn.settimeout(30)

        try:
            while self.running:
                data = conn.recv(1024)
                if not data:
                    break

                cmd = data.decode().strip()
                if not cmd:
                    continue

                print(f"[TCP] <- {cmd}")

                if self.ser and self.ser.is_open:
                    self.ser.write(f"{cmd}\n".encode())
                    time.sleep(0.05)

                    response = ""
                    if self.ser.in_waiting:
                        response = self.ser.readline().decode().strip()

                    print(f"[Serial] -> {response}")
                    conn.sendall(f"{response}\n".encode())
                else:
                    conn.sendall(b"ERR_NO_SERIAL\n")

        except socket.timeout:
            print(f"[TCP] Client timeout: {addr}")
        except ConnectionResetError:
            print(f"[TCP] Client disconnected: {addr}")
        except Exception as e:
            print(f"[TCP] Error: {e}")
        finally:
            conn.close()
            print(f"[TCP] Connection closed: {addr}")

    def start(self):
        if not self.connect_serial():
            print("[Relay] Cannot start without serial connection to ESP8266.")
            print("[Relay] Make sure ESP8266 is plugged into RPi USB port.")
            return

        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.listen_port))
        server.listen(1)
        server.settimeout(1)

        print(f"\n{'=' * 50}")
        print(f"  RELAY SERVER RUNNING")
        print(f"  Listening on port {self.listen_port}")
        print(f"  Serial: {self.serial_port} @ {self.baudrate}")
        print(f"{'=' * 50}")
        print(f"  On laptop, set RPi IP in config.py")
        print(f"  Then run: python main.py")
        print(f"{'=' * 50}\n")

        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                    t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n[Relay] Shutting down...")
        finally:
            self.running = False
            server.close()
            if self.ser and self.ser.is_open:
                self.ser.write(b"H\n")
                time.sleep(0.5)
                self.ser.close()
            print("[Relay] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPi relay: WiFi -> Serial bridge")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="ESP8266 serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--listen-port", type=int, default=5000, help="TCP port to listen on")
    args = parser.parse_args()

    relay = RelayServer(args.port, args.baudrate, args.listen_port)
    relay.start()
