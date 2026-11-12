"""
Vision bridge: USB camera + YOLO plastic detector + ArUco mat markers -> web app.

    python vision_bridge.py                     # camera 0, model from runs/...best.pt
    python vision_bridge.py --camera 1 --device 0          # 2nd camera, NVIDIA GPU
    python vision_bridge.py --no-model                     # camera + markers only (calibration)
    python vision_bridge.py --image calibration_mat_A4.png --no-model   # no camera at all

Then open http://localhost:8765 (this script also serves the RoboArm web app),
connect the arm (Wi-Fi / USB) in the header, and pick "PC camera" in the Vision tab.

Only the Python standard library + opencv-python (+ ultralytics for the model).
Pixel -> table mapping, tracking and the pick itself happen in the web app, so the
same pipeline runs against the simulator and the real arm.
"""

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(HERE, "runs", "detect", "runs", "detect", "plastic_detection_v1_70-20-10", "weights", "best.pt")
DEFAULT_WEB = os.path.normpath(os.path.join(HERE, "..", "web"))
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# --------------------------------------------------------------------------- vision
class Vision(threading.Thread):
    def __init__(self, a):
        super().__init__(daemon=True)
        self.a = a
        self.cond = threading.Condition()
        self.msg = None
        self.seq = 0
        self.model = None
        self.roi = None  # [x1, y1, x2, y2] pixels: YOLO only looks here (set by the web app = the mat)
        self.names = {0: "plastic"}
        self.model_error = None
        if a.no_model:
            self.model_error = "YOLO disabled (--no-model)"
        elif not os.path.exists(a.model):
            self.model_error = f"model file not found: {a.model}"
        else:
            try:
                from ultralytics import YOLO  # imported lazily so the bridge runs without it

                self.model = YOLO(a.model)
                self.names = {int(k): v for k, v in self.model.names.items()}
                print(f"[vision] model {a.model} classes={self.names}")
            except ImportError:
                self.model_error = "ultralytics not installed - run: pip install -r requirements.txt"
            except Exception as e:  # noqa: BLE001 - keep serving the app whatever happens
                self.model_error = f"model failed to load: {e}"
        if self.model_error:
            print(f"[vision] WARNING: {self.model_error} -> markers only, no plastic detection")
        dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, a.dict))
        self.aruco = cv2.aruco.ArucoDetector(dic, cv2.aruco.DetectorParameters())
        self.cap = None
        self.still = None
        self.cam_error = None
        self.next_try = 0.0
        if a.image:
            self.still = cv2.imread(a.image)
            if self.still is None:
                sys.exit(f"cannot read {a.image}")
        else:
            self.open_camera()

    def open_camera(self):
        """Open the camera / video. Never fatal: the web app keeps working and we retry."""
        a = self.a
        src = a.video if a.video else a.camera
        backend = cv2.CAP_DSHOW if sys.platform == "win32" and not a.video else cv2.CAP_ANY
        cap = cv2.VideoCapture(src, backend)
        if not cap.isOpened():
            cap.release()
            self.cap = None
            self.cam_error = f"camera {src!r} not found - plug it in, or try --camera 1 (retrying every 5 s)"
            print(f"[vision] {self.cam_error}")
            self.next_try = time.time() + 5
            return False
        if not a.video:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, a.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height)
            if a.no_autofocus:
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap = cap
        self.cam_error = None
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[vision] camera {src!r} open at {w}x{h}")
        return True

    def publish(self, obj):
        with self.cond:
            self.msg = json.dumps(obj)
            self.seq += 1
            self.cond.notify_all()

    def read(self):
        if self.still is not None:
            time.sleep(1 / self.a.fps)
            return self.still.copy()
        if self.cap is None:
            if time.time() >= self.next_try:
                self.open_camera()
            if self.cap is None:
                self.publish({"t": "bstatus", "camera": False, "msg": self.cam_error, "model": self.model is not None, "modelError": self.model_error})
                time.sleep(1.0)
                return None
        ok, frame = self.cap.read()
        if not ok:
            if self.a.video:  # loop video files
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            if not ok:
                if not self.a.video:  # unplugged?
                    self.cap.release()
                    self.cap = None
                    self.cam_error = "camera stopped sending frames - reconnecting"
                    self.next_try = time.time() + 1
                return None
        return frame

    def run(self):
        period = 1.0 / self.a.fps
        fps, n, t_fps = 0.0, 0, time.time()
        while True:
            t0 = time.time()
            frame = self.read()
            if frame is None:
                time.sleep(0.05)
                continue
            h, w = frame.shape[:2]
            boxes = []
            if self.model is not None:
                ox, oy, view = 0, 0, frame
                roi = self.roi
                if roi:
                    x1, y1 = max(0, int(roi[0])), max(0, int(roi[1]))
                    x2, y2 = min(w, int(roi[2])), min(h, int(roi[3]))
                    if x2 - x1 > 32 and y2 - y1 > 32:
                        ox, oy, view = x1, y1, frame[y1:y2, x1:x2]
                res = self.model.predict(view, conf=self.a.conf, iou=0.45, imgsz=self.a.imgsz, device=self.a.device, verbose=False)
                for r in res:
                    if r.boxes is None:
                        continue
                    for b, c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
                        boxes.append([round(b[0] + ox, 1), round(b[1] + oy, 1), round(b[2] + ox, 1), round(b[3] + oy, 1), round(c, 3), int(k)])
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = self.aruco.detectMarkers(gray)
            markers = []
            if ids is not None:
                for c, i in zip(corners, ids.flatten().tolist()):
                    p = c.reshape(4, 2).mean(axis=0)
                    markers.append({"id": int(i), "x": round(float(p[0]), 2), "y": round(float(p[1]), 2)})
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.a.quality])
            n += 1
            if time.time() - t_fps >= 1:
                fps, n, t_fps = n / (time.time() - t_fps), 0, time.time()
            msg = {
                "t": "vision", "src": "camera", "w": w, "h": h, "ts": time.time(), "fps": round(fps, 1),
                "boxes": boxes, "markers": markers, "names": self.names, "roi": self.roi, "dict": self.a.dict,
                "model": self.model is not None, "modelError": self.model_error,
                "img": "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode() if ok else None,
            }
            self.publish(msg)
            if self.a.verbose and (boxes or markers):
                print(f"[vision] {len(boxes)} boxes, markers {[m['id'] for m in markers]}")
            time.sleep(max(0.0, period - (time.time() - t0)))


# --------------------------------------------------------------------------- minimal WebSocket
def ws_send(sock, text):
    data = text.encode()
    n = len(data)
    if n < 126:
        head = struct.pack("!BB", 0x81, n)
    elif n < 65536:
        head = struct.pack("!BBH", 0x81, 126, n)
    else:
        head = struct.pack("!BBQ", 0x81, 127, n)
    sock.sendall(head + data)


def ws_reader(sock, alive, on_text):
    """Read client frames (masked), pass text messages to on_text; stop on close/error."""

    def exact(n):
        b = b""
        while len(b) < n:
            c = sock.recv(n - len(b))
            if not c:
                raise ConnectionError
            b += c
        return b

    try:
        while alive.is_set():
            hdr = exact(2)
            op, ln = hdr[0] & 0x0F, hdr[1] & 0x7F
            if ln == 126:
                ln = struct.unpack("!H", exact(2))[0]
            elif ln == 127:
                ln = struct.unpack("!Q", exact(8))[0]
            mask = exact(4) if hdr[1] & 0x80 else b"\0\0\0\0"
            data = exact(ln) if ln < (1 << 20) else b""
            if op == 0x8:
                break
            if op == 0x1 and data:
                text = bytes(b ^ mask[i % 4] for i, b in enumerate(data)).decode("utf-8", "replace")
                try:
                    on_text(json.loads(text))
                except (ValueError, TypeError) as e:
                    print(f"[ws] bad message: {e}")
    except (OSError, ConnectionError):
        pass
    alive.clear()


class Handler(SimpleHTTPRequestHandler):
    vision = None
    extensions_map = {
        ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
        ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".wasm": "application/wasm",
        ".onnx": "application/octet-stream", "": "application/octet-stream",
    }

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")  # lets the in-browser YOLO use threads
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            return self.websocket()
        if self.path == "/api/info":
            v = self.vision
            body = json.dumps({"bridge": "roboarm-vision", "model": bool(v.model), "modelError": v.model_error,
                               "camera": v.cap is not None or v.still is not None, "cameraError": v.cam_error, "names": v.names}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def on_message(self, m):
        if m.get("c") == "roi":
            roi = m.get("roi")
            self.vision.roi = [float(v) for v in roi] if isinstance(roi, list) and len(roi) == 4 else None
            print(f"[vision] detection area {'= ' + str([round(v) for v in self.vision.roi]) if self.vision.roi else 'cleared (full frame)'}")

    def websocket(self):
        key = self.headers["Sec-WebSocket-Key"]
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response_only(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        super(SimpleHTTPRequestHandler, self).end_headers()
        sock = self.connection
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        alive = threading.Event()
        alive.set()
        threading.Thread(target=ws_reader, args=(sock, alive, self.on_message), daemon=True).start()
        print(f"[ws] client {self.client_address[0]} connected")
        v, seen = self.vision, -1
        try:
            while alive.is_set():
                with v.cond:
                    v.cond.wait_for(lambda: v.seq != seen or not alive.is_set(), timeout=1.0)
                    msg, seen = v.msg, v.seq
                if msg and alive.is_set():
                    ws_send(sock, msg)
        except OSError:
            pass
        alive.clear()
        print(f"[ws] client {self.client_address[0]} left")
        self.close_connection = True


def main():
    ap = argparse.ArgumentParser(description="Camera + YOLO + ArUco -> RoboArm web app")
    ap.add_argument("--camera", type=int, default=0, help="camera index (0 = first USB/webcam)")
    ap.add_argument("--video", help="use a video file instead of a camera")
    ap.add_argument("--image", help="use a still image instead of a camera (testing)")
    ap.add_argument("--width", type=int, default=1920, help="ask the camera for this resolution")
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--dict", default="DICT_4X4_50", help="ArUco dictionary of your corner markers")
    ap.add_argument("--no-autofocus", action="store_true", help="lock focus (recommended once focused)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-model", action="store_true", help="skip YOLO (calibration / testing)")
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu", help="'cpu' or GPU index like 0")
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--quality", type=int, default=70, help="JPEG quality of the preview stream")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to allow other devices on the LAN")
    ap.add_argument("--web", default=DEFAULT_WEB, help="RoboArm web/ folder to serve")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    v = Vision(a)
    v.start()
    Handler.vision = v
    srv = ThreadingHTTPServer((a.host, a.port), partial(Handler, directory=a.web))
    srv.daemon_threads = True
    print(f"[bridge] web app  -> http://localhost:{a.port}/   (Vision tab -> 'PC camera')")
    print(f"[bridge] stream   -> ws://localhost:{a.port}/ws")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
