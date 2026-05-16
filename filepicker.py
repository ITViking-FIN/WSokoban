"""Native Windows 'open file' dialog via ctypes.

Avoids dragging tkinter into the bundle — comdlg32 is part of every
Windows install, ctypes is in the stdlib. Returns the picked path or
None on cancel.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes


class _OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ('lStructSize', wintypes.DWORD),
        ('hwndOwner', wintypes.HWND),
        ('hInstance', wintypes.HINSTANCE),
        ('lpstrFilter', wintypes.LPCWSTR),
        ('lpstrCustomFilter', wintypes.LPWSTR),
        ('nMaxCustFilter', wintypes.DWORD),
        ('nFilterIndex', wintypes.DWORD),
        ('lpstrFile', wintypes.LPWSTR),
        ('nMaxFile', wintypes.DWORD),
        ('lpstrFileTitle', wintypes.LPWSTR),
        ('nMaxFileTitle', wintypes.DWORD),
        ('lpstrInitialDir', wintypes.LPCWSTR),
        ('lpstrTitle', wintypes.LPCWSTR),
        ('Flags', wintypes.DWORD),
        ('nFileOffset', wintypes.WORD),
        ('nFileExtension', wintypes.WORD),
        ('lpstrDefExt', wintypes.LPCWSTR),
        ('lCustData', wintypes.LPARAM),
        ('lpfnHook', wintypes.LPVOID),
        ('lpTemplateName', wintypes.LPCWSTR),
        ('pvReserved', wintypes.LPVOID),
        ('dwReserved', wintypes.DWORD),
        ('FlagsEx', wintypes.DWORD),
    ]


_OFN_FILEMUSTEXIST = 0x00001000
_OFN_PATHMUSTEXIST = 0x00000800
_OFN_HIDEREADONLY  = 0x00000004
_OFN_EXPLORER      = 0x00080000


def pick_file(title: str = 'Open file',
              filters: list[tuple[str, str]] | None = None
              ) -> str | None:
    """Open a Windows 'open file' dialog. Returns the chosen path or None.

    `filters` is a list of (description, pattern) e.g.
    [('Sokoban files (*.sok;*.xsb;*.txt)', '*.sok;*.xsb;*.txt'),
     ('All files (*.*)', '*.*')].
    """
    if filters is None:
        filters = [('All files (*.*)', '*.*')]
    # The filter buffer is a sequence of \0-separated strings, double-\0
    # terminated. Build it once and keep a Python reference alive.
    parts = []
    for desc, pat in filters:
        parts.append(desc)
        parts.append(pat)
    filter_buf = '\0'.join(parts) + '\0\0'

    buf = ctypes.create_unicode_buffer(2048)
    ofn = _OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(_OPENFILENAMEW)
    ofn.lpstrFilter = filter_buf
    ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
    ofn.nMaxFile = 2048
    ofn.lpstrTitle = title
    ofn.Flags = (_OFN_FILEMUSTEXIST | _OFN_PATHMUSTEXIST
                 | _OFN_HIDEREADONLY | _OFN_EXPLORER)

    try:
        get_open = ctypes.windll.comdlg32.GetOpenFileNameW
    except AttributeError:
        return None
    get_open.argtypes = [ctypes.POINTER(_OPENFILENAMEW)]
    get_open.restype = wintypes.BOOL

    if get_open(ctypes.byref(ofn)):
        return buf.value
    return None


SOKOBAN_FILTERS = [
    ('Sokoban level packs (*.sok;*.xsb;*.slc;*.txt)',
     '*.sok;*.xsb;*.slc;*.txt'),
    ('All files (*.*)', '*.*'),
]


# ---- Clipboard -----------------------------------------------------------
_CF_UNICODETEXT = 13


def _clipboard_setup():
    """Bind argtypes/restype on the win32 calls so 64-bit handles aren't
    truncated to 32-bit ints (the default ctypes assumption)."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    return user32, kernel32


def get_clipboard_text() -> str:
    """Read Unicode text from the Windows clipboard, '' on failure.
    Uses user32 + kernel32 directly so we don't need pygame.scrap (which
    is excluded from the build to keep the bundle small)."""
    try:
        user32, kernel32 = _clipboard_setup()
    except (AttributeError, OSError):
        return ''
    if not user32.OpenClipboard(0):
        return ''
    try:
        handle = user32.GetClipboardData(_CF_UNICODETEXT)
        if not handle:
            return ''
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ''
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
