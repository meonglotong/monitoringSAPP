import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
from datetime import datetime
from tkinter import messagebox, filedialog

def setup_memo_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    main_container = tk.Frame(frame)
    main_container.pack(expand=True, fill="both")

    # Menggunakan ukuran kanvas yang lebih kecil agar muat di window 1280x720
    canvas_frame = tk.Frame(main_container, width=1920, height=1080)
    # Menggunakan place untuk memusatkan canvas_frame
    canvas_frame.place(relx=0.5, rely=0.5, anchor="center")
    canvas_frame.pack_propagate(False)

    canvas = tk.Canvas(canvas_frame, width=800, height=650, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttkb.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview, bootstyle=SECONDARY)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = tk.Frame(canvas)
    canvas.create_window((500, 0), window=scrollable_frame, anchor="nw")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    from ui_utils import create_styled_label, create_tooltip
    create_styled_label(scrollable_frame, f"📝 Memo - {operator_name}", 20).pack(pady=(20, 10))

    input_frame = ttkb.LabelFrame(scrollable_frame, text="Tulis Memo", padding=15)
    input_frame.pack(pady=20)

    memo_text = tk.Text(input_frame, height=10, width=60, font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=5, pady=5)
    memo_text.pack(pady=5)

    list_frame = ttkb.LabelFrame(scrollable_frame, text="Daftar Memo", padding=15)
    list_frame.pack(pady=20)

    memo_listbox = tk.Listbox(list_frame, height=10, width=80, font=("Segoe UI", 10))
    memo_listbox.pack(side="left", fill="x")
    list_scroll = ttkb.Scrollbar(list_frame, command=memo_listbox.yview, bootstyle=SECONDARY)
    memo_listbox.configure(yscrollcommand=list_scroll.set)
    list_scroll.pack(side="right", fill="y")

    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(pady=20)

    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

    memo_dir = os.path.join(os.getcwd(), "memos")
    os.makedirs(memo_dir, exist_ok=True)

    def load_memos():
        memo_listbox.delete(0, tk.END)
        for filename in os.listdir(memo_dir):
            if filename.endswith(".txt"):
                memo_listbox.insert(tk.END, filename)

    def save_memo():
        content = memo_text.get("1.0", tk.END).strip()
        if not content:
            status_label.config(text="❌ Memo kosong!", fg="red")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"memo_{timestamp}_{operator_name}.txt"
        filepath = os.path.join(memo_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        memo_text.delete("1.0", tk.END)
        load_memos()
        status_label.config(text=f"✅ Memo disimpan: {filename}", fg="green")

    def view_memo():
        selection = memo_listbox.curselection()
        if not selection:
            status_label.config(text="❌ Pilih memo terlebih dahulu!", fg="red")
            return
        filename = memo_listbox.get(selection[0])
        filepath = os.path.join(memo_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        memo_text.delete("1.0", tk.END)
        memo_text.insert(tk.END, content)
        status_label.config(text=f"📖 Memo {filename} dibuka", fg="green")

    def delete_memo():
        selection = memo_listbox.curselection()
        if not selection:
            status_label.config(text="❌ Pilih memo terlebih dahulu!", fg="red")
            return
        filename = memo_listbox.get(selection[0])
        filepath = os.path.join(memo_dir, filename)
        if messagebox.askyesno("Konfirmasi", f"Hapus {filename}?"):
            os.remove(filepath)
            load_memos()
            status_label.config(text=f"🗑️ Memo {filename} dihapus", fg="green")

    btn_simpan = ttkb.Button(button_frame, text="💾 Simpan Memo", command=save_memo, bootstyle=SUCCESS)
    btn_simpan.grid(row=0, column=0, padx=5, sticky="ew")
    create_tooltip(btn_simpan, "Simpan memo baru")

    btn_lihat = ttkb.Button(button_frame, text="📖 Lihat Memo", command=view_memo, bootstyle=INFO)
    btn_lihat.grid(row=0, column=1, padx=5, sticky="ew")
    create_tooltip(btn_lihat, "Lihat isi memo yang dipilih")

    btn_hapus = ttkb.Button(button_frame, text="🗑️ Hapus Memo", command=delete_memo, bootstyle=DANGER)
    btn_hapus.grid(row=0, column=2, padx=5, sticky="ew")
    create_tooltip(btn_hapus, "Hapus memo yang dipilih")

    btn_kembali = ttkb.Button(button_frame, text="🔙 Kembali", command=kembali_callback, bootstyle=SECONDARY)
    btn_kembali.grid(row=0, column=3, padx=5, sticky="ew")
    create_tooltip(btn_kembali, "Kembali ke menu utama")

    load_memos()

if __name__ == "__main__":
    from ui_utils import get_theme
    root = ttkb.Window(themename=get_theme())
    root.title("Memo Manager")
    root.geometry("1920x1080")
    frame = tk.Frame(root)
    frame.pack(expand=True, fill=tk.BOTH)
    setup_memo_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()