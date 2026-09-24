def map_text_to_components(detections, ocr_texts):
    mapped_components = []

    # Create a copy of every detection with an empty text list
    for detection in detections:
        component = detection.copy()
        component["texts"] = []
        mapped_components.append(component)

    # Check every OCR result
    for ocr in ocr_texts:
        box = ocr["box"]

        # Find OCR center
        center_x = sum(point[0] for point in box) / len(box)
        center_y = sum(point[1] for point in box) / len(box)

        matching_components = []

        for index, detection in enumerate(detections):
            x1 = detection["x1"]
            y1 = detection["y1"]
            x2 = detection["x2"]
            y2 = detection["y2"]

            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                matching_components.append(index)

        # If OCR is inside multiple boxes,
        # choose the YOLO detection with highest confidence
        if matching_components:
            best_index = max(
                matching_components,
                key=lambda i: detections[i]["confidence"]
            )

            mapped_components[best_index]["texts"].append(
                ocr["text"]
            )

    return mapped_components