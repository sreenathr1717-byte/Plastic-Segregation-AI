"""
One-time conversion: best.pt (PyTorch) -> web/models/plastic.onnx so the web app's
Vision tab can run the plastic detector in the browser (no Python needed afterwards).

    python export_onnx.py                 # uses runs/.../weights/best.pt
    python export_onnx.py --model other.pt --imgsz 640

Needs ultralytics (+ PyTorch) once — e.g. on the Windows PC you trained on:
    pip install ultralytics onnx
Then copy web/models/plastic.onnx and plastic.json to the other computer if needed.
"""

import argparse
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "runs", "detect", "runs", "detect", "plastic_detection_v1_70-20-10", "weights", "best.pt")
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "web", "models"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Export the YOLO model to ONNX for the browser")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--imgsz", type=int, default=640)
    a = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(a.model)
    # opset 12 + static 640x640 input: works in onnxruntime-web's WebAssembly backend
    path = model.export(format="onnx", imgsz=a.imgsz, opset=12, dynamic=False, simplify=True, nms=False)
    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, "plastic.onnx")
    shutil.copyfile(path, dst)
    names = {int(k): v for k, v in model.names.items()}
    with open(os.path.join(OUT_DIR, "plastic.json"), "w") as f:
        json.dump({"names": names, "imgsz": a.imgsz, "source": os.path.basename(a.model)}, f)
    print(f"Wrote {dst} ({os.path.getsize(dst) / 1e6:.1f} MB), classes {names}")
    print("Reload the web app: Vision tab -> Webcam (detect in browser).")
