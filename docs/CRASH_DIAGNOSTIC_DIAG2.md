# diag2 / v14 performance comparison

This test removes v13's per-call trampoline validation while retaining the
pinned image trampoline and complete validation before detour installation.
It is not a confirmed crash fix or a measured FPS improvement.

## Test

1. Extract ROTK-diag2-windows-test.zip into a new folder.
2. Close H1Z1 and all ROTK Launcher processes.
3. Run 2-Run-Hook.cmd. Confirm the launcher shows `1.4.5 (diag2: hook)`.
4. Test Combat Training with the same graphics settings, player load where
   possible, and rapid respawns. Record FPS and whether/when it crashes.
5. Keep the complete game-folder rotk-crouch-parity.log and any new dump.
   The log should show `build=diag2 mode=hook`, `ADS-safe v14 installed`,
   and `validation=install-only` for this run's PID.

The game and its log remain in the existing installation (C:\Games\ROTK
in the supplied dump). Do not copy DLLs manually: this launcher enforces the
matching DLL hash. A control script is also included, but start with hook
mode for the performance comparison. The terminal waits for launcher exit,
then shows its code and pauses; launcher output is saved beside the script.
Self-updates are disabled in this portable package.

Rollback: close both programs and use the previous launcher. It redeploys
its own expected DLL. Existing diag1 and v13 packages remain available.

## What changed

The original animation-call wrapper now directly calls the image thunk.
It no longer performs VirtualQuery, ReadProcessMemory, byte comparisons, or
fail-fast validation on every call. Installation still validates the full
thunk and continuation before publishing the detour, and pins the module.
There is no longer a per-call check for later corruption of that code/data.

Crouch timing, state-cache behavior, character-state reads, transition logging,
and the disabled camera hook are unchanged. Both diagnostic modes retain the
250 ms read-only crash probe and its heartbeat. Those costs can still affect
performance; this change isolates the extra per-call trampoline checks.

## Current reproduction evidence

The user reports roughly 20 minutes without crashing in each diag1 mode,
about 150 FPS with its hook versus a usual roughly 300 FPS, and a subsequent
crash in the original GitHub version after about five quick respawns in
Combat Training. These are user observations, not controlled benchmark
results; exact original release identity and its new dump remain unverified.
No single cause has been established for the differing crash behavior.

## Build and validation

```sh
ROTK_CRASH_DIAGNOSTIC=1 ZIG=/path/to/zig ZIG_GLOBAL_CACHE_DIR=/tmp/rotk-zig-cache \
  bash native/vivoxproxy/build-v5-compat.sh /tmp/rotk-diag2/vivoxsdk_x64.dll
python3 native/vivoxproxy/tests/test_trampoline_validation.py
python3 native/vivoxproxy/tests/test_crash_diagnostic.py
node scripts/package-crash-diagnostic.mjs /tmp/rotk-diag2/vivoxsdk_x64.dll diag2
```

Cross-compilation with Zig 0.15.2 and warnings as errors passed. The production
wrapper test forwards all ten arguments and the result without linking any
Windows query API or validator. The 25 validator cases and seven diagnostic
worker-routing cases pass. Windows gameplay/FPS testing remains outstanding.
