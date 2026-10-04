from pathlib import Path
from threading import Lock
from uuid import uuid4
import base64
import logging
import time
import cv2
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from preprocessing import preprocess_image
from detection import detect_components, find_rectangles, reconcile_detections, find_markers, find_containers
from ocr import extract_text_with_links
from mapping import map_text_to_components
from layout import reconstruct_layout
from code_generator import generate_react_code

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
                   allow_methods=['*'], allow_headers=['*'])
UPLOAD_FOLDER = Path(__file__).resolve().parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.mount('/uploads', StaticFiles(directory=str(UPLOAD_FOLDER)), name='uploads')
# One inference at a time avoids competing model calls on a student laptop.
inference_lock = Lock()
torch.set_num_threads(min(4, torch.get_num_threads()))


@app.get('/')
def home():
    return {'message': 'Sketch2Code backend is running'}


@app.get('/hello')
def hello():
    return {'message': 'Hello from FastAPI!'}


def attach_image_crops(components, image):
    """Embed raster assets so preview and JSX export do not need upload URLs."""
    if image is None:
        return
    height, width = image.shape[:2]
    for component in components:
        if component['class'] != 'Image':
            continue
        x1, y1 = max(0, int(component['x1'])), max(0, int(component['y1']))
        x2, y2 = min(width, int(component['x2'])), min(height, int(component['y2']))
        if x2 <= x1 or y2 <= y1:
            continue
        crop = image[y1:y2, x1:x2]
        # Bound asset dimensions while preserving the inferred aspect ratio.
        scale = min(1, 1200/max(crop.shape[:2]))
        if scale < 1:
            size = (max(1, round(crop.shape[1]*scale)), max(1, round(crop.shape[0]*scale)))
            crop = cv2.resize(crop, size, interpolation=cv2.INTER_AREA)
        success, encoded = cv2.imencode('.png', crop)
        if success:
            component['image_src'] = 'data:image/png;base64,' + base64.b64encode(encoded).decode('ascii')
            component['asset_source'] = 'wireframe-crop'
            component['alt'] = 'Cropped illustration from the uploaded wireframe'


def refine_visual_regions(components, image):
    """Recover compact artwork inside mapped cards using original-image ink.

    This supplements YOLO after mapping has established card boundaries. It
    retains raster artwork rather than claiming to recognise an icon's meaning.
    OCR covered by recovered artwork remains in the trace on that image region.
    """
    import copy
    import re
    import numpy as np
    if image is None:
        return components
    result = copy.deepcopy(components)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    height, width = ink.shape

    def inside(c, box):
        return (box['x1'] <= (c['x1']+c['x2'])/2 <= box['x2']
                and box['y1'] <= (c['y1']+c['y2'])/2 <= box['y2'])

    # A low-confidence carousel on blank paper can consist solely of a page
    # border crossing the prediction. Keep outlines, drawings and any text.
    for c in list(result):
        if c['class'] != 'Carousel' or c.get('confidence', 1) >= .5 or c.get('ocr'):
            continue
        if any(o.get('texts') and inside(o, c) for o in result if o is not c):
            continue
        x, y = max(0, int(c['x1'])), max(0, int(c['y1']))
        r, b = min(width, int(c['x2'])), min(height, int(c['y2']))
        region = ink[y:b, x:r]
        if not region.size:
            continue
        _, _, stats, _ = cv2.connectedComponentsWithStats(region)
        meaningful = [s for s in stats[1:] if s[4] >= max(8, region.size*.0003)
                      and not (s[2] < region.shape[1]*.025 and s[3] > region.shape[0]*.7)
                      and not (s[3] < region.shape[0]*.025 and s[2] > region.shape[1]*.7)]
        if meaningful:
            contours, hierarchy = cv2.findContours(region, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            enclosed = hierarchy is not None and any(
                h[3] >= 0 and cv2.contourArea(contours[i]) > region.size*.1
                for i, h in enumerate(hierarchy[0]))
            if not enclosed:
                horizontal = cv2.morphologyEx(region, cv2.MORPH_OPEN,
                    np.ones((1, max(15, region.shape[1]//4)), np.uint8))
                vertical = cv2.morphologyEx(region, cv2.MORPH_OPEN,
                    np.ones((max(15, region.shape[0]//4), 1), np.uint8))
                lines = cv2.dilate(cv2.bitwise_or(horizontal, vertical), np.ones((3, 3), np.uint8))
                remaining = cv2.bitwise_and(region, cv2.bitwise_not(lines))
                if cv2.countNonZero(remaining) < max(20, region.size*.0003):
                    meaningful = []
        if not meaningful:
            result.remove(c)

    cards = [c for c in result if c['class'] == 'Card']
    for index, card in enumerate(cards):
        children = [c for c in result if c is not card and inside(c, card)]
        text = sorted([c for c in children if c.get('texts')], key=lambda c: c['y1'])
        if not text or any(c['class'] not in {'Heading', 'Subheading', 'Paragraph', 'Label'}
                           for c in text):
            continue
        cw, ch = card['x2']-card['x1'], card['y2']-card['y1']
        numeric = lambda c: bool(re.fullmatch(r'[0-9]+(?:[.,][0-9]+)*%?',
                                             ' '.join(c.get('texts', [])).strip()))
        alphabetic = [c for c in text if any(ch.isalpha() for ch in ' '.join(c['texts']))]
        if len(text) == 2 and numeric(text[0]) and alphabetic:
            # Number and caption to the right of a possible illustration.
            bounds = (card['x1']+cw*.05, card['y1']+ch*.06,
                      min(c['x1'] for c in text)-cw*.025, card['y2']-ch*.06)
        elif len(alphabetic) >= 3:
            # Caption and description below an illustration. OCR occasionally
            # reads part of a chart as one digit; require further visual proof.
            bounds = (card['x1']+cw*.07, card['y1']+ch*.06,
                      card['x2']-cw*.07, alphabetic[0]['y1']-1)
        else:
            continue
        x, y = max(0, round(bounds[0])), max(0, round(bounds[1]))
        r, b = min(width, round(bounds[2])), min(height, round(bounds[3]))
        if r-x < cw*.1 or b-y < ch*.12:
            continue
        zone = dict(x1=x, y1=y, x2=r, y2=b)
        if any(c['class'] in {'Image', 'Carousel'} and inside(c, zone) for c in children):
            continue
        region = ink[y:b, x:r]
        _, _, stats, _ = cv2.connectedComponentsWithStats(region)
        marks = [s for s in stats[1:] if s[4] >= max(6, region.size*.001)]
        if not marks:
            continue
        a, t = min(s[0] for s in marks), min(s[1] for s in marks)
        z, v = max(s[0]+s[2] for s in marks), max(s[1]+s[3] for s in marks)
        if (a <= 1 or t <= 1 or z >= r-x-1 or v >= b-y-1
                or z-a < cw*.1 or v-t < ch*.15
                or not .4 <= (z-a)/max(1, v-t) <= 2.8):
            continue
        contour, _ = cv2.findContours(region[t:v, a:z], cv2.RETR_LIST,
                                      cv2.CHAIN_APPROX_SIMPLE)
        substantial = [p for p in contour if cv2.contourArea(p) > 8]
        if len(substantial) < 2:
            continue
        pad = max(3, round(min(cw, ch)*.025))
        box = dict(x1=max(x, x+a-pad), y1=max(y, y+t-pad),
                   x2=min(r, x+z+pad), y2=min(b, y+v+pad))
        box = {key: int(value) for key, value in box.items()}
        covered = [c for c in children if c.get('texts') and inside(c, box)]
        # Do not swallow words or a legitimate isolated counter. A digit may
        # be part of artwork only when several separate ink marks surround it.
        if covered and (len(marks) < 3 or any(not numeric(c) for c in covered)):
            continue
        evidence = [o for c in covered for o in c.get('ocr', [])]
        for c in covered:
            result.remove(c)
        result.append(dict(box, **{'class': 'Image'}, id=f'card-artwork-{index}',
                           texts=[], ocr=evidence, source='opencv-card-artwork',
                           corrections=['Compact drawing recovered inside an established card; preserved as an image crop.']))
    return result


def recover_empty_table_cells(layout, image):
    """Preserve unread ink in empty reconstructed cells as audited raster crops.

    Cell positions come from the existing spatial layout. This neither guesses
    missing text nor assigns edit/delete behaviour to unidentified symbols.
    Existing text and controls always take precedence over the crop fallback.
    """
    if image is None:
        return 0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    image_height, image_width = ink.shape
    page_width = layout.get('page', {}).get('width', 800)
    max_width = max(400, min(1100, round(page_width*.70)+64))
    scale = min(.70, (max_width-64)/max(1, page_width))
    count = 0

    def visit(node):
        nonlocal count
        if node.get('role') == 'table':
            rows = node.get('children', [])
            for row in rows[1:]:
                for cell in row.get('children', []):
                    component = cell.get('component', {})
                    if (cell.get('kind') != 'component' or cell.get('children')
                            or component.get('class') != 'Paragraph'
                            or component.get('texts') or component.get('ocr')):
                        continue
                    h = max(1, cell['y2']-cell['y1'])
                    x, r = max(0, round(cell['x1'])+3), min(image_width, round(cell['x2'])-3)
                    y = max(0, round(cell['y1']-h*.15))
                    b = min(image_height, round(cell['y2']+h*.15))
                    if r <= x or b <= y:
                        continue
                    region = ink[y:b, x:r]
                    _, _, stats, _ = cv2.connectedComponentsWithStats(region)
                    # Long fragments normally belong to the table/page border.
                    marks = [s for s in stats[1:] if s[4] >= max(5, region.size*.001)
                             and s[2] < (r-x)*.85 and s[3] < (b-y)*.85
                             and s[3] >= h*.2]
                    if not marks or len(marks) > 12:
                        continue
                    left, top = min(s[0] for s in marks), min(s[1] for s in marks)
                    right = max(s[0]+s[2] for s in marks)
                    bottom = max(s[1]+s[3] for s in marks)
                    if left < 1 or top < 1 or right >= r-x-1 or bottom >= b-y-1:
                        continue  # Do not preserve clipped or ambiguous ink.
                    bounds = dict(x1=int(max(x, x+left-3)), y1=int(max(y, y+top-3)),
                                  x2=int(min(r, x+right+3)), y2=int(min(b, y+bottom+3)))
                    recovered = dict(component, **{'class': 'Image'}, **bounds,
                                     source='table-cell-raster-fallback',
                                     corrections=['Unread ink preserved from this empty table cell as a raster crop.'])
                    attach_image_crops([recovered], image)
                    if not recovered.get('image_src'):
                        continue
                    recovered['alt'] = 'Unrecognised content cropped from the original table cell'
                    recovered['display_width'] = max(6, min(124, round(
                        (bounds['x2']-bounds['x1'])*scale)))
                    cell['component'] = recovered
                    count += 1
            return
        for child in node.get('children', []):
            visit(child)

    visit(layout.get('tree', {}))
    return count


def recover_table_actions(layout, image):
    """Infer a small set of outlined icons from repeated, otherwise unread cells.

    This is a conservative OpenCV fallback, not a trained icon classifier.
    A pencil needs a diagonal elongated outline with internal divisions. A bin
    needs a wide lid, a handle hole, a body hole and two internal vertical marks.
    Require the same recognised pattern in at least three rows of one column.
    Unknown shapes retain their original crops; numeric cells are never filled.
    """
    import numpy as np
    if image is None:
        return 0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    def identify(mask):
        h, w = mask.shape
        if min(h, w) < 10 or not .55 <= w/max(1, h) <= 1.8:
            return None
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            return None
        outer = max(contours, key=cv2.contourArea)
        (_, _), (rw, rh), angle = cv2.minAreaRect(outer)
        holes = [cv2.boundingRect(c) for i, c in enumerate(contours)
                 if hierarchy[0, i, 3] >= 0 and cv2.contourArea(c) >= w*h*.01]
        diagonal = 20 <= abs(angle) % 90 <= 70
        if (diagonal and max(rw, rh)/max(1, min(rw, rh)) >= 2.7
                and len(holes) >= 2):
            return 'edit'
        # A trash-bin outline is upright, with its widest stroke near the top.
        lid = int(np.argmax(np.count_nonzero(mask, axis=1)))
        body = [b for b in holes if b[2] >= .45*w and b[3] >= .45*h
                and b[1] >= .15*h]
        handle = [b for b in holes if b[1] < .2*h and b[3] <= .25*h
                  and .15*w <= b[2] <= .65*w]
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        bars = [s for s in stats[1:] if s[3] >= .25*h and s[2] <= .18*w
                and s[3] >= 3*s[2] and .15*w < s[0] < .85*w
                and s[1] > .2*h and s[1]+s[3] < .95*h]
        if (.6 <= w/h <= 1.2 and .08*h <= lid <= .35*h
                and body and handle and len(bars) >= 2):
            return 'delete'
        return None

    def symbols(component):
        x, y, r, b = [int(component[k]) for k in ('x1', 'y1', 'x2', 'y2')]
        if x < 0 or y < 0 or r > ink.shape[1] or b > ink.shape[0]:
            return []
        mask = ink[y:b, x:r]
        if not mask.size:
            return []
        occupied = np.flatnonzero(np.any(mask > 0, axis=0))
        if not len(occupied):
            return []
        # A wide blank interval separates icons; strokes inside one icon stay together.
        chunks = np.split(occupied, np.where(np.diff(occupied) > max(3, mask.shape[0]*.22))[0]+1)
        if not 1 <= len(chunks) <= 4:
            return []
        result = []
        for chunk in chunks:
            left, right = int(chunk[0]), int(chunk[-1])+1
            ys = np.flatnonzero(np.any(mask[:, left:right] > 0, axis=1))
            top, bottom = int(ys[0]), int(ys[-1])+1
            action = identify(mask[top:bottom, left:right])
            if action is None:
                return []
            result.append(dict(action=action, x1=x+left, y1=y+top,
                               x2=x+right, y2=y+bottom))
        return result

    count = 0
    def visit(node):
        nonlocal count
        if node.get('role') == 'table':
            columns = {}
            for row in node.get('children', [])[1:]:
                for col, cell in enumerate(row.get('children', [])):
                    c = cell.get('component', {})
                    if c.get('source') != 'table-cell-raster-fallback':
                        continue
                    found = symbols(c)
                    if found:
                        columns.setdefault((col, tuple(s['action'] for s in found)), []).append((cell, found))
            for matches in columns.values():
                if len(matches) < 3:
                    continue
                for cell, found in matches:
                    original = cell.pop('component')
                    cell.update(kind='row', children=[], source='opencv-repeated-action-shapes')
                    for i, symbol in enumerate(found):
                        action = symbol['action']
                        bounds = {k: symbol[k] for k in ('x1', 'y1', 'x2', 'y2')}
                        component = dict(bounds, id=f'{original["id"]}-action-{i}',
                                         **{'class': 'Button'}, texts=[action.title()],
                                         icon=action, source='opencv-repeated-action-shapes',
                                         corrections=['Action inferred from outlined icon geometry and repetition across table rows.'])
                        cell['children'].append(dict(bounds, kind='component', component=component))
                    count += 1
            return
        for child in node.get('children', []):
            visit(child)
    visit(layout.get('tree', {}))
    return count


def run_pipeline(file_path, processed_path):
    # FastAPI executes this in a worker thread; cap native pools here too.
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    started = time.perf_counter()
    processed = preprocess_image(file_path)
    if not cv2.imwrite(str(processed_path), processed):
        raise RuntimeError('Could not save the processed image.')
    original_detections = detect_components(file_path)
    processed_detections = detect_components(processed_path)
    rectangles = find_rectangles(file_path)
    detections = reconcile_detections(original_detections, processed_detections, rectangles)
    raw_ocr, ocr_texts = extract_text_with_links(file_path)
    markers = find_markers(file_path, rectangles)
    containers = find_containers(file_path)
    mapped = map_text_to_components(detections, ocr_texts, markers, rectangles, containers)
    original_image = cv2.imread(str(file_path))
    carousel_count = sum(c['class'] == 'Carousel' for c in mapped)
    mapped = refine_visual_regions(mapped, original_image)
    attach_image_crops(mapped, original_image)
    layout = reconstruct_layout(mapped)
    table_crops = recover_empty_table_cells(layout, original_image)
    action_cells = recover_table_actions(layout, original_image)
    table_crops -= action_cells
    warnings = []
    if action_cells:
        warnings.append(f'{action_cells} table cells use action buttons inferred from repeated pencil/bin shapes. Verify the inferred meanings; buttons have no data handlers.')
    if table_crops:
        warnings.append(f'{table_crops} unread table cells use original-image crops. These are visual fallbacks, not recognised editable text or working actions.')
    if sum(c['class'] == 'Carousel' for c in mapped) < carousel_count:
        warnings.append('A low-confidence carousel region contained only blank paper or crossing border lines and was omitted. Original detections remain in the trace.')
    if not detections:
        warnings.append('YOLO found no components. Text-only output may be incomplete.')
    if any(o['confidence'] < .70 for o in ocr_texts):
        warnings.append('Some OCR text has low confidence. Check it against the image.')
    if any(c.get('corrections') for c in mapped):
        warnings.append('Some components were inferred or corrected using geometry and OCR. Review the processing details.')
    if any(c.get('image_src') for c in mapped):
        warnings.append('Illustrations use crops of the original wireframe, not reconstructed editable artwork.')
    if any(c['class'] == 'Image' and not c.get('image_src') for c in mapped):
        warnings.append('Some image regions could not be cropped and remain placeholders.')
    if any(c['class'] in {'Carousel', 'Pagination'} for c in mapped):
        warnings.append('Unresolved carousel or pagination widgets may remain placeholders.')
    return {'detections': detections, 'original_detections': original_detections,
            'processed_detections': processed_detections, 'rectangles': rectangles, 'markers': markers,
            'container_candidates': containers,
            'raw_ocr_texts': raw_ocr, 'ocr_texts': ocr_texts,
            'mapped_components': mapped, 'layout': layout,
            'generated_code': generate_react_code(layout), 'warnings': warnings,
            'duration_seconds': round(time.perf_counter()-started, 2)}


@app.post('/upload')
def upload_image(file: UploadFile = File(...)):
    content = file.file.read(20*1024*1024+1)
    if len(content) > 20*1024*1024:
        raise HTTPException(413, 'Image must be smaller than 20 MB.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg'}:
        raise HTTPException(400, 'Upload a PNG or JPEG image.')
    filename = uuid4().hex + suffix
    file_path = UPLOAD_FOLDER / filename
    processed_name = f'processed_{Path(filename).stem}.png'
    file_path.write_bytes(content)
    image = cv2.imread(str(file_path))
    if image is None or image.shape[0]*image.shape[1] > 20_000_000:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, 'Invalid image or image larger than 20 megapixels.')
    try:
        with inference_lock:
            result = run_pipeline(file_path, UPLOAD_FOLDER / processed_name)
    except Exception as exc:
        logging.exception('Wireframe conversion failed')
        raise HTTPException(500, 'Conversion failed. Check the backend terminal and model/OCR setup.') from exc
    return {'message': 'Conversion complete. Review detected and inferred components.',
            'filename': filename, 'processed_filename': processed_name, **result}


@app.get('/upload-location')
def upload_location():
    return {'upload_folder': str(UPLOAD_FOLDER), 'absolute_path': str(UPLOAD_FOLDER)}
