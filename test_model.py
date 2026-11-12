"""
Test YOLOv11 plastic detection model on the test dataset.

Usage:
    python test_model.py                          # Full test set evaluation
    python test_model.py --show 5                 # Save 5 sample detection images
    python test_model.py --camera                 # Live camera test
    python test_model.py --image path/to/img.jpg  # Test on a single image
"""

import argparse
from pathlib import Path


def run_eval(model_path, data_yaml, save_samples=0):
    from ultralytics import YOLO

    print(f"\nLoading model: {model_path}")
    model = YOLO(model_path)

    print("Running evaluation on test set...\n")
    metrics = model.val(data=data_yaml, split="test", imgsz=640, batch=16, verbose=True)

    print("\n" + "=" * 50)
    print("  TEST SET RESULTS")
    print("=" * 50)
    print(f"  Precision:      {metrics.box.mp:.4f}")
    print(f"  Recall:         {metrics.box.mr:.4f}")
    print(f"  mAP@50:         {metrics.box.map50:.4f}")
    print(f"  mAP@50-95:      {metrics.box.map:.4f}")
    print("=" * 50)

    if save_samples > 0:
        save_sample_detections(model, data_yaml, save_samples)


def save_sample_detections(model, data_yaml, count):
    import cv2
    import random

    test_img_dir = Path(data_yaml).parent / "test" / "images"
    if not test_img_dir.exists():
        print(f"Test images not found at {test_img_dir}")
        return

    images = list(test_img_dir.glob("*.*"))
    samples = random.sample(images, min(count, len(images)))

    out_dir = Path("test_results")
    out_dir.mkdir(exist_ok=True)

    print(f"\nSaving {len(samples)} sample detections to {out_dir}/")

    for img_path in samples:
        results = model(str(img_path), imgsz=640, verbose=False)
        for r in results:
            plotted = r.plot()
            out_path = out_dir / f"det_{img_path.name}"
            cv2.imwrite(str(out_path), plotted)
            n = len(r.boxes)
            confs = [f"{c:.2f}" for c in r.boxes.conf.tolist()] if n > 0 else []
            print(f"  {img_path.name}: {n} detections {confs}")

    print(f"Saved to {out_dir}/")


def run_camera(model_path):
    import cv2
    from ultralytics import YOLO

    print(f"\nLoading model: {model_path}")
    model = YOLO(model_path)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("Camera open. Press q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, imgsz=640, conf=0.5, verbose=False)
        plotted = results[0].plot()
        n = len(results[0].boxes)
        if n > 0:
            confs = [f"{c:.2f}" for c in results[0].boxes.conf.tolist()]
            print(f"  Detected {n} plastic: {confs}")
        cv2.imshow("Plastic Detection Test", plotted)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def run_single(model_path, image_path):
    import cv2
    from ultralytics import YOLO

    print(f"\nLoading model: {model_path}")
    model = YOLO(model_path)
    print(f"Testing on: {image_path}")
    results = model(image_path, imgsz=640, conf=0.3, verbose=False)

    for r in results:
        n = len(r.boxes)
        print(f"\n  Detections: {n}")
        for i, (box, conf, cls) in enumerate(zip(r.boxes.xyxy, r.boxes.conf, r.boxes.cls)):
            x1, y1, x2, y2 = box.tolist()
            print(f"  [{i+1}] Plastic  conf={conf:.3f}  bbox=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")
        plotted = r.plot()
        out_path = "test_single_result.jpg"
        cv2.imwrite(out_path, plotted)
        print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test plastic detection model")
    parser.add_argument("--model", default="runs/detect/runs/detect/plastic_detection_v1_70-20-10/weights/best.pt")
    parser.add_argument("--data", default="dataset/plastic_roboflow_v1/export/data.yaml")
    parser.add_argument("--show", type=int, default=0, help="Save N sample detection images")
    parser.add_argument("--camera", action="store_true", help="Live camera test")
    parser.add_argument("--image", type=str, help="Test on a single image")
    args = parser.parse_args()

    if args.camera:
        run_camera(args.model)
    elif args.image:
        run_single(args.model, args.image)
    else:
        run_eval(args.model, args.data, args.show)