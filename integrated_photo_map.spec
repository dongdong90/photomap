# -*- mode: python ; coding: utf-8 -*-
"""
照片地图打包配置文件
版本: v0.9
功能: 打包照片地图应用程序，包含所有依赖和资源文件
"""

block_cipher = None

a = Analysis(
    ['integrated_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('utils.py', '.'),
        ('map_generator.py', '.'),
        ('ReadMe.md', '.'),
        ('alipay_qrcode.png', '.'),
        ('wechat_qrcode.png', '.'),
        ('app_icon.ico', '.'),
        ('photo_map.ico', '.'),
        ('logs/*', 'logs'),
        ('unified_photo_temp/*', 'unified_photo_temp'),
        ('unified_photo_temp_heic/*', 'unified_photo_temp_heic')
    ],
    hiddenimports=[
        'exifread',
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'piexif',
        'pillow_heif',
        'jinja2',
        'concurrent.futures',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'webbrowser',
        'json',
        'threading',
        'datetime',
        'os',
        'logging',
        'math',
        'base64',
        'sys',
        'time'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='照片地图',
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
    icon='app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='照片地图'
)