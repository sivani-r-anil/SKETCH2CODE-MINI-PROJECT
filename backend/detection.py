"""YOLO detections plus contour evidence for reconciliation and cautious recovery."""
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np


@lru_cache(maxsize=1)
def get_model():
    from ultralytics import YOLO
    return YOLO(str(Path(__file__).resolve().parent / 'models' / 'best.pt'))


def detect_components(image_path, conf=0.15, imgsz=1024):
    model = get_model()
    results = model(str(image_path), conf=conf, iou=0.45, imgsz=imgsz, verbose=False)
    return [dict(**{'class': model.names[int(b.cls[0])]},
                 confidence=round(float(b.conf[0]), 3),
                 **dict(zip(('x1', 'y1', 'x2', 'y2'),
                            [round(float(v), 1) for v in b.xyxy[0]])))
            for result in results for b in result.boxes]


def area(b):
    return max(0, b['x2'] - b['x1']) * max(0, b['y2'] - b['y1'])


def intersection(a, b):
    return max(0, min(a['x2'], b['x2']) - max(a['x1'], b['x1'])) * max(
        0, min(a['y2'], b['y2']) - max(a['y1'], b['y1']))


def iou(a, b):
    overlap = intersection(a, b)
    return overlap / max(1, area(a) + area(b) - overlap)


def find_rectangles(image_path):
    color = cv2.imread(str(image_path))
    if color is None:
        raise ValueError('Cannot decode this image.')
    image = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    height, width = image.shape
    hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)
    _, ink = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Closed, mostly rectangular outlines; reject letters and page borders.
        if w < width * .08 or h < height * .025 or h > height * .25:
            continue
        if not 1.5 < w / h < 20 or cv2.contourArea(contour) / (w * h) < .80:
            continue
        corners = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(corners) != 4:
            continue
        box = dict(x1=x, y1=y, x2=x+w, y2=y+h)
        inset = max(2, min(w, h)//12)
        patch = hsv[y+inset:y+h-inset, x+inset:x+w-inset]
        box['filled'] = bool(np.mean(patch[:, :, 1] > 80) > .65)
        # Extra visual evidence does not itself change the component class.
        # Keep the existing `filled` rule to avoid changing recovery behaviour.
        box['fill_fraction'] = round(float(np.mean(patch[:, :, 1] > 80)), 3)
        pixels = color[y+inset:y+h-inset, x+inset:x+w-inset]
        b, g, r = np.median(pixels.reshape(-1, 3), axis=0).astype(int)
        box['fill_color'] = f'#{r:02x}{g:02x}{b:02x}'
        if not any(iou(box, old) > .85 for old in boxes):
            boxes.append(box)
    # An enclosing bar/card with a separate control inside is not that control.
    boxes = [b for b in boxes if not any(area(other) < area(b)*.5
             and intersection(b, other)/max(1, area(other)) > .95 for other in boxes)]
    return sorted(boxes, key=lambda b: (b['y1'], b['x1']))


def reconcile_detections(original, processed, rectangles):
    """Keep raw evidence; merge only boxes supported by the same outline/region.

    A contour never invents a new control. It must have YOLO support.
    Confidence is the strongest raw score, NOT a calibrated fused probability.
    """
    candidates = []
    controls = {'Button', 'Textbox', 'Password box', 'Select', 'Textarea', 'Image'}
    for source, detections in [('original', original), ('processed', processed)]:
        for raw in detections:
            item = {**raw, 'source': 'yolo', 'evidence': [{**raw, 'image': source}]}
            if raw['class'] in controls:
                matches = [r for r in rectangles
                           if (intersection(raw, r) / max(1, area(raw)) > .72
                               and area(raw) > .30 * area(r))
                           or (intersection(raw, r) / max(1, min(area(raw), area(r))) > .85
                               and .65 < area(raw)/max(1, area(r)) < 2
                               and .65 < (raw['y2']-raw['y1'])/(r['y2']-r['y1']) < 1.7
                               and (r['x2']-r['x1'])/(r['y2']-r['y1']) >= 2.2)]
                if matches:
                    rectangle = max(matches, key=lambda r: iou(raw, r))
                    item.update(rectangle)
                    item['outline'] = True
            candidates.append(item)
    kept = []
    for item in sorted(candidates, key=lambda c: -c['confidence']):
        duplicate = next((c for c in kept if _same_component(c, item)), None)
        if duplicate is None:
            kept.append(item)
        else:
            duplicate['evidence'].extend(item['evidence'])
    return sorted(kept, key=lambda c: (c['y1'], c['x1']))



def _same_component(a, b):
    """Overlap alone must not collapse a container into its child control."""
    overlap = iou(a, b)
    if overlap <= .70:
        return False
    containers = {'Form', 'Card', 'Container', 'Panel', 'Section', 'Table', 'Table row'}
    if a['class'] != b['class'] and (a['class'] in containers or b['class'] in containers):
        return False
    # Text can sit inside an input/button; both observations carry useful evidence.
    text = {'Heading', 'Subheading', 'Label', 'Paragraph', 'Link'}
    if (a['class'] in text) != (b['class'] in text):
        return False
    # Different, nested artwork/control boxes need OCR-aware consolidation later.
    if (a['class'] == 'Image') != (b['class'] == 'Image') and overlap < .95:
        return False
    if a.get('outline') and b.get('outline'):
        # Distinct physical outlines remain separate even when YOLO overlaps.
        return all(abs(a[key]-b[key]) < .01 for key in ('x1', 'y1', 'x2', 'y2'))
    return True


def find_containers(image_path):
    """Return large closed outlines as candidates, never as invented YOLO hits.

    Kept separate from control rectangles: enclosing cards must not snap several
    child controls onto one shared box. Mapping must still validate ownership.
    """
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError('Cannot decode this image.')
    height, width = image.shape
    _, ink = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < width*.15 or h < height*.12 or not .4 < w/h < 8:
            continue
        rectangularity = cv2.contourArea(contour)/max(1, w*h)
        corners = cv2.approxPolyDP(contour, .02*cv2.arcLength(contour, True), True)
        if rectangularity < .8 or len(corners) != 4:
            continue
        candidate = dict(x1=x, y1=y, x2=x+w, y2=y+h,
                         source='opencv-container-candidate')
        candidates.append(candidate)
    kept = []
    for candidate in sorted(candidates, key=area, reverse=True):
        if not any(iou(candidate, other) > .90 for other in kept):
            kept.append(candidate)
    return sorted(kept, key=lambda b: (b['y1'], b['x1']))


def find_markers(image_path, rectangles):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError('Cannot decode this image.')
    height, width = image.shape
    _, ink = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    markers = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if not (width*.008 < w < width*.09 and height*.005 < h < height*.09):
            continue
        if not .65 < w/h < 1.5 or cv2.contourArea(c)/(w*h) < .60:
            continue
        marker = dict(x1=x, y1=y, x2=x+w, y2=y+h)
        perimeter = cv2.arcLength(c, True)
        marker['square'] = len(cv2.approxPolyDP(c, .03*perimeter, True)) == 4
        marker['circularity'] = round(float(4*np.pi*cv2.contourArea(c)/max(1, perimeter**2)), 3)
        marker['shape'] = 'square' if marker['square'] else ('round' if marker['circularity'] > .75 else 'unknown')
        if any(intersection(marker, r)/max(1, area(marker)) > .8 for r in rectangles):
            continue  # Icons inside an input are not checkboxes.
        if not any(iou(marker, old) > .7 for old in markers):
            markers.append(marker)
    return markers
