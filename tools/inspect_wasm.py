#!/usr/bin/env python3
"""
tools/inspect_wasm.py - Deep Static Inspection & Binary Deconstruction tool for WebAssembly modules.
Conforms to the official WebAssembly Binary Specification (v1.0).
"""

import sys
import os
import re
from typing import Tuple, List, Dict, Any


def read_leb128_u(data: bytes, offset: int) -> Tuple[int, int]:
    """Read an unsigned LEB128 integer from data starting at offset."""
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("Unexpected EOF reading LEB128 u")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, offset


def read_leb128_s(data: bytes, offset: int) -> Tuple[int, int]:
    """Read a signed LEB128 integer from data starting at offset."""
    result = 0
    shift = 0
    size = 32
    byte = 0
    while True:
        if offset >= len(data):
            raise ValueError("Unexpected EOF reading LEB128 s")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            break
    if shift < size and (byte & 0x40):
        result |= -1 << shift
    return result, offset


def read_string(data: bytes, offset: int) -> Tuple[str, int]:
    """Read a UTF-8 string prefixed with an unsigned LEB128 length."""
    length, offset = read_leb128_u(data, offset)
    s = data[offset:offset + length].decode('utf-8', errors='replace')
    return s, offset + length


SECTION_NAMES = {
    1: "Type",
    2: "Import",
    3: "Function",
    4: "Table",
    5: "Memory",
    6: "Global",
    7: "Export",
    8: "Start",
    9: "Element",
    10: "Code",
    11: "Data",
}

# Known mappings for minified symbols from waflash JavaScript runtime harness
EXPORT_MAPPINGS = {
    "pi": "linear_memory (WebAssembly.Memory)",
    "qi": "___wasm_call_ctors",
    "ri": "_Play",
    "si": "_Stop",
    "ti": "_reopenBuffer",
    "ui": "_invokeExternalCallback",
    "vi": "_strlen",
    "wi": "_free",
    "xi": "_main",
    "yi": "function_table (WebAssembly.Table)",
    "zi": "_malloc",
    "Ai": "___errno_location",
    "Bi": "_emscripten_builtin_memalign",
    "Ci": "_setThrew",
    "Di": "stackSave",
    "Ei": "stackRestore",
    "Fi": "stackAlloc",
    "Gi": "dynCall_jiji",
    "Hi": "dynCall_ji",
}


def inspect_wasm(filepath: str) -> Dict[str, Any]:
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "rb") as f:
        buf = f.read()

    # Header Verification
    magic = buf[:4]
    version = buf[4:8]

    if magic != b"\x00asm":
        raise ValueError(f"Invalid magic number: {magic!r}")
    if version != b"\x01\x00\x00\x00":
        raise ValueError(f"Unsupported WASM version: {version!r}")

    print("==================================================")
    print("      WAFLASH.WASM BINARY DECONSTRUCTION REPORT   ")
    print("==================================================")
    print(f"File: {filepath}")
    print(f"Binary Size: {len(buf):,} bytes ({len(buf) / (1024*1024):.2f} MB)")
    print(f"Header: Magic = '\\0asm', Version = 0x{version.hex()}")
    print("--------------------------------------------------\n")

    offset = 8
    sections: Dict[int, bytes] = {}

    while offset < len(buf):
        sec_id = buf[offset]
        offset += 1
        sec_len, offset = read_leb128_u(buf, offset)
        sec_bytes = buf[offset:offset + sec_len]
        sections[sec_id] = sec_bytes
        offset += sec_len

    results: Dict[str, Any] = {}

    # Section 1: Type
    if 1 in sections:
        t_data = sections[1]
        num_types, _ = read_leb128_u(t_data, 0)
        results['type_count'] = num_types
        print(f"[Section 1: Type] {num_types} function signatures declared.")

    # Section 2: Import
    if 2 in sections:
        i_data = sections[2]
        num_imports, off = read_leb128_u(i_data, 0)
        results['import_count'] = num_imports
        imports = []
        modules = {}
        for _ in range(num_imports):
            mod, off = read_string(i_data, off)
            field, off = read_string(i_data, off)
            kind = i_data[off]
            off += 1
            if kind == 0:  # Function
                sig, off = read_leb128_u(i_data, off)
            elif kind == 1:  # Table
                off += 1
                flags, off = read_leb128_u(i_data, off)
                initial, off = read_leb128_u(i_data, off)
                if flags & 1:
                    maxi, off = read_leb128_u(i_data, off)
            elif kind == 2:  # Memory
                flags, off = read_leb128_u(i_data, off)
                initial, off = read_leb128_u(i_data, off)
                if flags & 1:
                    maxi, off = read_leb128_u(i_data, off)
            elif kind == 3:  # Global
                off += 2
            imports.append((mod, field, kind))
            modules[mod] = modules.get(mod, 0) + 1

        results['imports'] = imports
        print(f"[Section 2: Import] {num_imports} imports from module(s): {modules}")

    # Section 3: Function
    if 3 in sections:
        f_data = sections[3]
        num_funcs, _ = read_leb128_u(f_data, 0)
        results['function_count'] = num_funcs
        print(f"[Section 3: Function] {num_funcs} internal function declarations.")

    # Section 4: Table
    if 4 in sections:
        tbl_data = sections[4]
        num_tables, off = read_leb128_u(tbl_data, 0)
        tables = []
        for _ in range(num_tables):
            elem_type = tbl_data[off]
            off += 1
            flags, off = read_leb128_u(tbl_data, off)
            initial, off = read_leb128_u(tbl_data, off)
            maxi = None
            if flags & 1:
                maxi, off = read_leb128_u(tbl_data, off)
            tables.append({'elem_type': elem_type, 'initial': initial, 'max': maxi})
        results['tables'] = tables
        print(f"[Section 4: Table] {num_tables} table(s): {tables}")

    # Section 5: Memory
    if 5 in sections:
        mem_data = sections[5]
        num_mems, off = read_leb128_u(mem_data, 0)
        mems = []
        for _ in range(num_mems):
            flags, off = read_leb128_u(mem_data, off)
            initial, off = read_leb128_u(mem_data, off)
            maxi = None
            if flags & 1:
                maxi, off = read_leb128_u(mem_data, off)
            mems.append({'initial_pages': initial, 'max_pages': maxi})
        results['memory'] = mems
        print(f"[Section 5: Memory] Initial: {mems[0]['initial_pages']} pages ({mems[0]['initial_pages'] * 64} KB), "
              f"Max: {mems[0]['max_pages']} pages ({mems[0]['max_pages'] * 64 / 1024:.0f} MB)")

    # Section 6: Global
    if 6 in sections:
        g_data = sections[6]
        num_globs, _ = read_leb128_u(g_data, 0)
        results['global_count'] = num_globs
        print(f"[Section 6: Global] {num_globs} global variables.")

    # Section 7: Export
    if 7 in sections:
        exp_data = sections[7]
        num_exps, off = read_leb128_u(exp_data, 0)
        exports = []
        print(f"[Section 7: Export] {num_exps} exported symbols:")
        for _ in range(num_exps):
            name, off = read_string(exp_data, off)
            kind = exp_data[off]
            off += 1
            idx, off = read_leb128_u(exp_data, off)
            mapped = EXPORT_MAPPINGS.get(name, "Unknown / Internal")
            exports.append({'name': name, 'kind': kind, 'index': idx, 'mapping': mapped})
            print(f"  - Alias: '{name}' | Kind: {kind} | Index: {idx} | Resolved: {mapped}")
        results['exports'] = exports

    # Section 11: Data & String Extraction
    if 11 in sections:
        d_data = sections[11]
        num_data, off = read_leb128_u(d_data, 0)
        print(f"\n[Section 11: Data] {num_data} segments (Total size: {len(d_data):,} bytes)")

        raw_strings = []
        for _ in range(num_data):
            memidx, off = read_leb128_u(d_data, off)
            opcode = d_data[off]
            off += 1
            if opcode == 0x41:  # i32.const
                _, off = read_leb128_s(d_data, off)
                assert d_data[off] == 0x0B
                off += 1
            size, off = read_leb128_u(d_data, off)
            chunk = d_data[off:off + size]
            off += size

            # Filter printable ASCII/UTF-8 strings min length 4
            matches = re.findall(rb'[\x20-\x7e]{4,}', chunk)
            for m in matches:
                raw_strings.append(m.decode('ascii'))

        # Categorize strings
        cpp_names = [s for s in raw_strings if '::' in s or 'AVM' in s or 'Crossbridge' in s or 'avmplus' in s]
        errors = [s for s in raw_strings if any(k in s.lower() for k in ['error', 'failed', 'invalid', 'exception', 'cannot', 'assert', 'null'])]
        as_tokens = [s for s in raw_strings if any(k in s for k in ['flash.', 'ActionScript', 'adobe', 'NetStream', 'DisplayObject', 'MovieClip', 'Sprite', 'Event', 'Stage'])]
        sys_calls = [s for s in raw_strings if any(k in s for k in ['GL_', 'emscripten', 'pthread', 'syscall', 'POSIX', 'fopen', 'malloc', 'free', 'socket', 'http'])]

        results['strings'] = {
            'total_extracted': len(raw_strings),
            'cpp_names_count': len(cpp_names),
            'errors_count': len(errors),
            'as_tokens_count': len(as_tokens),
            'sys_calls_count': len(sys_calls),
        }

        print("\n--- String Pool Categorization ---")
        print(f"Total Printable ASCII Strings (len >= 4): {len(raw_strings):,}")
        print(f"  1. C++ Class Names / Namespaces: {len(cpp_names):,}")
        print(f"     Sample: {cpp_names[:3]}")
        print(f"  2. Error Messages & Assertions:   {len(errors):,}")
        print(f"     Sample: {errors[:3]}")
        print(f"  3. ActionScript Tokens & APIs:    {len(as_tokens):,}")
        print(f"     Sample: {as_tokens[:3]}")
        print(f"  4. System Calls & Runtime Tokens: {len(sys_calls):,}")
        print(f"     Sample: {sys_calls[:3]}")

    print("\n==================================================")
    print("              INSPECTION COMPLETE                 ")
    print("==================================================")
    return results


if __name__ == "__main__":
    wasm_file = sys.argv[1] if len(sys.argv) > 1 else "waflash.wasm"
    inspect_wasm(wasm_file)
