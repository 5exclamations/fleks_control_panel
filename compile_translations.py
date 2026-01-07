#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для компиляции переводов без системных gettext tools
Использует библиотеку Babel
"""
import os
import sys
from pathlib import Path

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po
except ImportError:
    print("Babel не установлен. Установите его командой: pip install Babel")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
LOCALE_DIR = BASE_DIR / 'locale'

def compile_po_file(po_path, mo_path):
    """Компилирует .po файл в .mo файл"""
    try:
        with open(po_path, 'rb') as f:
            catalog = read_po(f)
        
        with open(mo_path, 'wb') as f:
            write_mo(f, catalog)
        
        print(f"[OK] Compiled: {po_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Error compiling {po_path.name}: {e}")
        return False

def main():
    if not LOCALE_DIR.exists():
        print(f"Directory {LOCALE_DIR} not found!")
        return
    
    compiled = 0
    failed = 0
    
    # Ищем все .po файлы
    for po_file in LOCALE_DIR.rglob('*.po'):
        mo_file = po_file.with_suffix('.mo')
        
        # Создаем директорию для .mo файла если нужно
        mo_file.parent.mkdir(parents=True, exist_ok=True)
        
        if compile_po_file(po_file, mo_file):
            compiled += 1
        else:
            failed += 1
    
    print(f"\nDone! Compiled: {compiled}, errors: {failed}")

if __name__ == '__main__':
    main()

