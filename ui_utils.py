import tkinter as tk

# Variabel global untuk tema
THEME_NAME = "cyborg"  # Anda bisa mengganti tema di sini (misalnya "litera", "darkly", dll.)

def get_theme():
    """Mengembalikan nama tema yang digunakan."""
    return THEME_NAME

def create_styled_label(parent, text, font_size=11):
    """Membuat label dengan gaya standar."""
    return tk.Label(parent, text=text, font=("Segoe UI", font_size))

def create_tooltip(widget, text):
    """Membuat tooltip untuk widget."""
    tooltip = None
    def enter(event):
        nonlocal tooltip
        x, y, _, _ = widget.bbox("insert") if hasattr(widget, "bbox") else (0, 0, 0, 0)
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()
    def leave(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)