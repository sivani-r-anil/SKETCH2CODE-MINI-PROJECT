import easyocr

# Load EasyOCR reader once
reader = easyocr.Reader(['en'])

def extract_text(image_path):
    results = reader.readtext(image_path)

    texts = []

    for result in results:
        box, text, confidence = result

        # Convert NumPy coordinates to normal Python integers
        clean_box = [
            [int(point[0]), int(point[1])]
            for point in box
        ]

        texts.append({
            "text": text,
            "confidence": round(float(confidence), 3),
            "box": clean_box
        })

    return texts