# diag3: pass-through isolation test

The latest control log verifies that the crouch scanner and detours stayed
disabled. This package tests the next distinction: installing the detour
versus processing crouch state and replacing the pose weight.

## Run this test

1. Extract ROTK-diag3-windows-test.zip into a new folder.
2. Close H1Z1 and all ROTK Launcher processes.
3. Run 3-Run-Passthrough.cmd.
4. Confirm the launcher shows `1.4.5 (diag3: passthrough)`.
5. Play Combat Training and test clicking Respawn immediately after death.
   Report crashes, approximate time played, and FPS.
6. Keep C:\Games\ROTK\rotk-crouch-parity.log and any new crash dump.

Confirm the current PID logs `build=diag3 mode=passthrough`, followed by
`ADS-safe v14 installed` and `validation=install-only`. The probe should show
an installed animation detour. Unlike full hook mode, this mode should not
log crouch blend transitions, because their processing is bypassed.

The package includes control and full-hook scripts too, but the next requested
test is 3-Run-Passthrough.cmd. The scripts check for existing processes, keep
the console open, and save startup output. Self-updates remain disabled.
The existing game installation is reused; no H1Z1.exe disk edit is made.
Close both programs and run a previous launcher to restore its expected DLL.

## What changes in pass-through mode

It retains the startup memory scanner, live detour installation, pinned image
trampoline, installation-time validation, and 250 ms diagnostic probe.
At the start of the hook it immediately forwards the ten original arguments
without reading node_def/network, acquiring the crouch cache lock, processing
transitions, or replacing any animation weights. This restores the original
animation calculation through the installed detour.

Disassembly confirms the selected branch restores saved registers and jumps
to the image trampoline before the node-definition dereferences. This path
is shorter and uses a tail jump; its timing/stack behavior differs from the
full hook. A stable result would narrow the investigation, not prove that a
particular state read or animation weight caused the crashes. A matching
crash would implicate something still present, such as scanning, detour
mechanics, timing, or an underlying game issue.

Camera patching is off. Expensive per-call trampoline validation remains
removed. The normal build excludes diagnostic-only mode selection.

## Build and verification

```sh
ROTK_CRASH_DIAGNOSTIC=1 ZIG=/path/to/zig ZIG_GLOBAL_CACHE_DIR=/tmp/rotk-zig-cache \
  bash native/vivoxproxy/build-v5-compat.sh /tmp/rotk-diag3/vivoxsdk_x64.dll
python3 native/vivoxproxy/tests/test_crash_diagnostic.py
python3 native/vivoxproxy/tests/test_trampoline_validation.py
node scripts/package-crash-diagnostic.mjs /tmp/rotk-diag3/vivoxsdk_x64.dll diag3
```

Native cross-compilation with warnings as errors passed. Eight mocked worker
routing cases, 25 validator cases and the argument-forwarding test pass.
Native branch inspection confirms the pass-through bypass. Packaged hashes,
build labels and disabled updater are verified before release. Windows
launch scripts and gameplay still require the user test above.
