// Stage a diagnostic launcher without overwriting the existing v13 package.
// Usage: node scripts/package-crash-diagnostic.mjs /path/to/diagnostic.dll
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve, join } from "node:path";
import { extractAll, createPackage } from "@electron/asar";

const dll = resolve(process.argv[2] || "missing-diagnostic-dll");
const build = process.argv[3] || "diag1";
if (!["diag1", "diag2", "diag3", "diag4"].includes(build)) throw new Error("Expected diag1, diag2, diag3 or diag4");
const stage = resolve(`release-${build}`);
if (existsSync(stage)) throw new Error(`Output already exists: ${stage}`);
const bytes = readFileSync(dll);
if (!bytes.includes(Buffer.from(`[crash-diagnostic] build=${build}`))) {
  throw new Error("DLL is not the diagnostic build");
}
const hash = createHash("sha256").update(bytes).digest("hex");
const existing = resolve("release/win-unpacked");
const originalHash = createHash("sha256")
  .update(readFileSync(join(existing, "resources/patches/vivoxsdk_x64.dll"))).digest("hex");
mkdirSync(stage);
const unpacked = join(stage, "win-unpacked");
cpSync(existing, unpacked, { recursive: true });
const source = join(stage, "app-source");
const archive = join(unpacked, "resources/app.asar");
extractAll(archive, source);
function replaceOnce(path, from, to) {
  const content = readFileSync(path, "utf8");
  if (content.split(from).length !== 2) throw new Error(`Expected one match in ${path}`);
  writeFileSync(path, content.replace(from, to));
}
replaceOnce(join(source, "dist-electron/electron/services/vivox-client.js"), originalHash, hash);
replaceOnce(join(source, "dist-electron/electron/main.js"),
  "appVersion: app.getVersion(),",
  `appVersion: app.getVersion() + " (${build}: " + (process.env.ROTK_CRASH_DIAGNOSTIC_MODE || "normal") + ")",`);
if (build !== "diag1") {
  replaceOnce(join(source, "dist-electron/electron/services/vivox-client.js"),
    "animation=v13-pinned-image-ads-safe-cache256-lru2s-pose-only-js-sine-idle400-200-move250",
    "animation=v14-install-validation-ads-safe-cache256-lru2s-pose-only-js-sine-idle400-200-move250");
}
// Portable diagnostics must not initialize an installer updater or replace themselves.
replaceOnce(join(source, "dist-electron/electron/main.js"),
  "updater: app.isPackaged ? electronUpdater.autoUpdater : null,",
  "updater: null, // Self-updates disabled for the portable diagnostic package.");
await createPackage(source, archive);
writeFileSync(join(unpacked, "resources/patches/vivoxsdk_x64.dll"), bytes);
writeFileSync(join(unpacked, "resources/patches/vivoxsdk_x64.dll.sha256"), `${hash}  vivoxsdk_x64.dll\n`);
const modes = [["1-Run-Control.cmd", "control"], ["2-Run-Hook.cmd", "hook"]];
if (["diag3", "diag4"].includes(build)) modes.push(["3-Run-Passthrough.cmd", "passthrough"]);
if (build === "diag4") modes.push(["4-Run-Scanner-Only.cmd", "scanner-only"]);
for (const [name, mode] of modes) {
  const script = `@echo off
setlocal DisableDelayedExpansion
title ROTK ${build} - ${mode}
echo ROTK crash diagnostic: ${mode}
echo.
if not exist "%~dp0win-unpacked\\ROTK Launcher.exe" goto missing
if not exist "%~dp0win-unpacked\\resources\\app.asar" goto missing
tasklist /FI "IMAGENAME eq H1Z1.exe" /NH | find /I "H1Z1.exe" >nul
if not errorlevel 1 goto running
tasklist /FI "IMAGENAME eq ROTK Launcher.exe" /NH | find /I "ROTK Launcher.exe" >nul
if not errorlevel 1 goto running
set "ROTK_CRASH_DIAGNOSTIC_MODE=${mode}"
echo Starting launcher. This window stays open until the launcher exits.
echo Launcher output is saved in launcher-${mode}-startup.log next to this script.
echo Expected launcher label: ${build}: ${mode}
echo.
start "" /wait /D "%~dp0win-unpacked" "%~dp0win-unpacked\\ROTK Launcher.exe" >"%~dp0launcher-${mode}-startup.log" 2>&1
set "ROTK_LAUNCH_EXIT=%errorlevel%"
echo Launcher exited with code %ROTK_LAUNCH_EXIT%.
echo.
type "%~dp0launcher-${mode}-startup.log"
echo.
echo If the launcher did not open, share the exit code and startup log.
pause
exit /b %ROTK_LAUNCH_EXIT%
:missing
echo Missing launcher files. Extract the entire test ZIP first.
echo Put this script beside the win-unpacked folder, not inside it.
echo Expected: "%~dp0win-unpacked\\ROTK Launcher.exe"
pause
exit /b 1
:running
echo Close H1Z1 and all ROTK Launcher processes before starting this test.
pause
exit /b 1
`;
  writeFileSync(join(stage, name), script.replaceAll("\n", "\r\n"));
}
cpSync(`docs/CRASH_DIAGNOSTIC_${build.toUpperCase()}.md`, join(stage, "START-HERE.txt"));
console.log(`Staged ${stage}\nDiagnostic DLL SHA-256: ${hash}`);
