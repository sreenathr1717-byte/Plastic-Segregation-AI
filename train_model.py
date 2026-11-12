"""
Train/retrain the plastic detection model.

Usage:
    python train_model.py                          # Train from scratch
    python train_model.py --resume                 # Resume last training
    python train_model.py --epochs 50 --batch 8    # Custom settings
"""

import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Train Plastic Detection Model")
    parser.add_argument("--model", type=str, default="yolo11n.pt",
                        help="Base model (yolo11n.pt, yolo11s.pt, etc.)")
    parser.add_argument("--data", type=str,
                        default="dataset/plastic_roboflow_v1/export/data.yaml",
                        help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    parser.add_argument("--name", type=str, default="plastic_detect",
                        help="Run name")
    args = parser.parse_args()

    if args.resume:
        checkpoint = "runs/detect/runs/detect/plastic_detection_v1_70-20-10/weights/last.pt"
        print(f"Resuming from {checkpoint}")
        model = YOLO(checkpoint)
        model.train(resume=True)
    else:
        model = YOLO(args.model)
        model.train(
            data=args.data,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            device="0",
            workers=2,
            project="runs/detect",
            name=args.name,
            pretrained=True,
            patience=20,
            save=True,
            amp=True,
            cos_lr=True,
            close_mosaic=10,
        )

    # Validate
    print("\n" + "=" * 50)
    print("VALIDATION")
    print("=" * 50)
    metrics = model.val()
    print(f"mAP50:    {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")


if __name__ == "__main__":
    main()
