# Plastic Segregation AI

An experimental computer-vision and robotics project that detects plastic objects with a YOLO model and can send pick-and-place commands to a 6-DOF robotic arm.

## How it works

```text
Camera → YOLO plastic detection → pickup-zone check → robotic arm
                                      ├─ Wi-Fi/TCP → Raspberry Pi relay → ESP8266
                                      ├─ Direct serial → ESP8266
                                      └─ Simulated arm (software testing)
```

The main application confirms detections across consecutive frames before triggering a pick-and-place action. The detector draws bounding boxes and pickup/drop zones in its preview window.

## Repository contents

- `main.py` — runs the live detection and pick-and-place pipeline.
- `detect_plastic.py` — loads the Ultralytics YOLO model and processes frames.
- `arm_controller.py` — network, direct-serial, and simulated arm controllers.
- `rpi_relay.py` — Raspberry Pi relay component.
- `arduino_arm_control/` — Arduino-side arm control files.
- `train_model.py` — trains or resumes a YOLO model.
- `test_model.py` — evaluates a model or tests it with an image or camera.
- `calibrate_arm.py` — arm calibration utility.
- `requirements.txt` — Python package dependencies.

## Requirements

- Python 3.9 or newer (use a Python version supported by your installed PyTorch and Ultralytics versions).
- A camera for live detection.
- For hardware operation: the compatible robotic arm, ESP8266/servo controller, and (for network mode) a Raspberry Pi running the relay.
- A trained YOLO weights file and, for training/evaluation, a dataset with a YOLO-compatible `data.yaml`.

The Python code imports a root-level `config.py` for model, camera, detection-zone, connection, and arm settings. Make sure that file is present and configured for your setup before running the application. Model weights and datasets may need to be supplied separately; the scripts use project-specific default paths.

## Setup

Clone the repository and create/activate a virtual environment:

```bash
git clone https://github.com/sreenathr1717-byte/Plastic-Segregation-AI.git
cd Plastic-Segregation-AI
python -m venv .venv
```

Activate it, then install dependencies:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Install a PyTorch build suitable for your operating system and hardware if the package installation does not provide one. See the [PyTorch installation guide](https://pytorch.org/get-started/locally/) for options.

## Run the application

After configuring `config.py`, connecting a camera, and supplying model weights:

```bash
# Use the Raspberry Pi network relay (default mode)
python main.py --model path/to/best.pt --rpi-host <RASPBERRY_PI_IP>

# Connect directly to the ESP8266 over serial
python main.py --direct --port <SERIAL_PORT> --model path/to/best.pt

# Test the pipeline without moving physical hardware
python main.py --simulate --model path/to/best.pt

# Run detection only
python main.py --no-arm --model path/to/best.pt
```

Press **q** to quit the preview, **h** to home the arm, or **p** to trigger a pick-and-place action manually. Camera index and serial port can also be selected with `--camera` and `--port`.

## Train and test a model

The training script defaults to a YOLO11 nano base model and expects a dataset YAML at `dataset/plastic_roboflow_v1/export/data.yaml`. Provide paths/settings appropriate to your dataset:

```bash
python train_model.py --data path/to/data.yaml --epochs 100 --batch 4
```

Evaluate a model, test an image, or run a camera test:

```bash
python test_model.py --model path/to/best.pt --data path/to/data.yaml
python test_model.py --model path/to/best.pt --image path/to/image.jpg
python test_model.py --model path/to/best.pt --camera
```

Training and evaluation require the dataset files to be available locally. Check the script defaults and pass `--help` for available options.

## Safety

Test first with `--simulate`. Before enabling the physical arm, verify the workspace is clear, the arm is securely mounted, the pickup/drop positions and servo limits are calibrated, and the emergency stop or power disconnect is accessible. Keep hands and loose objects away from moving parts.

## License

No license is currently specified. Unless a license is added, standard copyright restrictions apply.
