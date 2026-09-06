#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
zig_bin="${ZIG:-zig}"
output="${1:-$script_dir/dist/vivoxsdk_x64_v5_compat.dll}"
if [[ "$("$zig_bin" version)" != "0.15.2" ]]; then
    echo "Expected Zig 0.15.2" >&2
    exit 1
fi
diagnostic_flags=()
if [[ "${ROTK_CRASH_DIAGNOSTIC:-0}" == "1" ]]; then
    diagnostic_flags=(-DROTK_CRASH_DIAGNOSTIC=1)
fi
mkdir -p -- "$(dirname -- "$output")"
"$zig_bin" cc -target x86_64-windows-gnu -shared -O2 -s -fno-ident \
    -Wall -Wextra -Werror -DROTK_VIVOX_V5_COMPAT=1 "${diagnostic_flags[@]}" \
    -Wl,--dynamicbase -Wl,--nxcompat -Wl,--high-entropy-va \
    -o "$output" "$script_dir/vivoxsdk_x64_proxy.c" \
    "$script_dir/vivoxsdk_x64_v5_compat.def" -lwinhttp -lshell32
echo "Built $output"
