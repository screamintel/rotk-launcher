# diag3 pass-through crash: PID 12104

The user clarifies that clicking Respawn immediately after death sometimes
works and sometimes crashes. In their stable control session they could
perform that same action repeatedly without a crash; this is relevant to
the comparison, not simply a difference between rapid repeated clicks and
immediate post-death timing.

## Artifacts and mode verification

The new `/tmp/H1Z1.exe.12104.dmp` is present. The uploaded log still ends with
PID 2896's earlier control session, so no current-run log timeline is available.
The dump independently confirms:

- Loaded proxy at `0x7ffd2bd90000`; all 41,206 virtual .text bytes match the
  built diag3 DLL after applying base relocations.
- Process environment contains `ROTK_CRASH_DIAGNOSTIC_MODE=passthrough`.
- The selected pass-through flag at proxy + `0x24870` is 1.
- Animation detour at `0x143211fe0` targets proxy + `0x6390`.
- The conditional branch at proxy + `0x63f6` selects the bypass, restoring
  saved registers and tail-jumping to the image thunk at proxy + `0x10a0`.
  Node-definition dereferences begin on the unselected path at + `0x6462`.
- The thunk is intact, RX committed image memory owned by the proxy; its
  continuation slot at proxy + `0x14848` still contains `0x143211ff0`.

## Exception

Exception thread 7264 has execute AV `0xc0000005` at `0x280f6f676`.
RIP/RAX and RCX/RSP match the prior two analyzed dumps. All eight conditions
of `scripts/verify-crash-10116.py` pass against this dump. The restored object
addresses differ (RBX `0xc56f00f0`, RBP `0x2c90000`) but the final transfer
signature is the same.

This demonstrates the same observed failure with the mode that bypasses
crouch-state reads, cache processing, and replacement animation weights.
The snapshot does not record the entire execution history; the flag is set
by the worker before installing the detour and has no subsequent write path
in the diagnostic source. It strongly weakens hypotheses that require the
bypassed processing to run in this process.

Remaining differences from the stable control include startup scanning, live
detour installation, execution via a trampoline, and timing/stack effects.
The game-code operand combination alone remains nondiagnostic because it
also exists throughout stable control runs.

## Next split

Diag4 scanner-only executes the existing scanner and readiness loop, then
monitors without installing either detour. This keeps the game animation
entry unmodified while testing scanning. A matching crash would show that
an installed animation detour is not necessary in that run. Stability would
further focus attention on detour/trampoline behavior or its interaction
with game timing. Neither outcome alone identifies a specific defective
instruction or justifies a patch to the bad game address calculation.
