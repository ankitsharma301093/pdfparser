@echo off
REM Build Windows exe for PDF Parser
REM Run from the project root with the venv activated

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "PDFParser" ^
  --add-data "app.py;." ^
  --add-data "parser_pdf.py;." ^
  --add-data "recovery.py;." ^
  --add-data "diagnostics.py;." ^
  --add-data "exporter.py;." ^
  --hidden-import streamlit ^
  --hidden-import fitz ^
  launcher.py

echo.
echo Build complete. Executable is in dist\PDFParser.exe
