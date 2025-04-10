import tkinter as tk
from tkinter import ttk

def create_styled_button(parent, text, command, bg_color, fg_color="white", tooltip_text=None, width=15):
    btn = tk.Button(
        parent, text=text, command=command, bg=bg_color, fg=fg_color,
        font=("Segoe UI", 10, "bold"), relief="flat", padx=10, width=width
    )
    if tooltip_text:
        create_tooltip(btn, tooltip_text)
    return btn

def create_styled_label(parent, text, font_size=11, bg_color="#f5f6f5", fg_color="#34495e"):
    return tk.Label(parent, text=text, font=("Segoe UI", font_size), bg=bg_color, fg=fg_color)

def create_tooltip(widget, text):
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