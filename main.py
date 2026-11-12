"""
Plastic Segregation AI - Main Pipeline
Camera -> YOLO Detection -> Robotic Arm Pick-and-Place

Architecture: Laptop (YOLO) -> RPi (WiFi relay) -> ESP8266 (serial) -> PCA9685 -> 6-DOF arm

Usage:
    python main.py                  # Run with NetworkArm (via RPi relay)
    python main.py --direct         # Direct serial to ESP8266 (no RPi)
    python main.py --simulate       # Simulated arm (no hardware)
    python main.py --no-arm         # Detection only, no arm movement
"""

import argparse
import time
import cv2
from detect_plastic import PlasticDetector
from arm_controller import NetworkArm, ArmController, SimulatedArm
import config


def main():
    parser = argparse.ArgumentParser(description="Plastic Segregation AI")
    parser.add_argument("--simulate", action="store_true",
                        help="Use simulated arm (no hardware needed)")
    parser.add_argument("--direct", action="store_true",
                        help="Direct serial to ESP8266 (bypass RPi relay)")
    parser.add_argument("--no-arm", action="store_true",
                        help="Detection only, skip arm control")
    parser.add_argument("--model", type=str, default=None,
                        help="Path to YOLO model weights")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX,
                        help="Camera index")
    parser.add_argument("--port", type=str, default=config.SERIAL_PORT,
                        help="Serial port (for --direct mode)")
    parser.add_argument("--rpi-host", type=str, default=None,
                        help="RPi IP address (overrides config.RPI_HOST)")
    args = parser.parse_args()

    # ── Init detector ───────────────────────────────────────
    print("=" * 50)
    print("  PLASTIC SEGREGATION AI")
    print("  Laptop -> RPi -> ESP8266 -> 6-DOF Arm")
    print("=" * 50)

    detector = PlasticDetector(model_path=args.model)

    # ── Init arm ────────────────────────────────────────────
    arm = None
    if not args.no_arm:
        if args.simulate:
            arm = SimulatedArm()
        elif args.direct:
            print("[Main] Direct serial mode (no RPi)")
            arm = ArmController(port=args.port)
        else:
            host = args.rpi_host or config.RPI_HOST
            print(f"[Main] Connecting to RPi relay at {host}:{config.RPI_PORT}")
            arm = NetworkArm(host=host)

        if not arm.connect():
            print("[Main] Arm connection failed. Running detection-only mode.")
            arm = None

    # ── Init camera ─────────────────────────────────────────
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    if not cap.isOpened():
        print("[Main] ERROR: Cannot open camera!")
        return

    print(f"[Main] Camera opened (index {args.camera})")
    print("[Main] Press 'q' to quit, 'h' to home arm, 'p' to force pick-and-place")
    print("-" * 50)

    last_action_time = 0
    plastic_detected_frames = 0
    FRAMES_TO_CONFIRM = 3  # require N consecutive frames before acting

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Main] Frame capture failed")
                break

            # ── Detect ──────────────────────────────────────
            detections = detector.detect(frame)

            # ── Check for actionable detection ──────────────
            pickup_targets = [d for d in detections if detector.is_in_pickup_zone(d)]

            if pickup_targets:
                plastic_detected_frames += 1
            else:
                plastic_detected_frames = 0

            # ── Act on confirmed detection ──────────────────
            now = time.time()
            cooldown_ok = (now - last_action_time) > config.DETECTION_COOLDOWN

            if (plastic_detected_frames >= FRAMES_TO_CONFIRM
                    and cooldown_ok and arm is not None):

                target = pickup_targets[0]  # pick the largest
                nx, ny = target["center_norm"]
                conf = target["confidence"]

                print(f"\n[Main] PLASTIC DETECTED at ({nx:.2f}, {ny:.2f}) "
                      f"conf={conf:.0%}")
                print("[Main] Initiating pick-and-place...")

                arm.pick_and_place_mapped(nx, ny)

                last_action_time = time.time()
                plastic_detected_frames = 0

            # ── Display ─────────────────────────────────────
            if config.SHOW_PREVIEW:
                display = detector.draw_detections(frame.copy(), detections)

                # Status bar
                status = f"Detections: {len(detections)}"
                if pickup_targets:
                    status += f" | In pickup zone: {len(pickup_targets)}"
                    status += f" | Confirming: {plastic_detected_frames}/{FRAMES_TO_CONFIRM}"
                if not cooldown_ok:
                    remaining = config.DETECTION_COOLDOWN - (now - last_action_time)
                    status += f" | Cooldown: {remaining:.1f}s"

                cv2.putText(display, status, (10, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                cv2.imshow("Plastic Segregation AI", display)

            # ── Keyboard controls ───────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("h") and arm:
                arm.home()
            elif key == ord("p") and arm:
                arm.pick_and_place()

    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if arm:
            arm.disconnect()
        print("[Main] Shutdown complete")


if __name__ == "__main__":
    main()
