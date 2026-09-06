# diag1 crash comparison build

This is an investigation build, not a confirmed crash fix. It keeps the
existing Vivox runtime and game installation. It adds an optional read-only
probe and two explicit launch modes to the v13 test launcher.

## Windows test

1. Extract ROTK-diag1-windows-test.zip into a new folder.
2. Close H1Z1 and every ROTK Launcher process.
3. Run 1-Run-Control.cmd. The launcher should show
   `1.4.5 (diag1: control)`. Click Play and reproduce the same gameplay.
   This mode leaves the crouch scanner and both crouch detours uninstalled;
   crouch behavior will therefore differ from the patched game.
4. Keep the game's rotk-crouch-parity.log and any crash dump. The log is in
   the existing game folder (C:\Games\ROTK in the supplied dump).
5. Close both programs. Run 2-Run-Hook.cmd. The launcher should show
   `1.4.5 (diag1: hook)`. Repeat the same gameplay and retain its log/dump.

The scripts refuse to start if a game or launcher process is already running.
The terminal stays open while the launcher runs, then shows its exit code
and pauses. Launcher output is saved beside the script in
launcher-control-startup.log or launcher-hook-startup.log.
Use the scripts rather than a desktop shortcut. Self-updates are disabled in this portable diagnostic package.

Confirm the current PID in the log has `[crash-diagnostic] build=diag1`
and the requested mode. Control must also log `CONTROL active scanner=off
detours=off`. Hook must log `ADS-safe v13 installed`. An absent diagnostic
marker means the diagnostic run has not been confirmed.

Logs append across runs, so keep the complete log with its PID/timestamps.
Record what you were doing, approximate time in gameplay, and whether it
crashed. If it stays stable, test beyond the previous roughly three-minute
process lifetime where practical. One successful run is not proof of a fix.

Rollback: close the game and launcher, then run the previous launcher. It
redeploys its expected DLL. The mode is set only for the launched process
family; no persistent environment variable or game-executable edit is made.

## What the probe records

After validating the supported game image, it reads the two operands at game
RVAs 0x11627b8 and 0xf545e8, the candidate transfer code at RVA 0xdfb775, and
the animation entry. It records a snapshot before installation, after a
successful hook installation, and when a sampled value changes. Polling is
250 ms, with a heartbeat after 60 seconds without logged changes.

Snapshots include read-success flags. Failed or partial reads must not be
interpreted as valid operand values. The snapshots are not atomic across
locations and can miss changes between polls. The probe cannot identify a
writer or prove which instructions executed. Both modes still load the Vivox
proxy and pin it for the lifetime of the diagnostic worker; the control is
not an entirely unmodified game. Hook mode additionally retains the existing
scanner and per-call v13 validation overhead. Camera patching is off in both.

The normal build excludes the diagnostic code unless built with
ROTK_CRASH_DIAGNOSTIC=1. With no recognized mode, the diagnostic DLL follows
normal v13 behavior. It never corrects suspect pointers or catches the crash.

## Build

From the repository root, with Zig 0.15.2 available:

```sh
ROTK_CRASH_DIAGNOSTIC=1 ZIG=/path/to/zig ZIG_GLOBAL_CACHE_DIR=/tmp/rotk-zig-cache \
  bash native/vivoxproxy/build-v5-compat.sh /tmp/rotk-diag1/vivoxsdk_x64.dll
python3 native/vivoxproxy/tests/test_crash_diagnostic.py
python3 native/vivoxproxy/tests/test_trampoline_validation.py
node scripts/package-crash-diagnostic.mjs /tmp/rotk-diag1/vivoxsdk_x64.dll
```

The packaging script requires the existing v13 release/win-unpacked, creates
release-diag1, updates the staged launcher hash to match the staged DLL, and
adds the diagnostic label to the displayed version only. The protocol's
launcher version stays 1.4.5. Existing v13 artifacts are preserved.

Validation here covers native cross-compilation, mocked worker routing, and
package consistency. Windows launch behavior and gameplay require the user
comparison above.

## Verification performed

- Diagnostic and normal DLL cross-compilation passed with warnings as errors.
- Seven mocked production worker-routing cases and 25 existing production
  trampoline-validator cases passed.
- The normal DLL executable section matches v13 byte-for-byte.
- Packaged application comparison found exactly two changed JavaScript files:
  the displayed build label, disabled self-updater, and enforced bundled DLL hash. Their syntax
  checks passed; the staged DLL hash and sidecar agree.
- Windows gameplay and launch scripts have not been executed here.

## Portable updater repair

The first package initialized electron-updater despite lacking app-update.yml.
The repaired package supplies `updater: null` to the existing update service,
so it does not instantiate the native updater or read that missing file.
The normal launcher source and game/patch behavior are unchanged by this repair.
To repair an already extracted package, close the launcher and extract
ROTK-diag1-updater-fix.zip into the diagnostic folder, replacing app.asar
under win-unpacked/resources. The ZIP also includes the current start scripts.
