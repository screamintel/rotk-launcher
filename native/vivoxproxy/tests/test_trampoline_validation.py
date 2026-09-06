"""Run the production C trampoline validator against mocked Windows memory APIs.

This checks allocation/byte validation, not Windows detour execution or the ABI.
Run with Python 3 and a host C compiler (CC defaults to cc).
"""

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "crouch_parity_patch.h"


def extract_function(source, name):
    match = re.search(r"static (?:BOOL|uint16_t)\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise AssertionError(f"Production helper not found: {name}")
    opening = source.index("{", match.end())
    depth = 1
    cursor = opening + 1
    while depth:
        if source[cursor] == "{":
            depth += 1
        elif source[cursor] == "}":
            depth -= 1
        cursor += 1
    return source[match.start():cursor]


PRELUDE = r"""
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef int BOOL;
typedef size_t SIZE_T;
typedef uint32_t DWORD;
#define TRUE 1
#define FALSE 0
#define MEM_COMMIT 0x1000U
#define MEM_RESERVE 0x2000U
#define MEM_PRIVATE 0x20000U
#define MEM_MAPPED 0x40000U
#define MEM_IMAGE 0x1000000U
#define PAGE_READWRITE 0x04U
#define PAGE_EXECUTE_READ 0x20U
#define PAGE_EXECUTE_READWRITE 0x40U
#define PAGE_GUARD 0x100U
typedef struct {
    void *BaseAddress;
    void *AllocationBase;
    DWORD AllocationProtect;
    SIZE_T RegionSize;
    DWORD State;
    DWORD Protect;
    DWORD Type;
} MEMORY_BASIC_INFORMATION;
static void crouch_image_trampoline(void) {}
static unsigned char proxy_owner;
static void *g_proxy_module = &proxy_owner;
static void *g_crouch_original_blend_trampoline;
static uintptr_t g_crouch_image_base = 0x140000000ULL;
static uintptr_t g_crouch_blend_resume;
static uint8_t g_crouch_trampoline_expected[22];
static uint8_t mock_code[22];
static MEMORY_BASIC_INFORMATION thunk_region, game_region;
static int query_failure, read_failure, short_read;
static unsigned cases;
static void *GetCurrentProcess(void) { return &proxy_owner; }
static SIZE_T VirtualQuery(const void *address,
                          MEMORY_BASIC_INFORMATION *result, SIZE_T bytes) {
    int is_thunk = address == (void *)(uintptr_t)crouch_image_trampoline;
    if (bytes != sizeof(*result) || query_failure == (is_thunk ? 1 : 2)) {
        return 0;
    }
    *result = is_thunk ? thunk_region : game_region;
    return sizeof(*result);
}
static BOOL ReadProcessMemory(void *process, const void *address,
                              void *destination, SIZE_T count, SIZE_T *copied) {
    if (read_failure || process != GetCurrentProcess() ||
        address != (void *)(uintptr_t)crouch_image_trampoline ||
        count > sizeof(mock_code)) {
        *copied = 0;
        return FALSE;
    }
    *copied = short_read ? count - 1 : count;
    memcpy(destination, mock_code, *copied);
    return TRUE;
}
"""


CASES = r"""
static void reset(void) {
    uintptr_t thunk = (uintptr_t)crouch_image_trampoline;
    query_failure = read_failure = short_read = 0;
    g_crouch_original_blend_trampoline = (void *)thunk;
    g_crouch_blend_resume = g_crouch_image_base + CROUCH_BLEND_WEIGHT_RVA + 16;
    for (size_t i = 0; i < sizeof(mock_code); ++i) {
        mock_code[i] = g_crouch_trampoline_expected[i] = (uint8_t)(0x40 + i);
    }
    memset(&thunk_region, 0, sizeof(thunk_region));
    thunk_region.BaseAddress = (void *)thunk;
    thunk_region.AllocationBase = g_proxy_module;
    thunk_region.RegionSize = 4096;
    thunk_region.State = MEM_COMMIT;
    thunk_region.Protect = PAGE_EXECUTE_READ;
    thunk_region.Type = MEM_IMAGE;
    game_region = thunk_region;
    game_region.BaseAddress = (void *)(g_crouch_blend_resume - 16);
    game_region.AllocationBase = (void *)g_crouch_image_base;
}
static void expect(const char *label, BOOL accepted) {
    ++cases;
    if (!!crouch_validate_trampoline() != !!accepted) {
        fprintf(stderr, "FAILED: %s\n", label);
        exit(1);
    }
}
int main(void) {
    reset(); expect("pinned image RX", TRUE);
    reset(); game_region.Protect = PAGE_EXECUTE_READWRITE;
    expect("observed H1Z1 RWX image", TRUE);
    reset(); thunk_region.Type = MEM_MAPPED;
    expect("mapped reuse", FALSE);
    reset(); thunk_region.Type = MEM_PRIVATE;
    expect("private executable allocation", FALSE);
    reset(); thunk_region.Protect = PAGE_READWRITE;
    expect("nonexecutable thunk", FALSE);
    reset(); thunk_region.Protect = PAGE_EXECUTE_READWRITE;
    expect("writable proxy thunk", FALSE);
    reset(); thunk_region.Protect |= PAGE_GUARD;
    expect("guarded thunk", FALSE);
    reset(); thunk_region.AllocationBase = (void *)g_crouch_image_base;
    expect("wrong thunk owner", FALSE);
    reset(); thunk_region.State = MEM_RESERVE;
    expect("uncommitted thunk", FALSE);
    reset(); game_region.Type = MEM_MAPPED;
    expect("mapped game continuation", FALSE);
    reset(); game_region.AllocationBase = g_proxy_module;
    expect("wrong game owner", FALSE);
    reset(); game_region.Protect = PAGE_READWRITE;
    expect("nonexecutable game continuation", FALSE);
    reset(); game_region.Protect = PAGE_EXECUTE_READWRITE | PAGE_GUARD;
    expect("guarded game continuation", FALSE);
    reset(); game_region.State = MEM_RESERVE;
    expect("uncommitted game continuation", FALSE);
    reset(); mock_code[0] ^= 1;
    expect("modified copied prologue", FALSE);
    reset(); mock_code[21] ^= 1;
    expect("modified jump operand", FALSE);
    reset(); g_crouch_blend_resume += 1;
    expect("changed continuation pointer", FALSE);
    reset(); g_crouch_original_blend_trampoline = (void *)g_crouch_image_base;
    expect("changed thunk pointer", FALSE);
    reset(); query_failure = 1;
    expect("thunk query failure", FALSE);
    reset(); query_failure = 2;
    expect("game query failure", FALSE);
    reset(); read_failure = 1;
    expect("thunk read failure", FALSE);
    reset(); short_read = 1;
    expect("partial thunk read", FALSE);
    reset(); thunk_region.RegionSize = sizeof(mock_code) - 1;
    expect("thunk crosses region boundary", FALSE);
    reset(); game_region.RegionSize = 31;
    expect("continuation crosses region boundary", FALSE);
    reset(); thunk_region.RegionSize = sizeof(mock_code);
    game_region.RegionSize = 32;
    expect("exact region boundaries", TRUE);
    printf("Passed %u production trampoline validation cases\n", cases);
    return 0;
}
"""


class TrampolineValidationTest(unittest.TestCase):
    def test_original_call_forwards_without_windows_queries(self):
        wrapper = extract_function(SOURCE.read_text(), "crouch_call_original")
        harness = r"""
#include <stdint.h>
#include <stdlib.h>
static unsigned calls;
static uint16_t crouch_image_trampoline(
    void *a, void *b, void *c, void *d, void *e,
    float f, float g, float h, float i, unsigned char j) {
    if (a != (void *)1 || b != (void *)2 || c != (void *)3 ||
        d != (void *)4 || e != (void *)5 || f != 0.125f ||
        g != 0.25f || h != 0.5f || i != 0.75f || j != 1) abort();
    ++calls;
    return 0x1234;
}
""" + wrapper + r"""
int main(void) {
    uint16_t result = crouch_call_original(
        (void *)1, (void *)2, (void *)3, (void *)4, (void *)5,
        0.125f, 0.25f, 0.5f, 0.75f, 1);
    return result != 0x1234 || calls != 1;
}
"""
        # No Windows APIs or validator are linked: adding them to the hot
        # wrapper makes this fail, while verifying every forwarded argument.
        with tempfile.TemporaryDirectory(prefix="rotk-forward-") as tmp:
            source, binary = Path(tmp) / "forward.c", Path(tmp) / "forward"
            source.write_text(harness)
            subprocess.run(shlex.split(os.environ.get("CC", "cc")) + [
                "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(source), "-o", str(binary),
            ], check=True)
            subprocess.run([str(binary)], check=True)

    def test_production_validator(self):
        source = SOURCE.read_text()
        rva = re.search(r"^#define CROUCH_BLEND_WEIGHT_RVA .+$", source, re.M)
        self.assertIsNotNone(rva)
        helpers = "\n".join(extract_function(source, name) for name in (
            "crouch_read_exact", "crouch_image_code_region",
            "crouch_validate_trampoline",
        ))
        with tempfile.TemporaryDirectory(prefix="rotk-validator-") as temporary:
            directory = Path(temporary)
            harness = directory / "validator.c"
            executable = directory / "validator"
            harness.write_text(PRELUDE + rva.group() + "\n" + helpers + CASES)
            subprocess.run(shlex.split(os.environ.get("CC", "cc")) + [
                "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(harness), "-o", str(executable),
            ], check=True)
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
