# Sketch2Code — reviewed prototype

This is your existing FastAPI + YOLOv8 + EasyOCR + React/Vite project, repaired in place. The trained `backend/models/best.pt` is unchanged. No LLM service or API key is used.

## Run on Windows

Tested in the review environment with Python 3.12, CPU PyTorch 2.8.0, and Node 24. Use two terminals. Extract the ZIP first; do not run files inside the ZIP viewer.

**Terminal 1: backend (first setup)**

```powershell
cd Sketc2Code_copy\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2: frontend**

```powershell
cd Sketc2Code_copy\frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173>. Upload `backend/uploads/login2.png` (identical to your attached image). Wait for conversion, open Processing Details, switch between original YOLO, processed YOLO, and mapped components, then try the email/password fields and checkbox. Edit JSX in Monaco to update the preview.

On later runs, just run the two server commands; do not reinstall packages. If you already have a working environment, keep it as a backup while trying this one.

**Linux/macOS:** use `python3 -m venv .venv` and `.venv/bin/python` instead of the Windows executable paths. Install a PyTorch wheel appropriate for your platform; the CPU wheel index above was tested on Linux, and the project does not require CUDA.

## Important demo setup

- The first EasyOCR conversion downloads its detection and English recognition weights. Run one conversion before the review so these are cached.
- Monaco and the iframe's React/Tailwind scripts retain the existing CDN-based loading. They need an internet connection. This is not an offline bundle.
- CPU inference can take time, particularly on a cold start or when other workloads are running. Only one backend inference runs at a time.
- The preview is a UI prototype. Inputs and checkboxes are interactive; login, signup and navigation have no application business logic.
- `VITE_API_URL` can override the API base address. The default is `http://127.0.0.1:8000`. Development CORS allows localhost and 127.0.0.1 on port 5173.

## Reproduce the pipeline trace

From the backend directory, with the same Python environment:

```powershell
.\.venv\Scripts\python.exe diagnose.py uploads/login2.png --output diagnostics/login2
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`diagnose.py` saves the processed image, raw original-image detections, raw processed-image detections, mapped overlays, all OCR/mapping/layout data in JSON, and generated JSX. It accepts other PNG/JPEG images too. The frontend also offers Download JSX and Download pipeline trace.

To verify the frontend:

```powershell
npm run build
npm run lint
```

## Files to read for your viva

1. `REVIEW.md`: diagnosis, actual before/after results, changes and limitations.
2. `backend/detection.py`: YOLO predictions, rectangle-based reconciliation, marker geometry.
3. `backend/ocr.py`: EasyOCR, retaining raw output and separating underline-supported link text.
4. `backend/mapping.py`: spatial text assignment, preserving unmatched text, conservative corrections.
5. `backend/layout.py`: row grouping and proportional grid placement.
6. `backend/code_generator.py`: JSX rendering from the reconstructed data.
7. `backend/main.py`: the complete pipeline and upload API.
8. `review/evidence/`: captured intermediate data and browser screenshots.

The original versions of modified source files are in `review/original-source/`; `review/changes.diff` shows exact edits. Dependencies, build caches, browser tools and virtual environments are not bundled.
