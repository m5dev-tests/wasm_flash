# WAFlash Core Engine: Deep Static & Structural Analysis Report

## Executive Summary

This report provides a comprehensive architectural teardown and static reverse-engineering analysis of the core engine binary `waflash.wasm` via its 25MB decompiled C-like pseudocode representation (`docs/decompiled/waflash_decompiled.dcmp`), generated using `wasm-decompile` from the WebAssembly Binary Toolkit (WABT).

Through static code slicing and symbolic memory tracing, we have decoded the underlying implementation details of the primary WebAssembly exported entry points:
- **`xi` (`_main`)**: Application startup, command-line parameter parsing, MEMFS virtual file system setup, and preloader initialization.
- **`ri` (`_Play`)**: Resumes/starts SWF playhead progression and timeline frame tickers.
- **`si` (`_Stop`)**: Pauses/halts SWF timeline frame execution.
- **`ti` (`_reopenBuffer`)**: Audio buffer re-synchronization hook stub.
- **`ui` (`_invokeExternalCallback`)**: ActionScript `ExternalInterface` JavaScript bridge dispatcher and argument marshaller.
- **`zi` (`malloc`) & `wi` (`free`)**: High-performance dynamic heap allocation protocol based on `dlmalloc`.

---

## Exported Alias Resolution Table

| Minified Export | WASM Symbol Index | Native C/C++ Binding | Function & Subsystem Purpose |
| :--- | :--- | :--- | :--- |
| **`xi`** | Function 10162 | `_main` | Core initialization entry point (`argc`, `argv` parsing). |
| **`ri`** | Function 10298 | `_Play` | Playhead resume / state machine activator. |
| **`si`** | Function 9667 | `_Stop` | Playhead pause / state machine suspend. |
| **`ti`** | Function 690 | `_reopenBuffer` | Audio ring buffer re-alignment hook. |
| **`ui`** | Function 8140 | `_invokeExternalCallback` | ActionScript `ExternalInterface` JS interop dispatcher. |
| **`zi`** | Function 543 | `_malloc` | Dynamic heap block allocator (`dlmalloc`). |
| **`wi`** | Function 523 | `_free` | Dynamic heap block deallocator (`dlmalloc`). |
| **`pi`** | Memory 0 | `memory` | WebAssembly Linear Memory ArrayBuffer (`WebAssembly.Memory`). |
| **`yi`** | Table 0 | `table` | Function indirect call table (`funcref`). |

---

## 1. Subsystem 1: Core Entry Point & Startup Parameter Parsing (`export function xi` -> `_main`)

### Decompiled Function Signature & Primary Block
```c
export function xi(a:int, b:int):int {
  var f:int_ptr;
  var d:int;
  var i:int;
  var e:int;
  var h:int;
  var l:int;
  var m:int;
  var k:int_ptr;
  var o:int_ptr;
  var g:int = g_a - 4560;
  g_a = g;

  // Clean stack frame workspace
  f_ls(g + 4144, 0, 128);
  var c:int = a_p(994983, 109824, 0);
  if (c) {
    d = g + 4144;
    f_nya(d, c, f = select_if(f = vi(c), 127, f < 127));
    (d + f)[0]:byte = 0;
    wi(c);
  }

  // SWF URL Parameter Handling (argv[1])
  f_ls(g + 48, 0, 4096);
  c = a_p(995194, 109824, 0);
  if (c) {
    d = g + 48;
    f_nya(d, c, f = select_if(f = vi(c), 4095, f < 4095));
    (d + f)[0]:byte = 0;
    wi(c);
    goto B_b;
  }
  c = g + 48;
  f_nya(c, d = b[1]:int, d = select_if(d = vi(d), 4095, d < 4095));
  (c + d)[0]:byte = 0;

  label B_b:
  c = a_p(995836, 109824, 0);
  d = c != 0;

  // Parameter 3: Renderer Backend ("webgl" vs "default")
  if (a < 4) goto B_d;
  f = b[3]:int; // argv[3]
  if (f) { d = eqz(f_vt(f, 54958, 5)) | c != 0 } // Address 54958 = "webgl"

  // Parameter 4: ActionScript Filter Toggle ("0" = enabled, "1" = disabled)
  if (a < 5) goto B_d;
  c = b[4]:int; // argv[4]
  if (eqz(c)) goto B_d;
  if (c[0]:ubyte != 49) goto B_d; // 49 = ASCII "1"
  1005552[0]:byte = 1;            // Set disableFilters global flag

  label B_d:
  c = a_p(996017, 109824, 0);
  if (c) {
    f_nya(1005488, c, f = select_if(f = vi(c), 63, f < 63));
    (f + 1005488)[0]:byte = 0;
    wi(c);
    goto B_f;
  }
  1005492[0]:short = d_iu09AFaf44functionExternalMe[40251]:ushort@1;
  1005488[0]:int = d_iu09AFaf44functionExternalMe[40247]:int@1;

  label B_f:
  // Analytics & Logging Telemetry
  a_oh(86286); // Address 86286 = "UA-168755014-1"
  g[3]:long = 220918152613L;
  g[5]:int = 84251; // Engine Version String = "2.8.27"
  g[4]:int = select_if(43, 45, d);
  a_S(513, 109025, g + 16); // Address 109025 = "WAFLASH> Waflash %c WebAssembly Flash v%s (%llu)\n"

  // VFS / Shared Object Setup
  g[0]:int = 50244; // Address 50244 = "/waflashso"
  a_p(993777, 1024, g);

  // Engine State Allocation (1120 bytes)
  f = f_zbb(1120);
  c = f;
  c[277]:long@4 = 0L;
  c[1106]:byte = 0;
  c[552]:short = 0;
  c[546]:short = 0;
  c[272]:int = 1;
  c[135]:long = 4607182418800017408L;
  c[130]:long = 0L;
  c[129]:long = 1L;
  c[1]:int = 0;
  c[0]:int = 109836;
  c[1093]:byte = a_p(993939, 109824, 0) != 0;

  // Store Global Core Instance Pointer
  1005556[0]:int = f;
  ...
}
```

### Parameter Access & Schema

Function `xi` implements standard C `main(int argc, char** argv)` conventions:
- `a`: `argc` integer representing parameter count.
- `b`: `argv` pointer pointing to an array of string pointers in linear memory `pi`.

```
argv Array in Linear Memory:
  b[0] -> Ptr to Executable Name ("waflash.wasm")
  b[1] -> Ptr to SWF URL String (e.g., "https://domain.com/game.swf")
  b[2] -> Ptr to Subsystem Flag ("0")
  b[3] -> Ptr to Renderer Selector ("webgl" or "default")
  b[4] -> Ptr to Filter Toggle Flag ("0" or "1")
```

1. **SWF URL Parsing (`argv[1]`):**
   - The engine checks if an environment override exists via `a_p`.
   - If not, `b[1]` is fetched, its string length is calculated via `vi` (`_strlen`), and it is copied into stack buffer `g + 48` (capped at 4,095 bytes) via `f_nya` (`strncpy`).

2. **Graphics Renderer Backend (`argv[3]`):**
   - The engine examines `b[3]` (`argv[3]`).
   - String comparison is executed against literal address `54958` (`"webgl"`).
   - If `argv[3]` matches `"webgl"`, boolean flag `d` is toggled ON (`1`), selecting hardware-accelerated WebGL rendering routines instead of 2D canvas blitting.

3. **ActionScript DisplayObject Filter Toggle (`argv[4]`):**
   - The engine checks `b[4]` (`argv[4]`).
   - If `b[4][0] == '1'` (ASCII value 49), global memory flag `1005552[0]:byte` is set to `1`. This bypasses CPU/GPU filter passes (e.g. BlurFilter, DropShadowFilter) to optimize performance on low-end hardware.

4. **Virtual File System (MEMFS) & Engine Initialization:**
   - Registers analytics via `a_oh("UA-168755014-1")`.
   - Logs startup banner via `a_S` using version string `"2.8.27"` (address `84251`).
   - Mounts virtual storage directory `"/waflashso"` (address `50244`) for Flash SharedObjects (`LocalConnection` / `SharedObject` persistence).
   - Allocates **1,120 bytes** for the primary engine context instance `f` using `f_zbb` (calloc wrapper) and stores the pointer at global memory address `1005556[0]`.

---

## 2. Subsystem 2: Playhead & Timeline Loop (`export function ri` -> `_Play` & `export function si` -> `_Stop`)

### Decompiled Code Implementation

```c
// export function ri: Resumes SWF timeline and event execution
export function ri() {
  var a:int_ptr = 1005556[0]:int; // Fetch Core Engine Instance Pointer
  if (a) {
    a[258] = 5;                  // Set Playhead State Flag = 5 (STATE_PLAYING)
  }
}

// export function si: Pauses SWF timeline and event execution
export function si() {
  var a:int_ptr = 1005556[0]:int; // Fetch Core Engine Instance Pointer
  if (a) {
    a[258] = 6;                  // Set Playhead State Flag = 6 (STATE_PAUSED)
  }
}
```

### State Flag Architecture & Timeline Control

- Both `ri` and `si` query global memory address `1005556[0]`, which stores the primary engine instance context object `a`.
- The engine playback state is controlled via offset `258` (`a[258]`):
  - **`a[258] = 5` (`STATE_PLAYING`)**: Activates the timeline engine ticker. On each frame request (`requestAnimationFrame`), ActionScript bytecodes are executed, MovieClips step frame markers, user input events are dispatched, and WebGL draw calls are queued.
  - **`a[258] = 6` (`STATE_PAUSED`)**: Suspends timeline progression. ActionScript execution and DisplayObject transform updates are halted, while leaving rendering buffers intact.

---

## 3. Subsystem 3: Audio Subsystem Re-synchronization (`export function ti` -> `_reopenBuffer`)

### Decompiled Code Implementation

```c
export function ti(a:int, b:int, c:int):int {
  return 0;
}
```

### Audio Synchronization Architecture

- In the decompiled C++ core, function `ti` (`_reopenBuffer`) accepts three integer arguments and immediately returns `0` (success status).
- **Host / WASM Division of Labor:**
  - In WAFlash, audio sample generation and ring-buffer streaming are managed by host WebAudio JavaScript bindings in `waflash.min.js` (under module `"a"` imports, including `alGetSourcei`, `ScriptProcessorNode`, and `AudioContext`).
  - Function `ti` serves as the WASM entry point stub for `_reopenBuffer`. When browser tab focus toggles or audio devices change, host JavaScript calls `ti` to signal WASM audio synchronization, while executing WebAudio context suspension, buffer flushing, and sample-rate re-alignment on the JS side.

---

## 4. Subsystem 4: ActionScript JavaScript Bridge (`export function ui` -> `_invokeExternalCallback`)

### Decompiled Code Implementation

```c
export function ui(a:{ a:int, b:int }, b:int):int {
  var n:int_ptr;
  var o:int_ptr;
  var d:int_ptr;
  var e:int_ptr;
  var f:int_ptr;
  var l:int_ptr;
  var r:int;
  var q:int;
  var t:int;
  var h:int_ptr;
  var g:int_ptr;
  var j:int_ptr;
  var s:int;
  var v:int;
  var i:int_ptr;
  var w:int;

  var p:int_ptr = g_a - 32;
  g_a = p;

  var c:int = 1005556[0]:int; // Core Engine Instance
  if (c) {
    c[1]:int;
    c = p + 8;
    c[0]:int = c[0]:int & -4;
    var u:int_ptr = 1005556[0]:int;

    // Unpack ActionScript parameters into WASM stack structures
    f_cta(u[1], n = p + 24, a);
    f_cta(u[1], o = p + 16, b);
    b = u[1];
    a = c;

    var k:int = g_a - 16;
    g_a = k;

    if (eqz(b)) goto B_b;
    if (eqz(n)) goto B_b;
    if (eqz(o)) goto B_b;
    if (eqz((b + 1196)[0]:int)) goto B_b;
    if (eqz(f_ata(b, n))) goto B_b;

    d = ((b + 1196)[0]:int)[5]:int;
    if (eqz(d)) goto B_c;

    c = n[1];
    // Address 38648 = "_callbacks"
    d = f_tx(d, 38648, f_xv(38648) & 65535, 0);
    if (eqz(d)) goto B_c;
    ...
    // Address 54722 = "call"
    f_fw(d, 54722, 2, k + 4, k + 12);
    ...
  }
  g_a = p + 32;
  return d;
}
```

### ActionScript Parameter Marshalling Protocol

1. **Host Unpacking:**
   - Function `ui` receives callback parameters (`a` and `b`) passed across the WASM boundary from ActionScript `flash.external.ExternalInterface`.
   - `f_cta` converts high-level ActionScript runtime value wrappers into stack-allocated structure pointers `n` (`p + 24`) and `o` (`p + 16`).

2. **Callback Lookup:**
   - Quayside lookup is performed on object map string address `38648` (`"_callbacks"`).
   - `f_tx` validates whether the requested method string is registered in the Flash `ExternalInterface` registry.

3. **Host Execution:**
   - Function `f_fw` dispatches an indirect execution call to host JavaScript method address `54722` (`"call"`).
   - Primitive data types (Strings, Numbers, Booleans, Objects) are serialized into UTF-8 C-strings or 64-bit IEEE 754 floats and marshalled across the linear memory boundary (`pi`).
   - The returned JS result is packed back into an ActionScript runtime object reference and returned to the AVM execution context.

---

## 5. Subsystem 5: Dynamic Memory Management Allocation Protocol (`export function zi` -> `malloc` & `wi` -> `free`)

The WAFlash engine embeds Doug Lea's `dlmalloc` (ptmalloc variant) directly within the WebAssembly module.

### Allocation Implementation (`export function zi` -> `malloc`)

```c
export function zi(a:int):int {
  var h:int_ptr;
  var c:int;
  var k:int;
  ...
  var l:int = g_a - 16;
  g_a = l;

  // Fast-Path: Smallbin Allocations (size <= 244 bytes)
  if (a <= 244) {
    g = 1080908[0]:int; // Smallbin Bitmask
    b = g >> (c = (h = select_if(16, a + 11 & -8, a < 11)) >> 3);
    if (b & 3) {
      d = ((b ^ -1) & 1) + c;
      b = d << 3;
      e = (b + 1080956)[0]:int; // Bin Header Array
      a = e + 8;
      c = e.c;
      if (c == (b = b + 1080948)) {
        1080908[0]:int = g & -2 << d; // Update bitmask
        goto B_n;
      }
      c[3]:int = b;
      b.c = c;
      label B_n:
      e.b = (b = d << 3) | 3; // Set chunk size & PREV_INUSE flags
      b = b + e;
      b.b = b.b | 1;
      goto B_a;
    }
    ...
  }

  // Treebin Allocations (> 244 bytes) & Heap Expansion
  // Address 1081212 = Treebin Root Array Header
  ...
}
```

### Deallocation Implementation (`export function wi` -> `free`)

```c
export function wi(a:int_ptr) {
  var b:int_ptr;
  var e:{ a:int, b:int, c:int };
  var c:int_ptr;
  var h:int_ptr;
  var g:int_ptr;

  if (eqz(a)) goto B_a;

  var d:int = a - 8; // Access Chunk Header Prefix
  var f:int_ptr = d + (a = (b = (a - 4)[0]:int) & -8);

  if (b & 1) goto B_b;
  if (eqz(b & 3)) goto B_a;

  // Forward and Backward Coalescing
  d = d - (b = d[0]:int);
  if (d < 1080924[0]:int) goto B_a;
  a = a + b;

  if (d != 1080928[0]:int) {
    if (b <= 255) {
      c = d[2]:int;
      c == ((e = b >> 3) << 3) + 1080948;
      if (c == (b = d[3]:int)) {
        1080908[0]:int = 1080908[0]:int & -2 << e;
        goto B_b;
      }
      c[3] = b;
      b[2] = c;
      goto B_b;
    }
    ...
  }
}
```

### Dynamic Heap Topology & Subsystem Heap Segregation

```
+-------------------------------------------------------------------------------+
|                       WASM LINEAR MEMORY MAP (pi)                             |
+-------------------+--------------------+------------------+-------------------+
| Static Data &     | WASM Stack Space   | Dynamic Heap     | Unallocated Growth|
| Segments (0-1MB)  | (g_a pointer)      | (dlmalloc)       | Upper Bound (2GB) |
+-------------------+--------------------+------------------+-------------------+
0                   1,005,488            1,080,908          32,768 Pages
```

1. **Chunk Boundaries & Overhead:**
   - Allocations include an 8-byte header stored at `ptr - 8`.
   - Low-order bits store flags: bit 0 = `PREV_INUSE`, bit 1 = `IS_MMAPPED`.

2. **Smallbins ($\le 244$ Bytes):**
   - Bins are indexed at byte offsets starting at `1080948`.
   - Allocation fast-path utilizes bitmask `1080908` to locate free chunks in $O(1)$ time.

3. **Treebins ($> 244$ Bytes):**
   - Larger chunks are managed via treebin root structures stored at offset `1081212`.

4. **Linear Memory Growth (`memory.grow` / `pi`):**
   - Top chunk pointer resides at `1080932`. When the top chunk is exhausted, `sbrk` requests expand WebAssembly linear memory (`pi`) up to `32,768` pages (2 GB upper limit).

5. **Subsystem Memory Segregation:**
   - **WebGL Texture Buffers:** Allocated using `_emscripten_builtin_memalign` (`Bi`) to guarantee 16-byte alignment required for SIMD and GPU texture uploads.
   - **ActionScript Garbage Collector Heap:** Allocates fixed-size cell blocks via `zi` (`malloc`), managing object lifetimes via interior reference counting and GC sweeps.
   - **Audio Ring Buffers:** Audio sample arrays operate in dedicated heap buffers, exposed to WebAudio via offset pointers in linear memory `pi`.

---

## 6. Key Takeaways & Portability Strategy for WAFlash-ReFlexed

For building the `WAFlash-ReFlexed` C++ Libretro core or native embedder bridge, these decompiled code insights provide clear implementation guidelines:

1. **Native Entry Point Invocation:**
   - Construct `argc = 5` and pass parameters matching the 4-argument schema:
     `["waflash.wasm", swfUrl, "0", rendererMode, disableFiltersFlag]`
2. **Timeline Engine Driver:**
   - Drive frame ticks by inspecting core state at engine context `1005556[0]`:
     - Toggle playback via state flag `a[258]` (`5` for play, `6` for pause).
3. **Audio Pipeline Integration:**
   - Provide host Libretro PCM audio buffer pumping while referencing `_reopenBuffer` (`ti`) for audio state realignment.
4. **ExternalInterface Bridge Emulation:**
   - Handle string and parameter serialization across the WASM boundary to expose native C++ callbacks to ActionScript's `ExternalInterface`.
