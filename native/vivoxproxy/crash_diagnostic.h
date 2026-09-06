#ifndef ROTK_CRASH_DIAGNOSTIC_H
#define ROTK_CRASH_DIAGNOSTIC_H

/* Included only by an explicitly compiled diagnostic build. This probe reads
 * two operands and candidate code from the supported image; it never repairs
 * pointers, swallows exceptions, or modifies game memory. */
typedef struct crouch_diagnostic_state {
    BOOL base_ok, target_ok, code_ok, entry_ok;
    uintptr_t base_operand, target_operand;
    uint8_t code[59];
    uint8_t entry[16];
} crouch_diagnostic_state;

static int crouch_diagnostic_mode(void) {
    WCHAR mode[16];
    DWORD length = GetEnvironmentVariableW(L"ROTK_CRASH_DIAGNOSTIC_MODE",
                                           mode, 16U);
    if (length == 0U || length >= 16U) return 0;
    if (wcscmp(mode, L"control") == 0) return 1;
    if (wcscmp(mode, L"hook") == 0) return 2;
    if (wcscmp(mode, L"passthrough") == 0) return 3;
    if (wcscmp(mode, L"scanner-only") == 0) return 4;
    return 0;
}

static crouch_diagnostic_state crouch_diagnostic_read(void) {
    crouch_diagnostic_state state;
    memset(&state, 0, sizeof(state));
    state.base_ok = crouch_read_exact(
        (const void *)(g_crouch_image_base + 0x11627b8U),
        &state.base_operand, sizeof(state.base_operand));
    state.target_ok = crouch_read_exact(
        (const void *)(g_crouch_image_base + 0xf545e8U),
        &state.target_operand, sizeof(state.target_operand));
    state.code_ok = crouch_read_exact(
        (const void *)(g_crouch_image_base + 0xdfb775U),
        state.code, sizeof(state.code));
    state.entry_ok = crouch_read_exact(
        (const void *)(g_crouch_image_base + CROUCH_BLEND_WEIGHT_RVA),
        state.entry, sizeof(state.entry));
    return state;
}

static void crouch_diagnostic_emit(const char *reason,
                                  const crouch_diagnostic_state *state) {
    char code_hex[sizeof(state->code) * 2U + 1U];
    char entry_hex[sizeof(state->entry) * 2U + 1U];
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0U; i < sizeof(state->code); ++i) {
        code_hex[i * 2U] = digits[state->code[i] >> 4U];
        code_hex[i * 2U + 1U] = digits[state->code[i] & 15U];
    }
    code_hex[sizeof(code_hex) - 1U] = 0;
    for (size_t i = 0U; i < sizeof(state->entry); ++i) {
        entry_hex[i * 2U] = digits[state->entry[i] >> 4U];
        entry_hex[i * 2U + 1U] = digits[state->entry[i] & 15U];
    }
    entry_hex[sizeof(entry_hex) - 1U] = 0;
    crouch_log("[crash-diagnostic] snapshot=%s image=%p baseOk=%d "
               "base=%p targetOk=%d target=%p sum=%p codeOk=%d code=%s "
               "entryOk=%d entry=%s",
               reason, (void *)g_crouch_image_base,
               state->base_ok, (void *)state->base_operand,
               state->target_ok, (void *)state->target_operand,
               (void *)(state->base_operand + state->target_operand),
               state->code_ok, code_hex, state->entry_ok, entry_hex);
}

static void crouch_diagnostic_snapshot(const char *reason) {
    crouch_diagnostic_state state = crouch_diagnostic_read();
    crouch_diagnostic_emit(reason, &state);
}

static void crouch_diagnostic_monitor(void) {
    crouch_diagnostic_state previous = crouch_diagnostic_read();
    ULONGLONG last_log = GetTickCount64();
    crouch_diagnostic_emit("monitor-start", &previous);
    for (;;) {
        Sleep(250U);
        crouch_diagnostic_state current = crouch_diagnostic_read();
        ULONGLONG now = GetTickCount64();
        if (current.base_ok != previous.base_ok ||
            current.target_ok != previous.target_ok ||
            current.code_ok != previous.code_ok ||
            current.entry_ok != previous.entry_ok ||
            current.base_operand != previous.base_operand ||
            current.target_operand != previous.target_operand ||
            memcmp(current.code, previous.code, sizeof(current.code)) != 0 ||
            memcmp(current.entry, previous.entry, sizeof(current.entry)) != 0) {
            crouch_diagnostic_emit("changed", &current);
            last_log = now;
        } else if (now - last_log >= 60000U) {
            crouch_diagnostic_emit("heartbeat", &current);
            last_log = now;
        }
        previous = current;
    }
}
#endif
