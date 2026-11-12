"""
Plastic Segregation AI - Configuration
Hardware: ESP8266 NodeMCU 1.0 (ESP-12E) + PCA9685 + Shakti 12V SMPS (use 5V buck converter!) + 3D printed 6-DOF arm
"""

# ── YOLO Model ──────────────────────────────────────────────
MODEL_PATH = "runs/detect/runs/detect/plastic_detection_v1_70-20-10/weights/best.pt"
CONFIDENCE_THRESHOLD = 0.5
IOU_THRESHOLD = 0.45
IMG_SIZE = 640
DEVICE = "0"  # "0" for GPU, "cpu" for CPU

# ── Camera ──────────────────────────────────────────────────
CAMERA_INDEX = 0  # 0 for default webcam, 1 for USB camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# ── Frame Regions ───────────────────────────────────────────
# Pickup zone (X direction): where camera sees plastic to grab
PICKUP_ZONE = {"x_min": 0.0, "y_min": 0.0, "x_max": 0.5, "y_max": 1.0}
# Drop zone (Y direction): where arm drops plastic
DROP_ZONE = {"x_min": 0.5, "y_min": 0.0, "x_max": 1.0, "y_max": 1.0}

# ── Raspberry Pi Relay ─────────────────────────────────────
# Laptop connects to RPi over WiFi, RPi relays to ESP8266 serial
RPI_HOST = "192.168.1.100"  # ** CHANGE to your RPi's IP address **
RPI_PORT = 5000

# ── Direct Serial (fallback, if no RPi) ───────────────────
SERIAL_PORT = "/dev/ttyUSB0"  # Linux: /dev/ttyUSB0 or /dev/ttyACM0
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 2  # seconds

# ── Servo Channels (PCA9685) ───────────────────────────────
# Ch 0=Base(MG996R), 1=Waist(MG995), 2=Shoulder(MG995),
# Ch 3=Elbow(SG90), 4=Wrist(SG90), 5=Gripper(SG90)
SERVO_NAMES = ["base", "waist", "shoulder", "elbow", "wrist", "gripper"]
SERVO_CMDS = {"base": "B", "waist": "W", "shoulder": "S",
              "elbow": "E", "wrist": "R", "gripper": "G"}

# ── Servo Angles (degrees) ─────────────────────────────────
# ** RUN calibrate_arm.py FIRST to find these for YOUR arm **
ARM_HOME = {
    "base": 90, "waist": 90, "shoulder": 90,
    "elbow": 90, "wrist": 90, "gripper": 60,
}

# Position to pick up plastic (X direction)
ARM_PICKUP = {
    "base": 45, "waist": 80, "shoulder": 60,
    "elbow": 120, "wrist": 90, "gripper": 60,
}

# Position to drop plastic (Y direction)
ARM_DROP = {
    "base": 135, "waist": 80, "shoulder": 60,
    "elbow": 120, "wrist": 90, "gripper": 60,
}

# Gripper open/closed angles (geared parallel gripper)
GRIPPER_OPEN = 60
GRIPPER_CLOSED = 160

# ── Timing (seconds) ───────────────────────────────────────
MOVE_DELAY = 0.5       # delay between servo moves
GRAB_DELAY = 0.8       # time to wait after gripper closes
DETECTION_COOLDOWN = 2  # seconds between pick-and-place cycles

# ── Display ─────────────────────────────────────────────────
SHOW_PREVIEW = True
SHOW_ZONES = True
