# v13 trampoline lifetime test build

This build hardens trampoline ownership. It is not a confirmed fix for the
crash in `/tmp/H1Z1.exe.10996.dmp`.

## Dump findings

The installed animation detour at `0x143211fe0` targets
`vivoxsdk_x64.dll+0x5c80` (`0x7ffb8dea5c80`). The loaded hook reads its original
trampoline pointer from `0x7ffb8dec2868`; that pointer is `0x3a8d0000`.
The allocation is committed `MEM_PRIVATE / PAGE_EXECUTE_READ`, with the exact
16-byte original prologue and an intact absolute jump to `0x143211ff0`.

`0x161e0000`, reported by a log from PID 18020, is unrelated writable private
memory in this dump. Addresses from different process runs cannot establish
that this process freed its trampoline.

The exception is a read access violation at `H1Z1.exe+0x1bea5a0`, reading
`0xfffffffff0cfe54b`. The instruction uses `rdx-0xf301ab5`, with `RDX=0`.
The dump does not establish where that invalid execution state originated.

## Lifetime audit and change

The old trampoline has three release paths: failure to set RX protection
during preparation, camera installation failure before the animation detour
is installed, and animation installation failure. Code writes report failure
only before writing; failure to restore protection after writing returns
success. None of these paths releases a successfully installed animation
trampoline. The memory scanner releases a separate allocation. There is no
unmap call or process-detach trampoline cleanup in this source.

v13 replaces the separately allocated trampoline with a compiler-emitted x64
image thunk containing the same prologue and a RIP-relative indirect jump to
the original continuation. The proxy module is pinned before installing
either detour. Pinning is permanent even on installation failure, because
camera rollback is not guaranteed to succeed. Ordinary FreeLibrary cannot
unload the pinned module, and no trampoline allocation remains to free.

Every original-function call validates the exact thunk address, image owner,
committed RX protection, region bounds, all 22 thunk bytes, the continuation
address, and its executable image mapping. The game continuation accepts RX
or RWX because the supplied dump has RWX game code. An invalid trampoline
logs a FATAL validation message and fails fast; it never calls the suspect
pointer, invents successful output, or recursively calls the detoured entry.

This is not synchronization against arbitrary concurrent memory corruption.
The existing live detour installation still writes multiple bytes without
suspending game threads. Per-call validation adds Windows API overhead;
gameplay performance and live ABI behavior require Windows testing.

## Windows test

Extract the entire `ROTK-v13-windows-test.zip` into a separate directory.
Close the old launcher and H1Z1, then run `win-unpacked/ROTK Launcher.exe`.
Use this matching launcher: older launchers enforce the old DLL hash and
will replace or reject a manually substituted DLL. The new launcher deploys
the bundled v13 DLL and writes the v13 marker automatically. Do not accept
a launcher update during this test, since that would replace the test build.

Check the game's `rotk-crouch-parity.log` for `ADS-safe v13 installed` and
`ownership=pinned-image`. Reproduce the original crash scenario and note
frame-time changes. If it crashes, retain the new dump and this same run's
log, including its PID and trampoline address. For rollback, close both
programs and use the previous launcher, which redeploys its expected DLL.

## Build and verification

The DLL is built on Linux using the project's pinned Zig 0.15.2, Windows x64
GNU target, O2, and warnings as errors. A reproducible entry point is:

```sh
ZIG=/path/to/zig ZIG_GLOBAL_CACHE_DIR=/tmp/rotk-zig-cache \
  bash native/vivoxproxy/build-v5-compat.sh resources/patches/vivoxsdk_x64.dll
```

The DLL hash must also be updated in `electron/services/vivox-client.ts` and
the adjacent `.sha256` sidecar before building the matching launcher.

Validation passed 25 mocked-memory cases against the production C helpers,
including freed/reused mappings, ownership changes, changed instructions,
query/read failures, and region boundaries. PE inspection verified AMD64
format and the exact emitted thunk instructions. TypeScript checks and both
launcher compilation stages passed. Vitest passed 189 tests; nine tests in
the unchanged Windows path-policy and Steam-discovery suites fail on Linux.
The existing Windows-only native cache test cannot execute in this environment.
No Windows gameplay test has been performed here.
