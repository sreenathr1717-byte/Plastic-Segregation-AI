from ultralytics import YOLO
import torch

print("=" * 45)
print("PLASTIC SEGREGATION - AI TEST")
print("=" * 45)

print("GPU:", torch.cuda.get_device_name(0))

# Load pretrained YOLO11 nano
model = YOLO("yolo11n.pt")

print("\nModel loaded successfully!")

# Test image
results = model.predict(
    source="https://ultralytics.com/images/bus.jpg",
    device=0,
    conf=0.5,
    save=True
)

print("\nDetection completed!")

for result in results:
    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        print(
            "Object:",
            model.names[class_id],
            "| Confidence:",
            round(confidence * 100, 2),
            "%"
        )

print("\nAI TEST COMPLETED")

