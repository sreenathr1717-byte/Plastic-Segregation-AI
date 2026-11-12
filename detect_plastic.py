"""
Plastic detection module using YOLOv11.
"""

from ultralytics import YOLO
import cv2
import config


class PlasticDetector:
    def __init__(self, model_path=None):
        path = model_path or config.MODEL_PATH
        self.model = YOLO(path)
        print(f"[Detector] Loaded model: {path}")

    def detect(self, frame):
        """
        Run detection on a frame.
        Returns list of dicts: {bbox, center, confidence, area}
        """
        results = self.model.predict(
            source=frame,
            conf=config.CONFIDENCE_THRESHOLD,
            iou=config.IOU_THRESHOLD,
            imgsz=config.IMG_SIZE,
            device=config.DEVICE,
            verbose=False,
        )

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                area = (x2 - x1) * (y2 - y1)

                detections.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "center": (cx, cy),
                    "center_norm": (cx / frame.shape[1], cy / frame.shape[0]),
                    "confidence": conf,
                    "area": area,
                })

        # Sort by area descending (pick the biggest plastic first)
        detections.sort(key=lambda d: d["area"], reverse=True)
        return detections

    def is_in_pickup_zone(self, detection):
        """Check if detected plastic is in the pickup zone."""
        nx, ny = detection["center_norm"]
        z = config.PICKUP_ZONE
        return z["x_min"] <= nx <= z["x_max"] and z["y_min"] <= ny <= z["y_max"]

    def draw_detections(self, frame, detections):
        """Draw bounding boxes and zones on frame for visualization."""
        h, w = frame.shape[:2]

        if config.SHOW_ZONES:
            # Pickup zone (green)
            pz = config.PICKUP_ZONE
            cv2.rectangle(
                frame,
                (int(pz["x_min"] * w), int(pz["y_min"] * h)),
                (int(pz["x_max"] * w), int(pz["y_max"] * h)),
                (0, 255, 0), 2,
            )
            cv2.putText(frame, "PICKUP (X)", (int(pz["x_min"] * w) + 10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Drop zone (blue)
            dz = config.DROP_ZONE
            cv2.rectangle(
                frame,
                (int(dz["x_min"] * w), int(dz["y_min"] * h)),
                (int(dz["x_max"] * w), int(dz["y_max"] * h)),
                (255, 0, 0), 2,
            )
            cv2.putText(frame, "DROP (Y)", (int(dz["x_min"] * w) + 10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]
            in_zone = self.is_in_pickup_zone(det)
            color = (0, 255, 0) if in_zone else (0, 165, 255)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"Plastic {conf:.0%}"
            if in_zone:
                label += " [PICKUP]"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return frame
