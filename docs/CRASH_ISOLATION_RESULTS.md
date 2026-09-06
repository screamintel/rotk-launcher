# Combat Training respawn crash: verified isolation results

## Reproduction

The user reports an intermittent crash when clicking Respawn immediately
after death in Combat Training. Some immediate respawns succeed. The same
action was exercised in the reported stable control sessions; repeated
button clicking is not the required trigger.

## Test matrix

| Mode | Scanner | Animation entry redirected | Crouch state/pose processing | Observation |
| --- | --- | --- | --- | --- |
| diag1 control, PID 12400 | Off | No | No | User reported stable |
| diag1 full hook, PID 10584 | On | Yes | Yes, plus expensive per-call validation | User reported stable but substantial FPS loss |
| diag2 full hook, PID 12448 | On | Yes | Yes, without per-call validation | Same execute-AV signature; FPS improved |
| diag2 control, PID 2896 | Off | No | No | User reported stable, normal FPS |
| diag3 pass-through, PID 12104 | On | Yes | Bypassed | Same execute-AV signature |
| diag4 scanner-only, PID 13904 | On | No | No | User reported about 15 minutes stable |

Control/scanner-only still load the Vivox proxy and use the diagnostic probe.
These are user gameplay comparisons, not controlled statistical measurements.
The absence of a crash during one session does not establish universal safety.

## Latest log verification

PID 13904 logs `build=diag4 mode=scanner-only` at
2026-09-06 00:40:55.644 UTC. The scanner finds a candidate and completes at
00:41:26.073 UTC, followed by the explicit marker:

```text
SCANNER-ONLY active scanner=complete detours=off
```

The final heartbeat is 00:52:27.034 UTC. The supplied log covers about 11.5
minutes, including scanner startup, while the user estimates 15 minutes of
play. All 14 snapshots show the unmodified animation prologue:

```text
48 8b c4 48 89 58 18 57 41 54 41 55 41 56 41 57
```

There are no successful detour-installation or blend-transition entries for
this PID, and no `snapshot=changed` entries. The operands and candidate game
code match those in the other sampled sessions.

## What the evidence supports

The shared crash in full-hook and verified pass-through mode does not
require the added crouch-state reads, cache processing, or pose replacement.
Scanner-only stability weakens the scanner-alone hypothesis. The strongest
remaining association is with live modification of the animation entry and
execution through the detour/trampoline, including timing or interactions
with the original game's code. This is not proof of one specific defect.

All three analyzed matching dumps have execute AV at `0x280f6f676`.
The game block at `0x140dfb775` produces that address and matches the observed
registers/stack writes. Its operands/code are also present during stable
control runs; their mere presence is not evidence of corruption. In the
verified v13/v14/diag3 snapshots the trampoline is intact and the continuation
is correct. No freed-trampoline explanation has been established.

## Implementation review and limits

`crouch_commit_jump` changes 16 bytes of live game code using memcpy after
VirtualProtect, followed by FlushInstructionCache. It does not suspend other
game threads or relocate threads executing within the replaced instructions.
This is an installation race candidate, but no dump proves a thread saw a
torn write, and a later respawn crash does not by itself establish that link.

The copied prologue is exactly 16 bytes and contains no RIP-relative
instructions. The compiled diag3 pass-through branch restores its saved
registers/stack and tail-jumps to that thunk before dereferencing character
arguments. This weakens an argument-forwarding explanation for that run but
is not a general proof that every aspect of interception is compatible with
the game.

Further investigation should focus on synchronized detour installation and
the game's behavior when its code is redirected. Whether game-side code
validation, exception handling, or another timing-sensitive path participates
remains unknown. Do not blindly change the game's invalid-address calculation,
claim anti-tamper involvement as fact, or present a diagnostic bypass as a
confirmed production fix.

The per-call validation added during this investigation caused a substantial
reported FPS regression and remains removed. Its stable test session is not
proof it fixed the underlying crash; additional work can change timing.

No further runtime modification was made after verifying this scanner-only
log. Existing scanner-only/control packages are diagnostic alternatives, not
replacements asserted to preserve the crouch patch's intended behavior.
