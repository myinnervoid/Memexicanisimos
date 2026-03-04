#!/usr/bin/env python3
"""Syntax check for v5.2 modified files."""
import py_compile

files = [
    "installer/config.py",
    "installer/project_manager.py",
    "installer/memory_tools.py",
    "installer/installer_core.py",
    "daemon/genesis_protocol.py",
    "memex_gui.py",
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  ✅ {f}")
    except py_compile.PyCompileError as e:
        print(f"  ❌ {f}: {e}")
