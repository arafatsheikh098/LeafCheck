PROJECT: LeafCheck
PURPOSE: A person uploads or captures a photo of a tomato, potato, maize (corn) or bell-pepper leaf and gets the likely disease (or "healthy"), a confidence level, and plain-language advice in English and Bangla. When the model is not confident, it says so instead of guessing.

IN SCOPE
F1 Data pipeline CLI: python -m leafcheck.data prepare --source <URL or local dir> --out data/. Uses the PlantVillage "color" images for exactly these 19 classes: Tomato (10: bacterial spot, early blight, late blight, leaf mold, septoria leaf spot, spider mites, target spot, yellow leaf curl virus, mosaic virus, healthy), Potato (3: early blight, late blight, healthy), Corn/maize (4: cercospora/gray leaf spot, common rust, northern leaf blight, healthy), Bell pepper (2: bacterial spot, healthy). The download must work without a login; if it cannot be verified, accept a local folder and document the exact manual download step. Validate every image; record SHA-256 and perceptual hashes; write data/DATASET_INFO.md with the dataset's license and citation.
F2 Leakage-safe split: group duplicates and near-duplicates BEFORE splitting, including rotated and flipped copies (compute the perceptual hash for all 8 orientations of each image and group two images if any orientation matches within a configured Hamming distance). Split by GROUP, stratified by class, 70/15/15, fixed seed. Write manifests (path, class, group id, split, sha256) and a verify command that re-checks zero overlap.
F3 Training: config-driven (YAML); torchvision MobileNetV3-Small with ImageNet-pretrained weights; augmentation on the training split only; fixed seeds; class-weighted loss when the imbalance ratio exceeds 3; early stopping on validation macro-F1. Saves model.pt, class_names.json, metrics.json (including hardware and training time) and a config snapshot. A CI smoke training run on a tiny synthetic dataset finishes in under 2 minutes.
F4 Evaluation: on the test split only: accuracy, macro-F1, per-class precision/recall/F1, confusion-matrix PNG, and accuracy by confidence bucket. Choose the "not sure" threshold on the VALIDATION split (smallest confidence at which accepted predictions reach the configured precision target, default 95%) and report test coverage at that threshold. Robustness table: test accuracy under synthetic blur, brightness, contrast, JPEG quality, small rotation and center crop. Auto-generate reports/eval.md.
F5 Inference API (FastAPI): POST /api/predict (multipart image, max 5 MB; accept JPEG/PNG/WebP validated by content, not extension; apply EXIF orientation; convert to RGB; reject corrupt files and decompression bombs with clear 4xx errors). Response: status ("ok" or "not_sure"), top3 [{class_id, crop, condition, confidence}], advice {en, bn}, model_version, disclaimer. Also GET /api/classes, GET /api/model-info, GET /health (reports model loaded). Model loads once at startup; CPU only; torch.inference_mode; single worker; start-up fails loudly if model files are missing or the class count mismatches.
F6 Frontend: one mobile-first page (HTML/CSS/vanilla JS, no CDN): take a photo or choose a file (accept="image/*" capture="environment"), preview, client-side downscale to at most 1024px before upload, EN/Bangla toggle remembered in localStorage, results with confidence bars, a "not sure" state that tells the user how to retake the photo (single leaf, good light, plain background), friendly error states, and a visible disclaimer.
F7 Advice content: data/advice.json for each of the 19 classes: short description, what to do (general and conservative), when to contact a local agricultural extension officer; English and Bangla; field reviewed_by_human: false until the owner changes it. Never recommend pesticide brands or doses.
F8 Operations: Dockerfile with CPU-only PyTorch, non-root user, small image; models/ committed (at most 25 MB) with metrics.json; examples/ with 6 correctly classified test images and their expected labels (documented as hand-picked); scripts/smoke_test.sh; CI.

OUT OF SCOPE
User accounts, storing uploaded images, any database, GPU serving, a mobile app, object detection or segmentation, other crops, pesticide brands or doses, retraining from the web UI, analytics, anything not listed above.

ALLOWED STACK
Python 3.11 or 3.12; PyTorch and torchvision (CPU wheels); Pillow; imagehash; numpy; scikit-learn (metrics only); matplotlib (plots only); PyYAML; FastAPI; uvicorn; python-multipart; pydantic; pytest; httpx; pytest-playwright; ruff; Docker; GitHub Actions.

GLOBAL ACCEPTANCE CRITERIA
G1 Zero overlap between train/val/test by SHA-256 and by perceptual-hash group, including rotated and flipped variants (a test plus a verify command).
G2 One shared preprocessing module is used by training, evaluation and serving (a test asserts they call the same function).
G3 The README reports test macro-F1 honestly with the limitation text (lab-style PlantVillage images may not match real field photos).
G4 The API rejects: non-images, files over 5 MB, corrupt files, over-large pixel counts, and empty uploads.
G5 Each file in examples/ returns its expected class in an automated test through the real API.
G6 CI is green including the synthetic smoke training; peak memory during inference is measured and recorded in the README.

MILESTONES
M1 Foundation; M2 Data pipeline and leakage-safe split; M3 Training; M4 Evaluation and threshold; M5 Inference API; M6 Frontend and advice; M7 Deployment package and examples.
