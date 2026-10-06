# WAFLASH Core Engine: Technical Architecture & Binary Analysis Report

## Executive Summary

This report presents a comprehensive binary deconstruction and reverse-engineering teardown of `waflash.wasm`, the core WebAssembly emulation engine powering WAFlash. WAFlash is a high-performance ActionScript 2 (AS2) and ActionScript 3 (AS3) Flash emulation runtime.

Despite being a stripped binary with minified export aliases, deep static binary analysis combined with runtime JS harness deconstruction reveals the exact compilation fingerprint, memory topology, syscall dependencies, exported runtime interface, and recovered source-level C++ artifacts.

### Key Binary Metadata
- **File Name:** `waflash.wasm`
- **File Size:** 7,301,986 bytes (~6.96 MB)
- **Format:** WebAssembly Binary Format (`\0asm` magic, version `0x01`)
- **Compilation Toolchain:** Emscripten (LLVM/Clang) compiling an Adobe Flash / AVMPlus (ActionScript Virtual Machine) C++ codebase (incorporating Crossbridge/FlASCC lineage and Fastable optimizations).

---

## 1. WebAssembly Binary Section Topology

Analysis with `tools/inspect_wasm.py` reveals the following structure across standard WebAssembly sections (IDs 1–11):

| Section ID | Section Name | Count / Size | Technical Description |
| :--- | :--- | :--- | :--- |
| **Section 1** | Type | 98 signatures | Standard function signatures used across internal & imported calls. |
| **Section 2** | Import | 500 imports | All host functions imported under module `"a"`. |
| **Section 3** | Function | 9,799 functions | Declared internal WebAssembly C/C++ engine functions. |
| **Section 4** | Table | 1 table | Function pointer indirect call table (Elem type `funcref`/`0x70`, initial/max size 12,865). |
| **Section 5** | Memory | 1 memory | Linear memory page descriptor (Initial: 256 pages / 16MB, Max: 32,768 pages / 2048MB). |
| **Section 6** | Global | 1 global | WebAssembly internal mutable heap/stack pointer global. |
| **Section 7** | Export | 19 symbols | Exported functions, linear memory, and function table (minified identifiers). |
| **Section 9** | Element | 25,734 bytes | Function table initializers mapping indirect call indices. |
| **Section 10** | Code | 6,317,076 bytes | Executable WebAssembly bytecode instructions (9,799 function bodies). |
| **Section 11** | Data | 2,418 segments | Embedded string tables, virtual method tables (vtables), and static data (944,957 total bytes). |

---

## 2. Memory Architecture & Sizing

The WASM module manages linear memory through a single WebAssembly Memory export (`pi`).

- **Base Allocation:** `256 pages` = **16 MB** ($256 \times 64\text{ KB}$).
- **Maximum Heap Sizing:** `32,768 pages` = **2,048 MB** (**2 GB** upper bound).
- **Page Alignment:** Standard WebAssembly 64 KB alignment ($65,536\text{ bytes}$).
- **Heap Growth Dynamic:** Memory expands dynamically via `emscripten_builtin_memalign` (`Bi`) and `sbrk` / `malloc` calls up to 2 GB as ActionScript assets, SWF bitmaps, and Audio buffers are loaded.
- **Data Section Offset:** Static data, vtables, and string constants occupy `2,418` segments totaling **944,957 bytes** initialized at WASM instantiation.

---

## 3. Exported Symbols Catalog & Minified Mapping

The compiled WASM module exports 19 symbols. In the compiled binary, these symbols use minified two-letter identifiers (`pi` through `Hi`). Cross-referencing with the JS loader (`waflash.min.js`) yields the exact C/C++ entry points:

| Minified Export | Symbol Kind | WASM Index | Resolved Native C/C++ Entry Point | Function / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`pi`** | Memory | 0 | `memory` | WebAssembly linear memory ArrayBuffer (`WebAssembly.Memory`). |
| **`yi`** | Table | 0 | `table` | WebAssembly indirect function pointer table (`WebAssembly.Table`). |
| **`xi`** | Function | 10162 | `_main` | Core execution entry point initializing SWF playback. |
| **`qi`** | Function | 2559 | `___wasm_call_ctors` | C++ global static constructors caller. |
| **`ri`** | Function | 10298 | `_Play` | Resumes or starts SWF frame rendering and event processing. |
| **`si`** | Function | 9667 | `_Stop` | Pauses SWF playback loop. |
| **`ti`** | Function | 690 | `_reopenBuffer` | Audio buffer state re-initialization hook. |
| **`ui`** | Function | 8140 | `_invokeExternalCallback` | ActionScript `ExternalInterface` JS callback dispatcher. |
| **`vi`** | Function | 548 | `_strlen` | C-string length calculator operating on WASM heap pointers. |
| **`wi`** | Function | 523 | `_free` | Standard C dynamic heap deallocation. |
| **`zi`** | Function | 543 | `_malloc` | Standard C dynamic heap allocation. |
| **`Ai`** | Function | 4087 | `___errno_location` | Returns pointer to POSIX `errno` in WASM heap. |
| **`Bi`** | Function | 4069 | `_emscripten_builtin_memalign` | Aligned memory allocation for WebGL buffers and SIMD structures. |
| **`Ci`** | Function | 4068 | `_setThrew` | Emscripten exception handling state updater. |
| **`Di`** | Function | 4065 | `stackSave` | Saves current WebAssembly stack pointer state. |
| **`Ei`** | Function | 4064 | `stackRestore` | Restores saved WebAssembly stack pointer state. |
| **`Fi`** | Function | 4063 | `stackAlloc` | Allocates temporary stack memory on the WASM stack. |
| **`Gi`** | Function | 4062 | `dynCall_jiji` | Dynamic indirect function call dispatcher (`jiji` signature). |
| **`Hi`** | Function | 4061 | `dynCall_ji` | Dynamic indirect function call dispatcher (`ji` signature). |

---

## 4. Host Syscalls & JavaScript Imports

The WASM binary imports **500 functions** from the browser environment, all grouped under the import module namespace `"a"`. The JavaScript runtime (`waflash.min.js`) constructs these bindings to bridge WASM C++ engine functions to browser Web APIs:

1. **WebGL / Canvas Rendering Subsystem:**
   - Shaders, texture creation, framebuffers (`glCreateShader`, `glBindTexture`, `glDrawElements`).
   - Handles browser canvas fallback modes (`webgl` target vs. `default` 2D context).
2. **WebAudio & Sound System:**
   - ScriptProcessorNode & MediaStream audio streaming (`_reopenBuffer`, `vi` callbacks).
   - AudioContext sample rate conversion, panning, 3D audio listener positioning (`coneInnerAngle`, `rolloffFactor`).
3. **POSIX & Emscripten File System (FS):**
   - Virtual File System (`MEMFS`) operations (`FS_createDataFile`, `FS_createPreloadedFile`, `open`, `read`, `write`, `close`).
   - Asynchronous asset fetcher storing SWF assets and HTTP resources in MEMFS.
4. **DOM & ExternalInterface Integration:**
   - ActionScript `flash.external.ExternalInterface` calls dispatched into host JS environment via `_invokeExternalCallback`.

---

## 5. Runtime Argument Protocol (4-Parameter Execution Schema)

The loader initialization method `createWaflash(swfUrl, options)` invokes `_main` (`xi`) with a strict **4-parameter schema** passed in Emscripten's `arguments` array:

$$\text{arguments} = [\text{Parameter 0}, \text{Parameter 1}, \text{Parameter 2}, \text{Parameter 3}]$$

```js
arguments: [
    swfUrl,                         // Parameter 0
    "0",                            // Parameter 1
    options.gpu ? "webgl" : "default", // Parameter 2
    options.enableFilters ? "0" : "1"  // Parameter 3
]
```

### Parameter Breakdown
- **Parameter 0 (`swfUrl`):** UTF-8 string path or URL pointing to the primary SWF file asset to load and execute.
- **Parameter 1 (`subsystem`):** Subsystem mode flag (default `"0"` indicating standard SWF application execution).
- **Parameter 2 (`renderer`):** Graphics backend selector (`"webgl"` enables WebGL GPU hardware acceleration; `"default"` uses standard 2D canvas blitting).
- **Parameter 3 (`disableFilters`):** ActionScript DisplayObject filter processing toggle (`"0"` enables Stage/DisplayObject bitmap filters such as BlurFilter, DropShadowFilter; `"1"` disables filter processing for performance optimization).

---

## 6. Recovered Internal Source Artifacts & Strings

Parsing Section 11 (Data) with `tools/inspect_wasm.py` extracted **12,311 printable ASCII strings** ($\ge 4$ chars). These strings expose original Adobe, AVMPlus, and Crossbridge source code metadata:

### A. C++ Class Names & Namespaces (811 recovered)
- `adobe.utils::XMLUI$::setProperty`, `adobe.utils::XMLUI$::getProperty`
- `flash.media::Camera::setQuality`
- `flash.external::ExtensionContext$::_getExtensionDirectory`
- `flash.text.engine::TextBlock::findNextAtomBoundary`
- `avmplus::NativeID`, `AVMPlus` engine internals revealing Adobe Flash Player 11+ / AVM2 core lineage.

### B. ActionScript Tokens & Class Definitions (1,459 recovered)
- `http://www.adobe.com/2006/actionscript/flash/proxy`
- `NetStream.Buffer.Empty`, `NetStream.Play.StreamNotFound`
- `flash.accessibility`, `flash.display.MovieClip`, `flash.display.Sprite`, `flash.events.Event`

### C. Error Messages & Assertions (436 recovered)
- `invalid index`
- `flash.net.drm::DRMManager::errorCodeToThrow`
- `DRMContentData::errorCodeToThrow`
- `Invalid window`, `Out of memory`

### D. System Call & Graphics Tokens (544 recovered)
- `GL_SGIX_list_priority`, `GL_ARB_compatibility`, `GL_ARB_ES2_compatibility`, `GL_NV_vertex_buffer_unified_memory`

---

## 7. Integration Implications for Re:Flexed

These findings provide direct architectural guidance for integrating WAFlash engine binaries into the Re:Flexed Libretro core and native WebAssembly bridge:

1. **Memory Provisioning:**
   - Re:Flexed must allocate an initial WASM linear memory heap of at least **16 MB** with growth capability up to **2 GB**.
2. **Symbol Binding:**
   - Native C/C++ bridges (e.g. via Wasmtime, Wasmer, or native WASM embedders) must map WASM exported aliases (`xi`, `zi`, `wi`, `Di`, `Ei`, `ri`, `si`) to their corresponding native C wrappers (`_main`, `malloc`, `free`, `stackSave`, `stackRestore`, `_Play`, `_Stop`).
3. **Execution Schema:**
   - Core initialization routines must construct `argc=5` / `argv` arrays matching the 4-parameter execution schema (`[executable, swfUrl, "0", renderer, disableFilters]`).
4. **Host Syscall Emulation:**
   - System calls under module `"a"` must be backed by Libretro environment callbacks for frame video rendering, PCM audio sample buffer pumping, and input event polling.
