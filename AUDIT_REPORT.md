# Project Audit Report: LeafCheck

**Audit Date:** October 2026  
**Project Path:** `project/` (LeafCheck)  
**Repository State:** Git initialized (`main` branch) | Clean  

---

## 1. Executive Summary
LeafCheck is a lightweight, CPU-optimized computer vision web application that classifies tropical plant species from a single leaf photo. Shipped with a model trained on the BdLeaf20 Bangladesh plant dataset (9 target species), it predicts species probabilities with confidence scoring, top-3 alternatives, and provides multilingual plant care guidance in both English and Bengali.

---

## 2. Technical Stack & Architecture
- **Machine Learning Runtime:** PyTorch (CPU-only build), Torchvision, MobileNetV3 / ResNet backbone
- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Frontend / UI:** Single-page application with Vanilla JavaScript, drag-and-drop file upload, webcam photo capture, confidence progress meters, and multilingual toggle
- **Localization:** Bilingual English/Bangla dictionary (`static/i18n.js` and `data/advice.json`)
- **Deployment:** Production `Dockerfile`, `docker-compose.yml`, GitHub Actions CI

---

## 3. Git Status & Remote Audit
- **Git Initialized:** Yes
- **Current Branch:** `main`
- **Remote Configured:** None
- **Push Status:** **NOT PUSHED YET**
- **Working Tree:** Clean (evaluation matrices, trained weights snapshot, and configs committed)

---

## 4. UI / UX Standards Compliance
- **Design System:** Clean botanical aesthetic with responsive grid, camera snap button, drag-and-drop dropzone, and clear confidence indicators.
- **Micro-Interactions:** Instant image preview, top-3 ranked guess cards with percentage confidence bars, and expandable botanical care drawers.
- **Language Switcher:** Instant toggle between English and Bangla without page reloads.

---

## 5. Deployment & Publishing Standard
- [x] **Dockerfile:** Multi-stage CPU-only PyTorch build with minimal footprint
- [x] **Docker Compose:** Configured `docker-compose.yml` for instant startup
- [x] **Automated Tests:** 82 automated unit, integration, and e2e tests passing
- [x] **Model Evaluation Artifacts:** Complete confusion matrix image and evaluation reports in `reports/`
- [x] **CI/CD:** Automated workflow in `.github/workflows/ci.yml`

---

## 6. How to Push to GitHub
1. Create a repository named `LeafCheck` on GitHub (`https://github.com/new`).
2. Run the following commands:
   ```bash
   cd /Users/arafatsheikh/D_Drive/github_project/project
   git remote add origin https://github.com/arafatsheikh098/LeafCheck.git
   git push -u origin main
   ```
*(Do not commit local virtualenvs or temporary test caches)*.
