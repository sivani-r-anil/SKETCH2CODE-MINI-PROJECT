from ultralytics import YOLO

# Load our trained Sketch2Code model
model = YOLO("models/best.pt")


def detect_components(image_path):
    results = model(image_path, conf=0.15, iou=0.45, imgsz=1024)

    detections = []

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(float, box.xyxy[0])

            detections.append({
                "class": model.names[class_id],
                "confidence": round(confidence, 3),
                "x1": round(x1, 1),
                "y1": round(y1, 1),
                "x2": round(x2, 1),
                "y2": round(y2, 1)
            })

    return detections