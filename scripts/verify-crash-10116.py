"""Read-only verification of the candidate final transfer in PID 10116.

Usage: python3 scripts/verify-crash-10116.py /path/H1Z1.exe.10116.dmp
This is a snapshot consistency check, not an execution trace or root-cause proof.
Requires only Python standard-library modules. Addresses are specific to this dump.
"""
import argparse
import bisect
import json
import mmap
import struct


def verify(path):
    with open(path, "rb") as file, mmap.mmap(
        file.fileno(), 0, access=mmap.ACCESS_READ
    ) as dump:
        if dump[:4] != b"MDMP":
            raise ValueError("Not a Windows minidump")
        count, directory = struct.unpack_from("<II", dump, 8)
        streams = {}
        for index in range(count):
            kind, size, offset = struct.unpack_from("<III", dump, directory + index * 12)
            streams[kind] = (size, offset)
        offset = streams[9][1]
        count, data = struct.unpack_from("<QQ", dump, offset)
        ranges = []
        for index in range(count):
            address, size = struct.unpack_from("<QQ", dump, offset + 16 + index * 16)
            ranges.append((address, address + size, data))
            data += size
        ranges.sort()
        starts = [entry[0] for entry in ranges]

        def read(address, size):
            index = bisect.bisect_right(starts, address) - 1
            if index < 0 or address + size > ranges[index][1]:
                raise ValueError(f"Uncaptured memory at {address:#x}")
            start, _, data = ranges[index]
            result = dump[data + address - start:data + address - start + size]
            if len(result) != size:
                raise ValueError("Truncated dump")
            return result

        def qword(address):
            return struct.unpack("<Q", read(address, 8))[0]

        exception = streams[6][1]
        thread = struct.unpack_from("<I", dump, exception)[0]
        code = struct.unpack_from("<I", dump, exception + 8)[0]
        operation, target = struct.unpack_from("<QQ", dump, exception + 40)
        _, context = struct.unpack_from("<II", dump, exception + 160)
        values = struct.unpack_from("<17Q", dump, context + 120)
        registers = dict(zip(
            "rax rcx rdx rbx rsp rbp rsi rdi r8 r9 r10 r11 r12 r13 r14 r15 rip".split(),
            values,
        ))
        # Exact disassembled block: two loads/adds, stack writes, register
        # restoration, then jmp [rsp-8]. Validate bytes before modeling it.
        block = bytes.fromhex(
            "488b053c703600480305658e150048894500488b4500488d4d70"
            "4883e908488901488b5d40488d6560488b2c24488d642408"
            "488d642408ff6424f8"
        )
        if read(0x140DFB775, len(block)) != block:
            raise ValueError("Candidate code differs from PID 10116 analysis")
        base_value = qword(0x1411627B8)
        target_value = qword(0x140F545E8)
        calculated = (base_value + target_value) & ((1 << 64) - 1)
        frame = registers["rsp"] - 0x70
        checks = {
            "execute_access_violation": code == 0xC0000005 and operation == 8,
            "calculated_target_matches_exception": calculated == target == registers["rip"],
            "rax_matches": registers["rax"] == calculated,
            "rcx_matches": registers["rcx"] == frame + 0x68,
            "local_target_matches": qword(frame) == calculated,
            "stack_target_matches": qword(frame + 0x68) == calculated,
            "restored_rbx_matches": qword(frame + 0x40) == registers["rbx"],
            "restored_rbp_matches": qword(frame + 0x60) == registers["rbp"],
        }
        result = {
            "thread": thread,
            "base_operand": hex(base_value),
            "target_operand": hex(target_value),
            "calculated_target": hex(calculated),
            "inferred_frame": hex(frame),
            "checks": checks,
            "limitation": "Snapshot consistency only; no proof of prior execution or operand writers.",
        }
        print(json.dumps(result, indent=2))
        return all(checks.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump")
    raise SystemExit(0 if verify(parser.parse_args().dump) else 1)
