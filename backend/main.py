from pathlib import Path
from threading import Lock
from uuid import uuid4
import logging
import time
import cv2
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from preprocessing import preprocess_image
from detection import detect_components, find_rectangles, reconcile_detections, find_markers
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
    mapped = map_text_to_components(detections, ocr_texts, markers, rectangles)
    layout = reconstruct_layout(mapped)
    warnings = []
    if not detections:
        warnings.append('YOLO found no components. Text-only output may be incomplete.')
    if any(o['confidence'] < .70 for o in ocr_texts):
        warnings.append('Some OCR text has low confidence. Check it against the image.')
    if any(c.get('corrections') for c in mapped):
        warnings.append('Some components were inferred or corrected using geometry and OCR. Review the processing details.')
    if any(c['class'] == 'Image' and c.get('source') == 'geometry+yolo' for c in mapped):
        warnings.append('Nested textless shapes are represented as an image placeholder; artwork was not reconstructed.')
    if any(c['class'] in {'Carousel', 'Table', 'Table row', 'Table data', 'Table head', 'Pagination'} for c in mapped):
        warnings.append('Complex table/carousel/pagination widgets are represented as placeholders.')
    return {'detections': detections, 'original_detections': original_detections,
            'processed_detections': processed_detections, 'rectangles': rectangles, 'markers': markers,
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
