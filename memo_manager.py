import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

def setup_memo_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    frame.configure(bg="#f5f6f5")
    
    # Main container untuk memusatkan canvas secara horizontal
    main_container = tk.Frame(frame, bg="#f5f6f5")
    main_container.pack(expand=True, fill="both")

    # Frame untuk canvas dengan ukuran tetap
    canvas_frame = tk.Frame(main_container, bg="#f5f6f5", width=800, height=650)
    canvas_frame.pack(side="top", padx=(200,0), pady=20, expand=False)  # Hanya dipusatkan horizontal
    canvas_frame.pack_propagate(False)  # Mencegah frame menyesuaikan ukuran konten

    # Canvas dengan scrollbar
    canvas = tk.Canvas(canvas_frame, bg="#f5f6f5", width=800, height=650, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    # Scrollbar vertikal
    scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Frame yang akan digulir di dalam canvas
    scrollable_frame = tk.Frame(canvas, bg="#f5f6f5")
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    # Update scrollregion saat konten berubah
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Tambahkan binding untuk scroll dengan mouse wheel
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    from ui_utils import create_styled_label, create_styled_button
    create_styled_label(scrollable_frame, f"📝 Memo - {operator_name}", 20).pack(pady=(20, 10))

    # Frame Input Memo
    input_frame = tk.LabelFrame(scrollable_frame, text="Tulis Memo", font=("Segoe UI", 12, "bold"), bg="#f5f6f5", fg="#34495e", padx=15, pady=10, bd=2, relief="groove")
    input_frame.pack(pady=20)

    memo_text = tk.Text(input_frame, height=10, width=60, font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=5, pady=5)
    memo_text.pack(pady=5)

    # Frame Daftar Memo
    list_frame = tk.LabelFrame(scrollable_frame, text="Daftar Memo", font=("Segoe UI", 12, "bold"), bg="#f5f6f5", fg="#34495e", padx=15, pady=10, bd=2, relief="groove")
    list_frame.pack(pady=20)

    memo_listbox = tk.Listbox(list_frame, height=10, width=80, font=("Segoe UI", 10))
    memo_listbox.pack(side="left", fill="x")
    list_scroll = tk.Scrollbar(list_frame, command=memo_listbox.yview)
    memo_listbox.configure(yscrollcommand=list_scroll.set)
    list_scroll.pack(side="right", fill="y")

    # Tombol
    button_frame = tk.Frame(scrollable_frame, bg="#f5f6f5")
    button_frame.pack(pady=20)

    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

    # Direktori penyimpanan memo
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

    # Tombol
    create_styled_button(button_frame, "💾 Simpan Memo", save_memo, "#2ecc71", tooltip_text="Simpan memo baru").grid(row=0, column=0, padx=5)
    create_styled_button(button_frame, "📖 Lihat Memo", view_memo, "#3498db", tooltip_text="Lihat isi memo yang dipilih").grid(row=0, column=1, padx=5)
    create_styled_button(button_frame, "🗑️ Hapus Memo", delete_memo, "#e74c3c", tooltip_text="Hapus memo yang dipilih").grid(row=0, column=2, padx=5)
    create_styled_button(button_frame, "🔙 Kembali", kembali_callback, "#95a5a6", tooltip_text="Kembali ke menu utama").grid(row=0, column=3, padx=5)

    # Muat daftar memo saat pertama kali dibuka
    load_memos()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Memo Manager")
    root.geometry("1280x720")
    frame = tk.Frame(root, bg="#f5f6f5")
    frame.pack(expand=True, fill=tk.BOTH)
    setup_memo_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()