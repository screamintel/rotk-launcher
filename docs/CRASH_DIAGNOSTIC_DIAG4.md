# diag4: scanner-only isolation test

## Next test

1. Extract ROTK-diag4-windows-test.zip into a new folder.
2. Close H1Z1 and all ROTK Launcher processes.
3. Run 4-Run-Scanner-Only.cmd.
4. Confirm the launcher shows `1.4.5 (diag4: scanner-only)`.
5. In Combat Training, repeat clicking Respawn immediately after death.
   Record whether it crashes, approximate time played, and FPS.
6. Copy the updated game-folder rotk-crouch-parity.log and any new dump.

The game folder remains C:\Games\ROTK for the existing installation. The
log must include the current PID, `build=diag4 mode=scanner-only`, and
`SCANNER-ONLY active scanner=complete detours=off`. Its probe should retain
the stock animation entry. There should be no successful hook-installation
or crouch-blend transition entries for that PID.

Use only the scanner-only script for this comparison. The other scripts
remain available but are not the next requested test. Self-updates are
disabled. Scripts check for existing processes and keep startup results
visible. Roll back by closing both programs and using a previous launcher.

## Purpose and limits

Control runs skipped both scanning and detour installation and were reported
stable. A verified pass-through run crashed with the same exception while
skipping all crouch-state reads, cache processing and animation changes.

This test executes the original startup scanner and readiness loop. Once a
candidate is found it skips detour installation entirely and starts the same
read-only 250 ms diagnostic monitor. It never modifies the animation entry,
installs the camera hook, or executes an animation trampoline. The proxy
remains pinned during monitoring. If no candidate is found, it times out
without installing a detour; that run is not a completed scanner-only test.

The scanner reads process memory, so its allocation and timing effects are
still present. Stable gameplay would strengthen the focus on the detour
path but would not prove a root cause. Intermittent failures require repeated
comparisons. This is a diagnostic build, not a confirmed fix.

## Build and checks

```sh
ROTK_CRASH_DIAGNOSTIC=1 ZIG=/path/to/zig ZIG_GLOBAL_CACHE_DIR=/tmp/rotk-zig-cache \
  bash native/vivoxproxy/build-v5-compat.sh /tmp/rotk-diag4/vivoxsdk_x64.dll
python3 native/vivoxproxy/tests/test_crash_diagnostic.py
python3 native/vivoxproxy/tests/test_trampoline_validation.py
node scripts/package-crash-diagnostic.mjs /tmp/rotk-diag4/vivoxsdk_x64.dll diag4
```

Native cross-compilation passes with warnings as errors. Tests exercise
scanner-only completion and timeout without detour installation alongside
the other modes. The existing trampoline validation and forwarding checks
also pass. Packaged labels, hashes and disabled updater are checked locally;
Windows gameplay and script execution remain user validation.
