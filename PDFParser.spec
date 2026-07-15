# PyInstaller spec — bundles the Streamlit app and all dependencies into one exe.
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

for pkg in ('streamlit', 'fitz', 'pymupdf', 'altair', 'pydeck'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Our application modules
datas += [
    ('app.py', '.'),
    ('parser_pdf.py', '.'),
    ('recovery.py', '.'),
    ('diagnostics.py', '.'),
    ('exporter.py', '.'),
]

hiddenimports += [
    'streamlit.runtime.scriptrunner.magic_funcs',
    'streamlit.runtime.caching.storage.dummy_cache_storage',
]

a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PDFParser',
    debug=False,
    strip=False,
    upx=True,
    console=False,  # no console window
    icon=None,
)
