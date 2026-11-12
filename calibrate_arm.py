"""
6-DOF Servo Calibration Tool
Test each servo and find the right angles for pickup and drop positions.

Usage:
    python calibrate_arm.py                     # Real arm
    python calibrate_arm.py --port /dev/ttyUSB0 # Specify port
    python calibrate_arm.py --simulate          # No Arduino

Commands:
    b <angle>  - Move base (0-180)
    w <angle>  - Move waist (0-180)
    s <angle>  - Move shoulder (0-180)
    e <angle>  - Move elbow (0-180)
    r <angle>  - Move wrist (0-180)
    g <angle>  - Move gripper (0-180)
    h          - Home all servos
    t          - Test sweep all servos
    save pickup  - Save current position as pickup
    save drop    - Save current position as drop
    show         - Show all saved positions
    done         - Print config.py values and exit
"""

import sys
import time
import serial


def connect(port, baudrate=115200):
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(2)
        response = ser.readline().decode().strip()
        print(f"Connected: {response}")
        return ser
    except serial.SerialException as e:
        print(f"Connection failed: {e}")
        return None


def send(ser, cmd):
    if ser:
        ser.write(f"{cmd}\n".encode())
        time.sleep(0.05)
        resp = ser.readline().decode().strip()
        if resp:
            print(f"  -> {resp}")
        return resp
    print(f"  [SIM] {cmd}")
    return "OK"


def main():
    port = "/dev/ttyUSB0"
    simulate = False

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--port" and i + 1 < len(sys.argv) - 1:
            port = sys.argv[i + 2]
        if arg == "--simulate":
            simulate = True

    ser = None
    if not simulate:
        ser = connect(port)
        if not ser:
            print("Could not connect. Use --simulate to test without hardware.")
            print("Common ports: /dev/ttyUSB0, /dev/ttyACM0, COM3")
            return
    else:
        print("[Simulation mode]")

    current = {
        "base": 90, "waist": 90, "shoulder": 90,
        "elbow": 90, "wrist": 90, "gripper": 60,
    }
    saved = {"pickup": None, "drop": None, "gripper_open": 60, "gripper_closed": 160}

    servo_map = {"b": "base", "w": "waist", "s": "shoulder",
                 "e": "elbow", "r": "wrist", "g": "gripper"}
    cmd_map = {"b": "B", "w": "W", "s": "S", "e": "E", "r": "R", "g": "G"}

    print("\n" + "=" * 55)
    print("  6-DOF SERVO CALIBRATION")
    print("=" * 55)
    print("Servos: b(ase) w(aist) s(houlder) e(lbow) w(r)ist g(ripper)")
    print("Commands: <servo> <angle>, h, t, save pickup/drop, show, done")
    print(f"Current: {current}\n")

    while True:
        try:
            user_input = input(">> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        parts = user_input.split()
        cmd = parts[0]

        if cmd == "done":
            break

        elif cmd == "h":
            send(ser, "H")
            current = {
                "base": 90, "waist": 90, "shoulder": 90,
                "elbow": 90, "wrist": 90, "gripper": 60,
            }
            print(f"  Home: {current}")

        elif cmd == "t":
            print("  Testing all servos...")
            send(ser, "T")
            time.sleep(8)
            while ser and ser.in_waiting:
                print(f"  {ser.readline().decode().strip()}")

        elif cmd in servo_map and len(parts) == 2:
            try:
                angle = int(parts[1])
                angle = max(0, min(180, angle))
                send(ser, f"{cmd_map[cmd]}{angle}")
                current[servo_map[cmd]] = angle
                print(f"  {servo_map[cmd]} = {angle}")
            except ValueError:
                print("  Invalid angle. Example: b 90")

        elif cmd == "save" and len(parts) == 2:
            if parts[1] == "pickup":
                saved["pickup"] = dict(current)
                print(f"  PICKUP saved: {saved['pickup']}")
            elif parts[1] == "drop":
                saved["drop"] = dict(current)
                print(f"  DROP saved: {saved['drop']}")
            else:
                print("  Use: save pickup, save drop")

        elif cmd == "show":
            print(f"  Current:     {current}")
            print(f"  Pickup:      {saved['pickup']}")
            print(f"  Drop:        {saved['drop']}")
            print(f"  Grip open:   {saved['gripper_open']}")
            print(f"  Grip closed: {saved['gripper_closed']}")

        else:
            print("  Try: b 90, w 80, s 60, e 120, r 90, g 160, h, t, save pickup, show, done")

    # Output config
    print("\n" + "=" * 55)
    print("  PASTE INTO config.py:")
    print("=" * 55)

    if saved["pickup"]:
        p = saved["pickup"]
        print(f"ARM_PICKUP = {{")
        print(f'    "base": {p["base"]}, "waist": {p["waist"]}, "shoulder": {p["shoulder"]},')
        print(f'    "elbow": {p["elbow"]}, "wrist": {p["wrist"]}, "gripper": {p["gripper"]},')
        print(f"}}")

    if saved["drop"]:
        d = saved["drop"]
        print(f"ARM_DROP = {{")
        print(f'    "base": {d["base"]}, "waist": {d["waist"]}, "shoulder": {d["shoulder"]},')
        print(f'    "elbow": {d["elbow"]}, "wrist": {d["wrist"]}, "gripper": {d["gripper"]},')
        print(f"}}")

    print(f"GRIPPER_OPEN = {saved['gripper_open']}")
    print(f"GRIPPER_CLOSED = {saved['gripper_closed']}")
    print()

    if ser:
        send(ser, "H")
        ser.close()
        print("Arm homed and disconnected.")


if __name__ == "__main__":
    main()
