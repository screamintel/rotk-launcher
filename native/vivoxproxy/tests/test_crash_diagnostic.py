"""Exercise the production worker routing with mocked Windows operations."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "crouch_parity_patch.h"

PRELUDE = r"""
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#define ROTK_CRASH_DIAGNOSTIC 1
#define WINAPI
#define FALSE 0
#define TRUE 1
#define GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS 4
#define GET_MODULE_HANDLE_EX_FLAG_PIN 1
typedef unsigned long DWORD;
typedef int BOOL;
typedef void *LPVOID;
typedef void *HMODULE;
typedef const wchar_t *LPCWSTR;
static uintptr_t g_crouch_image_base;
static BOOL g_crouch_enable_camera;
static BOOL g_crouch_diagnostic_passthrough;
static int mode, image_ok, pin_ok, install_result, candidates;
static int scans, installs, monitors, snapshots, pins;
static void crouch_log(const char *format, ...) { (void)format; }
static BOOL crouch_validate_h1z1_image(uintptr_t *base) {
    *base = 0x140000000ULL; return image_ok;
}
static int crouch_diagnostic_mode(void) { return mode; }
static BOOL GetModuleHandleExW(DWORD flags, LPCWSTR address, HMODULE *owner) {
    if (flags != 5 || !address) abort();
    ++pins; *owner = (void *)1; return pin_ok;
}
static void crouch_diagnostic_snapshot(const char *reason) {
    if (!reason) abort();
    ++snapshots;
}
static void crouch_diagnostic_monitor(void) { ++monitors; }
static size_t crouch_scan_node_defs(void) { ++scans; return (size_t)candidates; }
static int crouch_install_runtime_patch(void) { ++installs; return install_result; }
static void Sleep(DWORD ms) { (void)ms; }
"""
CASES = r"""
static void reset(int requested) {
    mode = requested; image_ok = pin_ok = install_result = candidates = 1;
    scans = installs = monitors = snapshots = pins = 0;
    g_crouch_enable_camera = TRUE;
    g_crouch_diagnostic_passthrough = FALSE;
}
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "failed line %d\n", __LINE__); return 1; } } while (0)
int main(void) {
    reset(1); crouch_patch_worker(NULL);
    CHECK(scans == 0 && installs == 0 && monitors == 1 && snapshots == 1 && pins == 1);
    CHECK(!g_crouch_enable_camera);
    reset(2); crouch_patch_worker(NULL);
    CHECK(scans == 1 && installs == 1 && monitors == 1 && snapshots == 2 && pins == 1);
    CHECK(!g_crouch_enable_camera);
    reset(3); crouch_patch_worker(NULL);
    CHECK(scans == 1 && installs == 1 && monitors == 1 && snapshots == 2);
    CHECK(g_crouch_diagnostic_passthrough && !g_crouch_enable_camera);
    reset(4); crouch_patch_worker(NULL);
    CHECK(scans == 1 && installs == 0 && monitors == 1 && snapshots == 2 && pins == 1);
    CHECK(!g_crouch_diagnostic_passthrough && !g_crouch_enable_camera);
    reset(4); candidates = 0; crouch_patch_worker(NULL);
    CHECK(scans == 240 && installs == 0 && monitors == 0 && snapshots == 1);
    reset(0); crouch_patch_worker(NULL);
    CHECK(scans == 1 && installs == 1 && monitors == 0 && snapshots == 0 && pins == 0);
    CHECK(g_crouch_enable_camera);
    reset(1); pin_ok = 0; crouch_patch_worker(NULL);
    CHECK(scans == 0 && installs == 0 && monitors == 0);
    reset(2); image_ok = 0; crouch_patch_worker(NULL);
    CHECK(scans == 0 && installs == 0 && monitors == 0 && pins == 0);
    reset(2); install_result = -1; crouch_patch_worker(NULL);
    CHECK(installs == 1 && monitors == 0 && snapshots == 1);
    reset(2); install_result = 0; crouch_patch_worker(NULL);
    CHECK(installs == 240 && monitors == 0 && snapshots == 1);
    puts("Passed 10 diagnostic worker routing cases");
    return 0;
}
"""

class DiagnosticWorkerTest(unittest.TestCase):
    def test_production_worker(self):
        source = SOURCE.read_text()
        start = source.index("static DWORD WINAPI crouch_patch_worker(")
        end = source.index("\nstatic size_t crouch_scan_node_defs(void) {", start)
        with tempfile.TemporaryDirectory(prefix="rotk-diag-test-") as tmp:
            src, binary = Path(tmp) / "test.c", Path(tmp) / "test"
            src.write_text(PRELUDE + source[start:end] + CASES)
            subprocess.run(shlex.split(os.environ.get("CC", "cc")) + [
                "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(src), "-o", str(binary),
            ], check=True)
            subprocess.run([str(binary)], check=True)

if __name__ == "__main__":
    unittest.main()
