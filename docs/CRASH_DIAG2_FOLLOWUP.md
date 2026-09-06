# diag2 follow-up: death-to-respawn timing

## User observations

The trigger is clicking Respawn too soon after death in Combat Training,
not repeatedly clicking Respawn. The user reports much better FPS with
`diag2: hook`, followed by another crash. They previously reported stable
sessions in both diag1 modes and a crash in the original GitHub version.
These observations do not establish that all crashes share an exception.

## Received artifacts

The updated `/tmp/rotk-crouch-parity.log` ends at 2026-09-05 22:52:30.405 UTC
with PID 12448. It confirms `build=diag2 mode=hook`, v14 installation,
`ownership=pinned-image`, and `validation=install-only`.
The log was initially supplied without its dump. The subsequently supplied
`/tmp/H1Z1.exe.12448.dmp` has now been analyzed below. The older PID 10116
dump is no longer in `/tmp`; comparisons use its previously recorded findings.

## Cross-run log comparison

| PID | Mode | First to last log entry (UTC) | Probe snapshots |
| --- | --- | --- | --- |
| 12400 | diag1 control | 21:54:32.605–22:23:35.267 | 31 |
| 10584 | diag1 hook | 22:24:29.228–22:39:01.873 | 17 |
| 12448 | diag2 hook | 22:49:52.193–22:52:30.405 | 5 |

These intervals describe captured log coverage, not exact gameplay duration.
Every one of the 53 snapshots successfully reads the same operands and
candidate code bytes, including the before-install samples:

- base operand: `0x140000000`;
- target operand: `0x140f6f676`;
- calculated sum: `0x280f6f676`;
- candidate block: the 59 bytes previously reconstructed at `0x140dfb775`.

There are no `snapshot=changed` records in these runs. Control confirms
`scanner=off detours=off`. Consequently, the suspect operand combination and
candidate block exist without crouch detour installation and throughout the
reported stable control session. Their mere presence is not evidence of
crouch-hook-induced corruption. The earlier snapshot reconstruction still
supports a possible final transfer for PID 10116; it does not establish why
execution reaches it or whether the latest crash follows it.

Polling is non-atomic and 250 ms apart, so this does not exclude transient
changes or earlier execution effects. Control retains the proxy and probe.

The new run logs stale-cache resets through count 128. No generation-reset,
pressure, or out-of-order warning is logged. Stale resets are expected cache
behavior, not evidence on their own of a lifetime error. v14 no longer has
per-call trampoline validation, so absence of its old FATAL message cannot
be used as evidence of validation success throughout the run.

## Next investigation

The PID 12448 dump comparison is now complete; see below. The corrected death-to-respawn trigger makes object teardown and
recreation a relevant hypothesis; it is not a confirmed fault in the hook.
FPS improvement supports retaining the removal of expensive per-call checks,
but timing changes could alter reproducibility and do not prove a crash fix.
No additional runtime code was changed during this log analysis.

## PID 12448 dump findings

- Exception thread: 13088.
- Exception: `0xc0000005`, execute (parameter 0 = 8).
- RIP, RAX, and exception target: `0x280f6f676`, unmapped memory.
- RSP: `0x15e980`; RCX: `0x15e978`.
- The same candidate final transfer at `0x140dfb775` matches all eight
  verifier conditions, including the two target copies and restored RBX/RBP.
- Restored RBX is `0x699d8cf0`, restored RBP is `0x2d00000`; these differ
  from the old run's object addresses while the control-flow signature agrees.

Verification command:

```sh
python3 scripts/verify-crash-10116.py /tmp/H1Z1.exe.12448.dmp
```

This repeats the older PID 10116 execute-violation signature. The performance
change did not eliminate it. It does not establish that every reported crash
of the original GitHub build has this same signature, since that separate
dump has not been identified here.

The loaded proxy base is `0x7ffd38b70000`. All 41,110 virtual `.text` bytes
match the built diag2 DLL after applying image-base relocations. The animation
detour points to `0x7ffd38b76370`. The thunk at `0x7ffd38b710a0` retains its
expected 16-byte prologue and RIP-relative jump. Its continuation slot at
`0x7ffd38b84848` contains `0x143211ff0`. The thunk is committed RX image
memory owned by the proxy; the continuation is executable H1Z1 image memory.
No proxy-address candidates occur among aligned qwords in the captured
exception stack, `0x15e980` through `0x160000`. This is not a verified unwind
and cannot exclude an earlier indirect effect from the hook.

The strongest current distinction is between reaching the game transfer and
the mere existence of its operands: the same operands/code were sampled
throughout the stable control session. No evidence here supports removing
an image-base addition blindly or claiming that the trampoline was freed.

A controlled follow-up should use diag2 control and specifically click Respawn
immediately after death in Combat Training, with the same conditions as the
crashing hook run. A matching control crash would show the failure can occur
without crouch scanner/detours; continued stability would be supporting, not
conclusive, evidence of a hook-dependent timing or lifetime interaction.
No additional game-code patch was made based on this dump.

## Second control run verified

The latest log confirms PID 2896 is `diag2 mode=control` with
`scanner=off detours=off`. It spans 2026-09-05 23:56:05.544 UTC through
2026-09-06 00:09:06.393 UTC (about 13 minutes of logged coverage). The user
reports about 20 minutes playing without crashes or performance problems.
All 15 probe snapshots retain the stock animation prologue; there are no
installation or blend-transition entries for this PID. The same suspect
operands and code are present with no logged snapshot changes.

This supports investigating the enabled crouch path but cannot distinguish
its scanner, detour mechanics, state reads/cache, pose changes, or timing.
A new diag3 pass-through mode retains scanning and installation but bypasses
all crouch-state processing and forwards the original function arguments.
