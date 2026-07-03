import ctypes

def set_windows_click_through(hwnd: int, enabled: bool):
    if not hwnd:
        return
    try:
        gwl_exstyle = -20
        ws_ex_transparent = 0x00000020
        ws_ex_layered = 0x00080000
        user32 = ctypes.windll.user32
        current_style = user32.GetWindowLongW(hwnd, gwl_exstyle)
        if enabled:
            new_style = current_style | ws_ex_transparent | ws_ex_layered
        else:
            new_style = current_style & ~ws_ex_transparent
        if current_style != new_style:
            user32.SetWindowLongW(hwnd, gwl_exstyle, new_style)
    except Exception:
        pass