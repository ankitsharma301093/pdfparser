#!/bin/bash
# Build macOS app for PDF Parser
# Run from the project root with the venv activated

pyinstaller \
  --onefile \
  --windowed \
  --name "PDFParser" \
  --add-data "app.py:." \
  --add-data "parser_pdf.py:." \
  --add-data "recovery.py:." \
  --add-data "diagnostics.py:." \
  --add-data "exporter.py:." \
  --hidden-import streamlit \
  --hidden-import fitz \
  launcher.py

echo "Build complete. App is in dist/PDFParser"
