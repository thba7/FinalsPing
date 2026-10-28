"""FinalsPing."""
import ctypes
from ctypes import wintypes
import queue
import os
import sys
import threading
import tkinter as tk

from engine import State, process_loop, sniff_loop, measurement_loop

APP_NAME = 'FinalsPing'
WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002
WM_RBUTTONUP = 0x0205
WM_MOUSEWHEEL = 0x020A
WM_LBUTTONUP = 0x0202
NIM_ADD = 0
NIM_DELETE = 2
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
IDI_APPLICATION = 32512

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetCursorPos.argtypes = [ctypes.c_void_p]
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
user32.LoadIconW.restype = wintypes.HICON
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DestroyWindow.argtypes = [wintypes.HWND]
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

class GUID(ctypes.Structure):
    _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]

class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND),
        ('uID', wintypes.UINT), ('uFlags', wintypes.UINT),
        ('uCallbackMessage', wintypes.UINT), ('hIcon', wintypes.HICON),
        ('szTip', ctypes.c_wchar * 128), ('dwState', wintypes.DWORD),
        ('dwStateMask', wintypes.DWORD), ('szInfo', ctypes.c_wchar * 256),
        ('uTimeoutOrVersion', wintypes.UINT), ('szInfoTitle', ctypes.c_wchar * 64),
        ('dwInfoFlags', wintypes.DWORD), ('guidItem', GUID), ('hBalloonIcon', wintypes.HICON)
    ]

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
class WNDCLASS(ctypes.Structure):
    _fields_ = [('style', wintypes.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int),
                ('cbWndExtra', ctypes.c_int), ('hInstance', wintypes.HINSTANCE), ('hIcon', wintypes.HICON),
                ('hCursor', wintypes.HANDLE), ('hbrBackground', wintypes.HBRUSH),
                ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR)]

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

class Tray(threading.Thread):
    def __init__(self, commands, closed):
        super().__init__(daemon=True)
        self.commands = commands
        self.closed = closed
        self.details = False
        self.locked = False
        self.colors = True
        self.hwnd = None
        self.callback = WNDPROC(self._wndproc)

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_TRAY and lp in (WM_RBUTTONUP, WM_LBUTTONUP):
            self._popup(hwnd)
            return 0
        if msg == WM_COMMAND:
            cmd = int(wp) & 0xffff
            if cmd == 100:
                self.details = not self.details
                self.commands.put(('details', self.details))
            elif cmd == 101:
                self.locked = not self.locked
                self.commands.put(('lock', self.locked))
            elif cmd == 105:
                self.colors = not self.colors
                self.commands.put(('colors', self.colors))
            elif cmd == 104:
                self.commands.put(('exit', None))
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def _popup(self, hwnd):
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, 0x0000 | (0x0008 if self.details else 0), 100, 'Details')
        user32.AppendMenuW(menu, 0x0000 | (0x0008 if self.locked else 0), 101, 'Lock')
        user32.AppendMenuW(menu, 0x0800, 0, None)
        user32.AppendMenuW(menu, 0x0000 | (0x0008 if self.colors else 0), 105, 'Colors')
        user32.AppendMenuW(menu, 0x0800, 0, None)
        user32.AppendMenuW(menu, 0, 104, 'Exit')
        pos = POINT()
        user32.GetCursorPos(ctypes.byref(pos))
        user32.SetForegroundWindow(hwnd)
        user32.TrackPopupMenu(menu, 0x0002, pos.x, pos.y, 0, hwnd, None)
        user32.PostMessageW(hwnd, 0, 0, 0)
        user32.DestroyMenu(menu)

    def run(self):
        name = 'FinalsPingTrayWindow'
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASS()
        wc.lpfnWndProc = self.callback
        wc.hInstance = hinst
        wc.lpszClassName = name
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, name, APP_NAME, 0, 0, 0, 0, 0, None, None, hinst, None)
        if not self.hwnd:
            return
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        icon_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'FinalsPing.ico')
        if getattr(sys, '_MEIPASS', None):
            icon_path = os.path.join(sys._MEIPASS, 'FinalsPing.ico')
        nid.hIcon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not nid.hIcon:
            nid.hIcon = user32.LoadIconW(None, ctypes.cast(IDI_APPLICATION, wintypes.LPCWSTR))
        nid.szTip = APP_NAME
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        msg = wintypes.MSG()
        while not self.closed.is_set() and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        user32.DestroyWindow(self.hwnd)

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_COMMAND, 104, 0)

class Overlay:
    def __init__(self):
        self.closed = threading.Event()
        self.commands = queue.SimpleQueue()
        self.updates = queue.SimpleQueue()
        self.st = State()
        self.details = False
        self.locked = False
        self.colors = True
        self.size = 26
        self.value = None
        self.pos = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#010101')
        self.root.wm_attributes('-transparentcolor', '#010101')
        self.label = tk.Label(self.root, text='', font=('Segoe UI', self.size, 'bold'),
                              bg='#010101', fg='#52e09c', padx=8, pady=3)
        self.label.pack()
        self.label.bind('<Button-1>', self._drag_start)
        self.label.bind('<B1-Motion>', self._drag_move)
        self.label.bind('<MouseWheel>', self._resize_wheel)
        self.label.bind('<Button-3>', self._resize_start)
        self.label.bind('<B3-Motion>', self._resize_move)
        self.root.geometry('+80+80')
        icon_file = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)), 'FinalsPing.ico')
        try:
            self.root.iconbitmap(default=icon_file)
        except tk.TclError:
            pass
        self.tray = Tray(self.commands, self.closed)
        self.tray.start()
        self.threads = [threading.Thread(target=process_loop, args=(self.st, self.closed), daemon=True)]
        self.threads += [threading.Thread(target=sniff_loop, args=(self.st, ip, self.closed), daemon=True)
                         for ip in self.st.ips]
        self.threads += [threading.Thread(target=measurement_loop,
                          args=(self.st, self.closed, self.updates.put), daemon=True)]
        for thread in self.threads:
            thread.start()
        self.root.after(100, self.tick)

    def _bounds(self):
        x = 0
        y = 0
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return x, y, max(1, w), max(1, h)

    def _keep_visible(self, x=None, y=None):
        self.root.update_idletasks()
        left, top, width, height = self._bounds()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = self.root.winfo_x() if x is None else x
        y = self.root.winfo_y() if y is None else y
        x = max(left, min(int(x), left + width - min(w, width)))
        y = max(top, min(int(y), top + height - min(h, height)))
        self.root.geometry(f'+{x}+{y}')

    def _change_size(self, delta):
        left, top, width, height = self._bounds()
        proposed = max(8, min(240, self.size + delta))
        self.size = proposed
        self.label.configure(font=('Segoe UI', self.size, 'bold'))
        self.draw()
        self._keep_visible()

    def _resize_wheel(self, event):
        self._change_size(2 if event.delta > 0 else -2)

    def _resize_start(self, event):
        self.resize_anchor = (event.y_root, self.size)

    def _resize_move(self, event):
        if hasattr(self, 'resize_anchor'):
            y, size = self.resize_anchor
            target = max(8, min(240, size + round((y - event.y_root) / 3)))
            if target != self.size:
                self._change_size(target - self.size)

    def _drag_start(self, event):
        if not self.locked:
            self.pos = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _drag_move(self, event):
        if not self.locked and self.pos:
            self._keep_visible(event.x_root - self.pos[0], event.y_root - self.pos[1])

    def tick(self):
        while True:
            try:
                command, arg = self.commands.get_nowait()
            except queue.Empty:
                break
            if command == 'exit':
                self.close()
                return
            if command == 'details':
                self.details = arg
                self.draw()
            if command == 'lock':
                self.locked = arg
            if command == 'colors':
                self.colors = arg
                self.draw()
        latest = None
        while True:
            try:
                latest = self.updates.get_nowait()
            except queue.Empty:
                break
        if latest != None:
            self.value = latest
            self.draw()
        elif self.value is not None and self.st.get_match() is None:
            self.value = None
            self.draw()
        if not self.closed.is_set():
            self.root.after(100, self.tick)

    def draw(self):
        info = self.value
        if not info or info.get('value') is None:
            self.root.withdraw()
            return
        ms = info['value']
        text = f'{ms:.1f}ms'
        if self.details:
            extras = [info.get('region'), info.get('city')]
            text += ' ' + ' '.join(x for x in extras if x)
        color = '#59e49b' if ms < 100 else '#efce5a' if ms < 200 else '#ef8a56' if ms < 350 else '#f16f79'
        self.label.configure(text=text, fg=color if self.colors else '#FFFFFF')
        self._keep_visible()
        self.root.deiconify()

    def close(self):
        self.closed.set()
        self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Windows required')
    if not shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, f'"{__file__}"', None, 1)
        raise SystemExit(0)
    Overlay().run()
