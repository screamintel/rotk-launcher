# Fork builds and releases

Target repository: `screamintel/rotk-launcher`.

## Behavior

The installer is named `ROTK-Launcher-Fork-<version>-x64.exe`. The application and
shortcut are named **ROTK Launcher Fork**, with a separate Windows application ID
and settings directory (`%APPDATA%\ROTK Launcher Fork`). Select your existing game
folder if prompted; the installer does not bundle `H1Z1.exe`.

The version display includes `(fork: control)`. The launcher writes
`mode=disabled` and `animation=fork-control-no-scanner-no-hook` into the game's
`rotk-crouch-parity.ini`, replacing an old hook-enabled marker. The normal native
build includes no diagnostic monitor. No scanner or crouch animation detour starts
in this mode. Vivox 5 voice compatibility and existing client verification remain.
The official launcher may overwrite this marker when used again.

Control was stable during the reported tests, but the intermittent respawn crash's
root cause is not established. Crouch animation changes supplied by the upstream
hook are absent. Server acceptance of a fork is not guaranteed; no server-side
code is modified. See [the evidence](CRASH_ISOLATION_RESULTS.md).

## Publish an installer

1. Enable GitHub Actions in the fork's Actions tab.
2. Put these changes on the fork's `main` branch.
3. Select **Release Windows Fork → Run workflow → main**.

The workflow builds and tests on Windows with Node 22 and Zig 0.15.2, verifies
native binaries and their hashes, packages an NSIS installer, and publishes a
release named `fork-v<package.json version>` at the exact tested commit. A matching
`fork-v*` tag pushed to the fork also triggers it. Every release version must be new;
existing releases are not overwritten. For later releases, bump `package.json`
and `package-lock.json` together before running it again.

The release contains the installer, updater metadata, blockmap and SHA256SUMS.txt.
GitHub also records a provenance attestation. The workflow uses its own
`GITHUB_TOKEN`; no personal token is needed. It can publish only when running in
`screamintel/rotk-launcher`, and explicitly targets that repository. The packaged
update configuration also points there, but automatic update checks are disabled
for these experimental builds: download each new installer from the fork Releases
page. This keeps the upstream protocol version unchanged and avoids collisions
with inherited upstream tags. Rename the repository settings if the fork moves.

Without optional Windows signing secrets, the installer is unsigned. Signing
configuration uses repository secrets `WINDOWS_CERTIFICATE_BASE64` and
`WINDOWS_CERTIFICATE_PASSWORD`, plus repository variable
`WINDOWS_PUBLISHER_SUBJECT`. No upstream release environment is required.

## Preserve and reproduce the investigation

The commit titled `Preserve respawn crash investigation and diagnostic modes`
records the diagnostic source and reports before the fork's Control default.
The diagnostic packager expects a separately built historical v13
`release/win-unpacked` seed and is not the production release pipeline.
The old seed has been retained locally; diag1–diag3 generated archives and staging
folders can be discarded. Raw dumps and runtime logs are not included in Git.

The fork release pipeline builds directly from source and does not need any local
`release*` directory. The latest diag4 archive is retained locally for comparison.
