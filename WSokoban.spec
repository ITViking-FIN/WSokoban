# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('screens', 'screens'), ('icon.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # We don't use numpy at runtime — it gets pulled in transitively by
        # pygame/surfarray and bloats the build by ~12 MB.
        'numpy',
        # GUI toolkits, not used.
        'tkinter', '_tkinter', 'turtle', 'turtledemo',
        # Stdlib modules we don't touch.
        'unittest', 'doctest', 'pdb', 'pydoc',
        'distutils', 'setuptools', 'pip',
        # XML / web / email modules pygame doesn't need.
        'xml', 'xmlrpc', 'html', 'http',
        # IPython / debugger remnants.
        'IPython', 'jedi',
        # Numeric / data modules we don't use.
        'decimal', '_decimal', 'fractions', 'statistics',
        # File-format / DB modules we don't use.
        'sqlite3', '_sqlite3', 'csv', '_csv',
        'lzma', '_lzma', 'bz2', '_bz2',
        # Concurrency we don't use.
        'multiprocessing', 'concurrent',
        # Pygame submodules we don't use.
        'pygame.midi', 'pygame.camera', 'pygame.scrap',
        'pygame.movie', 'pygame.tests',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WSokoban',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
