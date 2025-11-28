# simplecolorpicker.py
import tkinter as tk
import pyautogui
import pyperclip
from pynput import mouse

POLL_MS = 40       # refresh rate
OFFSET = (16, 16)  # tooltip offset from cursor

def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'

def text_color(rgb):
    r, g, b = [v/255 for v in rgb]
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    return '#000' if lum > 0.6 else '#fff'

class ColorTooltip:
    def __init__(self):
        self.hex_now = '#000000'

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)

        self.label = tk.Label(self.root, font=('Consolas', 12, 'bold'),
                              bd=0, padx=6, pady=6)
        self.label.pack()

        # Global mouse listener: copy on first left click, then quit
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.daemon = True
        self.listener.start()

        self.update()
        self.root.mainloop()

    def on_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            pyperclip.copy(self.hex_now)
            self.quit()

    def update(self):
        x, y = pyautogui.position()
        try:
            r, g, b = pyautogui.pixel(x, y)
        except Exception:
            r, g, b = (0, 0, 0)

        self.hex_now = rgb_to_hex(r, g, b)
        fg = text_color((r, g, b))
        txt = f'{self.hex_now}  ({r}, {g}, {b})'
        self.label.config(text=txt, bg=self.hex_now, fg=fg)
        self.place_near(x, y)
        self.root.after(POLL_MS, self.update)

    def place_near(self, x, y):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        nx, ny = x + OFFSET[0], y + OFFSET[1]
        if nx + w > sw - 4: nx = x - w - 8
        if ny + h > sh - 4: ny = y - h - 8
        self.root.geometry(f'{w}x{h}+{int(nx)}+{int(ny)}')

    def quit(self):
        try:
            self.listener.stop()
        except Exception:
            pass
        self.root.destroy()

if __name__ == '__main__':
    ColorTooltip()
