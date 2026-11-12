"""
6-DOF Robotic arm controller.

Two modes:
  - NetworkArm: Laptop -> RPi (TCP/WiFi) -> ESP8266 (serial) -> PCA9685
  - ArmController: Direct serial (for testing without RPi)

Serial protocol:
  B/W/S/E/R/G + angle  (Base/Waist/Shoulder/Elbow/wRist/Gripper)
  H = Home, T = Test sweep
"""

import time
import socket
import serial
import config


class NetworkArm:
    """Sends commands to RPi relay server over WiFi/TCP."""

    def __init__(self, host=None, port=None):
        self.host = host or config.RPI_HOST
        self.port = port or config.RPI_PORT
        self.sock = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            print(f"[Arm] Connected to RPi at {self.host}:{self.port}")
            return True
        except (socket.error, socket.timeout) as e:
            print(f"[Arm] Cannot reach RPi at {self.host}:{self.port}: {e}")
            print("[Arm] Make sure rpi_relay.py is running on the Pi.")
            return False

    def send_command(self, cmd):
        if self.sock:
            try:
                self.sock.sendall(f"{cmd}\n".encode())
                time.sleep(0.05)
                response = self.sock.recv(1024).decode().strip()
                if response:
                    print(f"[Arm] {cmd} -> {response}")
                return response
            except socket.error as e:
                print(f"[Arm] Send failed: {e}")
                return None
        print("[Arm] Not connected!")
        return None

    def move_servo(self, name, angle):
        angle = max(0, min(180, int(angle)))
        cmd_char = config.SERVO_CMDS.get(name)
        if cmd_char:
            self.send_command(f"{cmd_char}{angle}")
            time.sleep(config.MOVE_DELAY)

    def home(self):
        print("[Arm] Moving to HOME")
        self.send_command("H")
        time.sleep(1.5)

    def test(self):
        print("[Arm] Running test sweep...")
        self.send_command("T")
        time.sleep(8)

    def open_gripper(self):
        self.move_servo("gripper", config.GRIPPER_OPEN)

    def close_gripper(self):
        self.move_servo("gripper", config.GRIPPER_CLOSED)
        time.sleep(config.GRAB_DELAY)

    def move_to_position(self, position):
        for name in ["base", "waist", "shoulder", "elbow", "wrist"]:
            if name in position:
                self.move_servo(name, position[name])

    def pick_and_place(self, pickup_pos=None, drop_pos=None):
        pickup = pickup_pos or config.ARM_PICKUP
        drop = drop_pos or config.ARM_DROP

        print("[Arm] === PICK AND PLACE ===")

        self.open_gripper()
        print("[Arm] -> PICKUP (X direction)")
        self.move_to_position(pickup)
        time.sleep(0.5)

        self.close_gripper()
        print("[Arm] Grabbed!")

        self.move_servo("shoulder", config.ARM_HOME["shoulder"])
        self.move_servo("elbow", config.ARM_HOME["elbow"])
        time.sleep(0.3)

        print("[Arm] -> DROP (Y direction)")
        self.move_to_position(drop)
        time.sleep(0.5)

        self.open_gripper()
        print("[Arm] Released!")
        time.sleep(0.3)

        self.home()
        print("[Arm] === DONE ===")

    def pick_and_place_mapped(self, norm_x, norm_y):
        pickup_base = int(30 + norm_x * 120)
        pickup = dict(config.ARM_PICKUP)
        pickup["base"] = pickup_base
        self.pick_and_place(pickup_pos=pickup)

    def disconnect(self):
        if self.sock:
            try:
                self.send_command("H")
                time.sleep(0.5)
                self.sock.close()
            except Exception:
                pass
            print("[Arm] Disconnected from RPi")


class ArmController:
    """Direct serial connection (for testing without RPi)."""

    def __init__(self, port=None, baudrate=None):
        self.port = port or config.SERIAL_PORT
        self.baudrate = baudrate or config.SERIAL_BAUDRATE
        self.serial = None

    def connect(self):
        try:
            self.serial = serial.Serial(
                self.port, self.baudrate, timeout=config.SERIAL_TIMEOUT,
            )
            time.sleep(2)
            response = self.serial.readline().decode().strip()
            print(f"[Arm] Connected on {self.port}: {response}")
            return "ARM_READY" in response or True
        except serial.SerialException as e:
            print(f"[Arm] Connection failed: {e}")
            return False

    def send_command(self, cmd):
        if self.serial and self.serial.is_open:
            self.serial.write(f"{cmd}\n".encode())
            time.sleep(0.05)
            response = self.serial.readline().decode().strip()
            if response:
                print(f"[Arm] {cmd} -> {response}")
            return response
        print("[Arm] Not connected!")
        return None

    def move_servo(self, name, angle):
        angle = max(0, min(180, int(angle)))
        cmd_char = config.SERVO_CMDS.get(name)
        if cmd_char:
            self.send_command(f"{cmd_char}{angle}")
            time.sleep(config.MOVE_DELAY)

    def home(self):
        print("[Arm] Moving to HOME")
        self.send_command("H")
        time.sleep(1.5)

    def test(self):
        print("[Arm] Running test sweep...")
        self.send_command("T")
        time.sleep(8)

    def open_gripper(self):
        self.move_servo("gripper", config.GRIPPER_OPEN)

    def close_gripper(self):
        self.move_servo("gripper", config.GRIPPER_CLOSED)
        time.sleep(config.GRAB_DELAY)

    def move_to_position(self, position):
        for name in ["base", "waist", "shoulder", "elbow", "wrist"]:
            if name in position:
                self.move_servo(name, position[name])

    def pick_and_place(self, pickup_pos=None, drop_pos=None):
        pickup = pickup_pos or config.ARM_PICKUP
        drop = drop_pos or config.ARM_DROP

        print("[Arm] === PICK AND PLACE ===")

        self.open_gripper()
        print("[Arm] -> PICKUP (X direction)")
        self.move_to_position(pickup)
        time.sleep(0.5)

        self.close_gripper()
        print("[Arm] Grabbed!")

        self.move_servo("shoulder", config.ARM_HOME["shoulder"])
        self.move_servo("elbow", config.ARM_HOME["elbow"])
        time.sleep(0.3)

        print("[Arm] -> DROP (Y direction)")
        self.move_to_position(drop)
        time.sleep(0.5)

        self.open_gripper()
        print("[Arm] Released!")
        time.sleep(0.3)

        self.home()
        print("[Arm] === DONE ===")

    def pick_and_place_mapped(self, norm_x, norm_y):
        pickup_base = int(30 + norm_x * 120)
        pickup = dict(config.ARM_PICKUP)
        pickup["base"] = pickup_base
        self.pick_and_place(pickup_pos=pickup)

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.home()
            self.serial.close()
            print("[Arm] Disconnected")


class SimulatedArm(NetworkArm):
    """Simulated arm for testing without hardware."""

    def connect(self):
        print("[SimArm] Simulated arm connected (6-DOF)")
        return True

    def send_command(self, cmd):
        print(f"[SimArm] >> {cmd}")
        return "OK"

    def disconnect(self):
        print("[SimArm] Disconnected")
