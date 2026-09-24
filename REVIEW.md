# Sketch2Code diagnosis and implementation review

## Outcome and scope

The supplied login sketch has a substantially better reconstructed structure. YOLOv8, the supplied model weights, EasyOCR, OpenCV, FastAPI, React/Vite, Tailwind, Monaco, Babel and the iframe preview remain in use. The repairs are a detector/OCR/layout post-processing improvement, **not retraining and not a claim of general model accuracy**.

No manually entered list of expected login elements is used by the application. The before/after evidence contains real inference output. The expected visual elements were counted by inspecting the supplied image, not used as pipeline input.

## What was inspected before editing

All seven backend pipeline files, `frontend/src/App.jsx`, frontend configuration and styles, `best.pt`, and the supplied image. The ZIP also contains three additional sample designs. The attached `login2(1).png` is byte-for-byte identical to `backend/uploads/login2.png`.

The model checkpoint identifies YOLOv8n, Ultralytics 8.4.135, 20 UI classes, 50 training epochs, batch size 8 and training image size 640. Existing inference used 1024. The dataset path recorded in the checkpoint is `/content/sketch2code-7/data.yaml`; that dataset and its annotated validation images were not supplied.

Stored validation metrics are precision 0.93678, recall 0.97725, mAP50 0.96768 and mAP50–95 0.84588. These are checkpoint metadata, **not metrics measured on these uploaded samples**. Without annotations and the original split, class balance, leakage and domain coverage cannot be assessed.

The unchanged model SHA-256 is:

`29d1a0be1b49e33bdf81a6fb1a6214e675c85378e40700dfe2f81e7c559fbe8c`

## Exact information-loss trace for the supplied image

| Stage | Original implementation: observed problem | Revised implementation |
|---|---|---|
| Original → preprocessing | Otsu removes the light hatched button fill and grey stroke detail. Resolution is preserved. | Keeps the same preprocessing, but does not assume it is the best detector input. |
| YOLO on original at 1024 | 11 boxes. Email field is Button 0.616; password field is Button 0.685. Login is Image 0.188. The true large heading is missed. | Original predictions remain visible in the trace and overlay. |
| YOLO on processed at 1024 | 10 boxes. Email is Button 0.512; password is Button 0.740. Login splits into Textbox 0.879 and Textbox 0.728. | Runs both inputs. Reconciles boxes supported by the same physical outline and removes high-overlap duplicates. It never chooses a complete image solely by confidence. |
| EasyOCR | Both versions read Welcome and Back. Processed OCR also reads Email, Password and the forgot-password text. It returns the email words in the order Enter, email, Your. | Uses original-image OCR, sorts text spatially, keeps raw OCR for audit, and rereads geometrically supported mixed prose/link crops with EasyOCR. |
| Mapping | Drops unmatched OCR. On the processed sample this loses Welcome, Back, Email, Password and Forget_password?. On the original it loses Welcome, Back, Password and Forgot_password?. | Retains unmatched text, reconstructs text runs, associates labels with nearby fields and records inferred/corrected types. |
| Layout | Duplicate controls survive; low-confidence blank textboxes are inconsistently discarded. A fixed 24-pixel row threshold changes with image scale. Entire rows are moved into a single left/right column in multi-column mode. | Normalised vertical overlap groups rows; a shared 24-column grid preserves horizontal positions and relative widths. No absolute positioning. |
| JSX | Keyword reclassification is mixed into rendering; empty detections generate fake defaults. All multi-item rows get equal widths. Checkbox text precedes the checkbox. | Rendering uses mapped types. Checkbox precedes its caption. Geometry controls grid width/gaps. OCR strings are JSX string expressions, so braces and quotes remain literal. |
| Preview | The baseline browser screenshot shows the wrong title, duplicate email input, a fake Subheading, an extra textbox beside Login and a footer rendered as a heading. | See the recorded corrected browser screenshots and verification results below. |

The baseline processed preview has **four text/password inputs plus one checkbox**. Only two text/password fields and one checkbox are present in the sketch. The corrected sample has two fields, one checkbox, one login button and two links; it also restores the title, subtitle, labels and footer prose.

### Original versus processed and 640 versus 1024

At 640, the original produces 12 boxes and the processed version 11. Both still contain significant errors, including missing or misclassified controls and oversized text regions. At 1024, neither version is uniformly better: preprocessing makes the split login textboxes more confident, while the original better retains some text and appearance cues. The implementation therefore keeps 1024 as the existing operating resolution and combines evidence conservatively. This is not a claim that 1024 is optimal for the unseen training distribution.

The reconciliation stage produces 7 consolidated predictions for the supplied image; mapping reconstructs 11 visible semantic components. These numbers refer to different stages. OCR-derived headings/labels/links are **not counted as successful raw YOLO detections**. Consolidated confidence is the strongest retained raw score, not a calibrated ensemble probability.

## Exactly which existing files changed

| File | Reason and simple explanation |
|---|---|
| `backend/preprocessing.py` | Adds an invalid-image check. Keeps the original grayscale, blur and Otsu processing and original dimensions. |
| `backend/detection.py` | Resolves the model path relative to the file, loads once, exposes inference parameters, compares both images, reconciles rectangular split boxes, preserves raw evidence, and extracts small marker geometry. |
| `backend/ocr.py` | Loads EasyOCR lazily; retains its raw output; identifies thin connected underline strokes and optionally rereads split text regions. It does not guess replacement words. |
| `backend/mapping.py` | Orders OCR spatially; excludes large containers from text ownership; retains unmatched OCR; checks toggle geometry; corrects controls with placeholder/action/label evidence; joins nearby text fragments; retains provenance. |
| `backend/layout.py` | Replaces the broken row-to-column split with row grouping and proportional grid spans. Labels retain field associations. Vertical gaps are bounded for readable pages. |
| `backend/code_generator.py` | Removes classification from rendering; renders clean JSX from mapped types; uses relative grid placement; puts checkboxes before labels; supports native textarea/select/radio controls and explicit placeholders for unsupported widgets. |
| `backend/main.py` | Coordinates both detector passes and original-image OCR, returns diagnostics/warnings, validates uploads, uses unique filenames, permits both localhost forms, serialises inference and bounds native CPU threads. Existing health, hello, upload and upload-location routes remain. |
| `frontend/src/App.jsx` | Keeps the main design and Monaco workflow; adds JSX/trace downloads, detection overlays, provenance and warnings; fixes object-URL cleanup; shows compilation/runtime errors; isolates editable code in a sandboxed iframe. |

New files: `backend/requirements.txt`, `backend/diagnose.py`, `backend/tests/test_pipeline.py`, this review, the root README and review evidence. The model, sample images, frontend dependency manifests/lockfile, Vite configuration, CSS and other application source files are unchanged.

The layout and generator functions are the largest targeted edits because the old multi-column assignment and equal-width rendering could not preserve the detected spatial relationships. There is no framework or pipeline replacement.

## How to explain the changes in a viva

- **YOLO** proposes component types and bounding boxes from learned visual features.
- **OpenCV** provides image preprocessing and rectangle/marker measurements. Rectangle snapping is used only for an existing YOLO prediction; it does not invent a missing control.
- **EasyOCR** reads text. Unmatched text is kept rather than silently thrown away.
- **Mapping** combines geometry and text using explicit rules. For example, an instruction beginning with “Enter” inside a rectangular predicted button is evidence for an input. A short action caption inside an outlined input is evidence for a button. A password link is never converted merely because it contains the word password.
- **Layout** groups components by vertical overlap, sorts left-to-right, and maps their positions to normal-flow CSS grid columns. This keeps widths/alignments without absolute-coordinate overlap.
- **Generation** renders the mapped data as editable JSX. It does not independently reinterpret labels.
- **Preview** compiles JSX in the browser and renders it in an isolated iframe. No generated application backend or real authentication is implied.

Heuristics are explainable but imperfect. Detection confidence and OCR confidence describe different models and should not be treated as interchangeable probabilities.

## Remaining limitations

1. The model still misses controls and confuses buttons, inputs, images, checkboxes and radio buttons. The weights have not improved; post-processing improves the pipeline output. Retraining requires the actual dataset, representative handwritten/digital examples, corrected labels and a held-out test set.
2. The complex signup sample remains imperfect: illustration regions and some controls are misclassified or absent. A control missed by YOLO is not fabricated just because a matching word appears. This can leave a button caption as plain text.
3. OCR can still change capitalisation or characters. For example the supplied signup link is read as “Sign UP.” Generic apostrophe spacing is normalised, but no login-specific dictionary is used to conceal recognition errors.
4. Marker checks are conservative. Stylised, filled or occluded controls can fail geometry checks. Underline detection can miss attached/curved strokes. Ordinary un-underlined action text may remain plain text.
5. Form containers are excluded from visible text rendering; arbitrary nested cards/tables, independently flowing complex columns, carousels and pagination are not fully reconstructed. A shared spatial grid improves relative placement, but is not a full DOM hierarchy inference system.
6. Generated colours, typography and icons are approximate. The model has no dedicated email/lock/eye icon classes, so these are not reproduced. This is a structural prototype, not pixel-perfect conversion.
7. Monaco and iframe React/Tailwind retain their external CDN dependencies. A network failure is reported in preview, but an offline asset bundle is not included.
8. The frontend still bundles Babel and is relatively large; Vite reports a chunk-size warning. That is a build warning, not a build failure.
9. Inputs, selects and checkboxes are interactive; buttons/links do not implement authentication, storage or real navigation. Editor preview supports this generated single-component format, not arbitrary npm imports.
10. Uploads are stored on disk. Automatic retention cleanup, multi-user authentication and production deployment are outside this local academic prototype.

## Verification


- **Real end-to-end upload:** FastAPI returned HTTP 200 for the supplied PNG. The frontend used that response to populate Monaco and the live iframe.
- **Intermediate verification:** saved original/processed predictions, OCR, mapping, layout, JSX and overlays. The final generated JSX was compared byte-for-byte with the browser-tested response after the last geometric refinements.
- **Browser verification:** no uncaught page errors; email accepted `student@example.com`; password input retained password type; checkbox toggled successfully. The Login button accepted clicks but intentionally has no authentication behaviour.
- **Editor verification:** changing Monaco's actual model through its editor API changed the rendered heading from Welcome Back to Greetings Back. Invalid JSX showed a visible compilation error. Restoring the original code recovered the preview. This verifies Monaco's change callback/compilation/render path; it was not an automated human typing assessment.
- **Mobile rendering:** tested a 390-pixel outer viewport; the iframe content width and scroll width both measured 340 pixels, so no horizontal overflow. Text wraps naturally.
- **Backend regression suite:** 11 tests pass, covering unmatched text, container ownership, OCR ordering, preserved links, false toggles, action versus placeholder semantics, duplicate merging, adjacent controls, scale-invariant rows and literal JSX text.
- **API checks:** health 200; invalid extension/image 400; both supported development origins pass CORS.
- **Frontend:** production build and ESLint pass. Babel's bundle size still produces the noted Vite warning.
- **Additional samples:** all three were run through real before/after inference. Their saved generated outputs were replayed through the frontend to check browser rendering; these are separate from the live HTTP upload test above.

| Additional sample | Original processed detections | Revised original / processed detections | Revised mapped items | Assessment |
|---|---:|---:|---:|---|
| `login.png` | 7 | 9 / 7 | 9 | Restores the LOGIN heading instead of a radio/checkbox and a normal submit button; two fields plus one checkbox. Un-underlined navigation text remains plain text. |
| `signup.png` | 14 | 19 / 14 | 27 | More text/labels retained and password fields identified, but navigation, illustration and some controls remain wrong; extra controls persist. Not considered an accurate reconstruction. |
| `exapmle.png` | 5 | 10 / 5 | 8 | Retains header/body/footer text and removes false text toggles, but two large section regions remain misclassified as textareas. Not considered an accurate reconstruction. |

Counts are diagnostic counts, **not precision/recall or an accuracy percentage**. There is no annotated benchmark in the supplied project.

### Evidence index

In `review/evidence/`:

- `before.json`: unchanged original versus processed pipeline trace for the supplied sample.
- `before_original.jsx`, `before_processed.jsx`: actual baseline generated code.
- `before_original_detections.png`, `before_processed_detections.png`: raw detection overlays.
- `before_preview.png`, `before_browser.json`: original browser result (recorded baseline pipeline response replayed through the unmodified frontend).
- `after.json`, `after.jsx`: final complete pipeline trace and JSX.
- `after_http.json`: the successful real HTTP upload response used by the browser.
- `after_original_detections.png`, `after_processed_detections.png`, `after_mapped_components.png`: raw versus reconstructed overlays.
- `after_preview.png`, `after_mobile_preview.png`, `after_workspace.png`, `after_browser.json`: browser screenshots and interaction/error-recovery results.
- `model_metadata.json`, `detections_640.json`: inspected checkpoint metadata and training-size comparison.
- `login_*`, `signup_*`, `exapmle_*`: additional real inference traces, generated code and rendered screenshots.
- `api_checks.json`, `additional_browser.json`, `tests.log`, `build.log`, `lint.log`: verification records.

`review/changes.diff` records the exact changes to the eight original files. `review/original-source/` preserves those original files for comparison or rollback. The original weights and supplied sample images are unchanged.
