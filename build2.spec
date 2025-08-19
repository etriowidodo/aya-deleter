# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
block_cipher = None

added_files = [('AYA.ico', '.')]  # include icon

a = Analysis(
    ['aya_delete_folder2.py'],
    pathex=['D:\\KERJAAN\\experiment\\aya_hapus_super_cepat'],
    binaries=[],
    datas=added_files,
    hiddenimports=['psutil._psutil_windows'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='AYA_DELETER',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='AYA.ico',
    onefile=True,  # single exe
)

