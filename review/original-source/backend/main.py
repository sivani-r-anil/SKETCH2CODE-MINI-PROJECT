from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from preprocessing import preprocess_image
from detection import detect_components
from ocr import extract_text
from mapping import map_text_to_components
from layout import reconstruct_layout
from code_generator import generate_react_code


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Make uploaded images accessible to the React frontend
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_FOLDER),
    name="uploads"
)


@app.get("/")
def home():
    return {
        "message": "Sketch2Code backend is running"
    }


@app.get("/hello")
def hello():
    return {
        "message": "Hello from FastAPI!"
    }


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    # Save the original image
    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process the image using OpenCV
    processed_image = preprocess_image(file_path)

    # Create processed image filename
    processed_filename = "processed_" + file.filename

    processed_path = os.path.join(
        UPLOAD_FOLDER,
        processed_filename
    )

    # Save processed image
    import cv2

    cv2.imwrite(
        processed_path,
        processed_image
        
    )
    
    # Detect UI components using YOLO
    detections = detect_components(processed_path)
    
    # Extract text using EasyOCR
    ocr_texts = extract_text(processed_path)
    
    mapped_components = map_text_to_components(detections, ocr_texts)
    
    layout = reconstruct_layout(mapped_components)
    
    generated_code = generate_react_code(layout)

    return {
    "message": "Image uploaded, processed and detected successfully",
    "filename": file.filename,
    "processed_filename": processed_filename,
    "detections": detections,
    "ocr_texts": ocr_texts,
    "mapped_components": mapped_components,
    "layout": layout,
    "generated_code": generated_code
}


@app.get("/upload-location")
def upload_location():
    return {
        "upload_folder": UPLOAD_FOLDER,
        "absolute_path": os.path.abspath(UPLOAD_FOLDER)
    }