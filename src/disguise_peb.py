"""
Educational demonstration: modify the current process PEB image path.

WARNING
-------
This file is for **local cybersecurity education only**.
- It modifies internal Windows structures in the current process.
- Anti-cheat and EDR products may flag this behaviour.
- It does NOT change the kernel EPROCESS.ImageFileName, so Task Manager's
  "Details" tab may still show the original executable name.
- It WILL change what many user-mode tools (Process Explorer, Process Hacker,
  WMI queries, some debuggers) report for the process image path and command
  line.

How it works
------------
Windows keeps per-process bookkeeping in the Process Environment Block (PEB),
located via the TEB (gs:[0x60] on x64). Inside the PEB is a pointer to
RTL_USER_PROCESS_PARAMETERS, which contains UNICODE_STRING fields such as
ImagePathName and CommandLine. These fields are read by many user-mode
enumerators. Because the buffer they point to is in the process's own address
space, we can allocate a new wide-character string and repoint the
UNICODE_STRING there.

Offsets used (x64 Windows 10/11, 22H2+):
- TEB.ProcessEnvironmentBlock        : 0x60
- PEB.ProcessParameters              : 0x20
- RTL_USER_PROCESS_PARAMETERS.ImagePathName : 0x60
- RTL_USER_PROCESS_PARAMETERS.CommandLine   : 0x70
"""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass

# ntdll handles
_ntdll = ctypes.windll.ntdll
_kernel32 = ctypes.windll.kernel32

# ProcessBasicInformation for NtQueryInformationProcess
_ProcessBasicInformation = 0


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", ctypes.c_ushort),
        ("MaximumLength", ctypes.c_ushort),
        ("Padding", ctypes.c_uint32),  # structure alignment on x64
        ("Buffer", ctypes.c_void_p),
    ]


class _PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("ExitStatus", ctypes.c_ulong),
        ("PebBaseAddress", ctypes.c_void_p),
        ("AffinityMask", ctypes.c_ulonglong),
        ("BasePriority", ctypes.c_long),
        ("UniqueProcessId", ctypes.c_void_p),
        ("InheritedFromUniqueProcessId", ctypes.c_void_p),
    ]


# Set up ctypes signatures
_ntdll.NtQueryInformationProcess.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),
]
_ntdll.NtQueryInformationProcess.restype = ctypes.c_long

_kernel32.GetCurrentProcess.argtypes = []
_kernel32.GetCurrentProcess.restype = ctypes.c_void_p

_kernel32.VirtualAllocEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
_kernel32.VirtualAllocEx.restype = ctypes.c_void_p

_kernel32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
_kernel32.ReadProcessMemory.restype = ctypes.c_bool

_kernel32.WriteProcessMemory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
_kernel32.WriteProcessMemory.restype = ctypes.c_bool

_kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
_kernel32.CloseHandle.restype = ctypes.c_bool


class PebDisguiseError(RuntimeError):
    """Raised when PEB disguise cannot be applied safely."""


def _read_ptr(process: int, address: int) -> int:
    """Read a pointer-sized value from another (or the same) process."""
    buf = ctypes.c_void_p(0)
    read = ctypes.c_size_t(0)
    ok = _kernel32.ReadProcessMemory(
        process, address, ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(read)
    )
    if not ok or read.value != ctypes.sizeof(buf):
        raise PebDisguiseError(f"Failed to read pointer at 0x{address:X}")
    return buf.value or 0


def _read_unicode_string(process: int, address: int) -> _UNICODE_STRING:
    """Read a UNICODE_STRING from another (or the same) process."""
    us = _UNICODE_STRING()
    read = ctypes.c_size_t(0)
    ok = _kernel32.ReadProcessMemory(
        process, address, ctypes.byref(us), ctypes.sizeof(us), ctypes.byref(read)
    )
    if not ok or read.value != ctypes.sizeof(us):
        raise PebDisguiseError(f"Failed to read UNICODE_STRING at 0x{address:X}")
    return us


def _read_wide_string(process: int, address: int, length: int) -> str:
    """Read a UTF-16 string of ``length`` bytes from another process."""
    if length <= 0 or address == 0:
        return ""
    byte_count = length + 2  # include null terminator padding
    buf = (ctypes.c_char * byte_count)()
    read = ctypes.c_size_t(0)
    ok = _kernel32.ReadProcessMemory(
        process, address, buf, byte_count, ctypes.byref(read)
    )
    if not ok:
        raise PebDisguiseError(f"Failed to read wide string at 0x{address:X}")
    return buf.raw.decode("utf-16-le", errors="replace").rstrip("\x00")


def _get_peb_address() -> int:
    """Return the PEB address of the current process."""
    pbi = _PROCESS_BASIC_INFORMATION()
    ret_len = ctypes.c_ulong(0)
    status = _ntdll.NtQueryInformationProcess(
        _kernel32.GetCurrentProcess(),
        _ProcessBasicInformation,
        ctypes.byref(pbi),
        ctypes.sizeof(pbi),
        ctypes.byref(ret_len),
    )
    if status != 0:
        raise PebDisguiseError(f"NtQueryInformationProcess failed with status 0x{status:08X}")
    if pbi.PebBaseAddress == 0:
        raise PebDisguiseError("PebBaseAddress is NULL")
    return pbi.PebBaseAddress


def _get_current_image_path_peb() -> str:
    """Return the current PEB ImagePathName value (for diagnostics)."""
    h_self = _kernel32.GetCurrentProcess()
    peb = _get_peb_address()
    process_parameters = _read_ptr(h_self, peb + 0x20)
    image_path_us = _read_unicode_string(h_self, process_parameters + 0x60)
    return _read_wide_string(h_self, image_path_us.Buffer, image_path_us.Length)


def _allocate_wide_string(text: str) -> int:
    """Allocate a writable copy of ``text`` (UTF-16) in the current process."""
    h_self = _kernel32.GetCurrentProcess()
    raw = text.encode("utf-16-le")
    # Include room for a terminating null wide-character.
    size = len(raw) + 2
    addr = _kernel32.VirtualAllocEx(
        h_self,
        None,
        size,
        0x3000,  # MEM_COMMIT | MEM_RESERVE
        0x04,    # PAGE_READWRITE
    )
    if addr is None or addr == 0:
        raise PebDisguiseError("VirtualAllocEx failed for fake image path")

    written = ctypes.c_size_t(0)
    buf = ctypes.create_string_buffer(raw + b"\x00\x00")
    ok = _kernel32.WriteProcessMemory(
        h_self, addr, buf, size, ctypes.byref(written)
    )
    if not ok or written.value != size:
        raise PebDisguiseError("WriteProcessMemory failed for fake image path")
    return addr


def _write_unicode_string(process: int, address: int, buffer_addr: int, text: str) -> None:
    """Rewrite a UNICODE_STRING in-place to point at ``buffer_addr``."""
    raw = text.encode("utf-16-le")
    length = len(raw)
    maximum_length = length + 2

    new_us = _UNICODE_STRING()
    new_us.Length = length
    new_us.MaximumLength = maximum_length
    new_us.Buffer = buffer_addr

    written = ctypes.c_size_t(0)
    ok = _kernel32.WriteProcessMemory(
        process,
        address,
        ctypes.byref(new_us),
        ctypes.sizeof(new_us),
        ctypes.byref(written),
    )
    if not ok or written.value != ctypes.sizeof(new_us):
        raise PebDisguiseError(f"Failed to write UNICODE_STRING at 0x{address:X}")


def get_process_image_path() -> str:
    """Public helper: return current PEB image path."""
    return _get_current_image_path_peb()


def set_process_image_path(fake_path: str) -> bool:
    """
    Repoint the current process PEB ImagePathName to ``fake_path``.

    This is a user-mode only change. Kernel-level tools and Task Manager's
    "Details" tab may still show the original executable name.
    """
    if not fake_path:
        raise PebDisguiseError("fake_path must not be empty")

    h_self = _kernel32.GetCurrentProcess()
    peb = _get_peb_address()
    process_parameters = _read_ptr(h_self, peb + 0x20)

    new_buffer = _allocate_wide_string(fake_path)
    _write_unicode_string(h_self, process_parameters + 0x60, new_buffer, fake_path)
    return True


def set_command_line(fake_command_line: str) -> bool:
    """
    Repoint the current process PEB CommandLine to ``fake_command_line``.

    Many enumeration tools display the command line, so changing it helps
    complete the disguise.
    """
    if fake_command_line is None:
        return False

    h_self = _kernel32.GetCurrentProcess()
    peb = _get_peb_address()
    process_parameters = _read_ptr(h_self, peb + 0x20)

    new_buffer = _allocate_wide_string(fake_command_line)
    _write_unicode_string(h_self, process_parameters + 0x70, new_buffer, fake_command_line)
    return True


@dataclass
class PebDisguiseConfig:
    enabled: bool = False
    fake_image_path: str = ""
    fake_command_line: str = ""


def apply_peb_disguise(cfg: PebDisguiseConfig) -> PebDisguiseConfig:
    """Apply PEB image-path disguise according to ``cfg``."""
    if not cfg.enabled:
        return cfg

    if not cfg.fake_image_path:
        # Default to a neutral-looking path under System32.
        cfg.fake_image_path = r"C:\Windows\System32\svchost.exe"

    if cfg.fake_command_line is None:
        cfg.fake_command_line = cfg.fake_image_path

    set_process_image_path(cfg.fake_image_path)
    set_command_line(cfg.fake_command_line)
    return cfg


def main() -> int:
    """CLI smoke-test: show before/after values."""
    print("PEB image path disguise demo")
    print("=" * 50)

    try:
        before = get_process_image_path()
        print(f"Before: {before}")
    except PebDisguiseError as e:
        print(f"Cannot read current image path: {e}")
        return 1

    fake = r"C:\Windows\System32\notepad.exe"
    fake_cmd = '"C:\\Windows\\System32\\notepad.exe" "C:\\Users\\Public\\notes.txt"'

    try:
        set_process_image_path(fake)
        set_command_line(fake_cmd)
        after = get_process_image_path()
        print(f"After:  {after}")
        print(f"Expected fake path: {fake}")
        print(f"Match: {after.lower() == fake.lower()}")
    except PebDisguiseError as e:
        print(f"Disguise failed: {e}")
        return 1

    print("=" * 50)
    print("Check Process Explorer / Process Hacker to see the changed name.")
    print("Task Manager 'Details' tab may still show the original name.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
