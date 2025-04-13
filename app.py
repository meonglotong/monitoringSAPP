import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import re
import logging
import recap_zabbix
import report_email
import memo_manager
from assistant.assistant_rag import create_assistant, load_pdf_and_create_vectorstore
from ui_utils import create_styled_label, create_tooltip, get_theme

logging.basicConfig(filename="app.log", level=logging.ERROR)

# Inisialisasi window dengan tema dari ui_utils.py
window = ttkb.Window(themename=get_theme())
window.title("Monitoring SAPP")
window.geometry("1280x720")
window.state("zoomed")

operator_name = ""

# --- Frame dan Fungsi ---
frame_login = tk.Frame(window)
frame_login.pack(expand=True, fill="both")

frame_pilihan = tk.Frame(window)
frame_recap = tk.Frame(window)
frame_email = tk.Frame(window)
frame_memo = tk.Frame(window)

def is_valid_name(name):
    return bool(re.match(r"^[a-zA-Z\s]{1,20}$", name))

def tombol_masuk():
    global operator_name
    nama = entry_nama.get().strip()
    if not nama:
        status_label.config(text="Masukkan nama terlebih dahulu!", fg="red")
    elif not is_valid_name(nama):
        status_label.config(text="Nama hanya boleh huruf dan maksimum 20 karakter!", fg="red")
    else:
        status_label.config(text="Login berhasil!", fg="green")
        frame_login.pack_forget()
        frame_pilihan.pack(expand=True, fill="both")
        label_selamat.config(text=f"Selamat Datang, {nama}!")
        operator_name = nama

def kembali_login():
    frame_pilihan.pack_forget()
    frame_login.pack(expand=True, fill="both")
    entry_nama.delete(0, tk.END)
    status_label.config(text="")

def keluar_aplikasi():
    if messagebox.askyesno("Keluar", "Apakah Anda yakin ingin keluar?"):
        window.quit()

def kembali_pilihan():
    frame_recap.pack_forget()
    frame_email.pack_forget()
    frame_memo.pack_forget()
    frame_pilihan.pack(expand=True, fill="both")

def open_recap_zabbix():
    frame_pilihan.pack_forget()
    frame_recap.pack(expand=True, fill="both")
    try:
        recap_zabbix.setup_recap_frame(frame_recap, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor recap_zabbix: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Recap Zabbix: {str(e)}")

def open_report_email():
    frame_pilihan.pack_forget()
    frame_email.pack(expand=True, fill="both")
    try:
        report_email.setup_email_frame(frame_email, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor report_email: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Report Email: {str(e)}")

def open_assistant():
    frame_pilihan.pack_forget()
    assistant_frame = tk.Frame(window)
    assistant_frame.pack(expand=True, fill="both")

    # Inisialisasi asisten
    try:
        qa = create_assistant()
    except Exception as e:
        logging.error(f"Gagal menginisialisasi asisten: {str(e)}")
        messagebox.showerror("Error", f"Gagal menginisialisasi asisten: {str(e)}")
        kembali_pilihan()
        return

    main_container = tk.Frame(assistant_frame)
    main_container.pack(expand=True, fill="both")

    canvas_frame = tk.Frame(main_container, width=1920, height=1080)
    canvas_frame.pack(side="top", padx=0, pady=20, expand=False)
    canvas_frame.pack_propagate(False)

    canvas = tk.Canvas(canvas_frame, width=1920, height=1080, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttkb.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview, bootstyle=SECONDARY)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = tk.Frame(canvas)
    canvas.create_window((500,500), window=scrollable_frame, anchor="w")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Judul
    create_styled_label(scrollable_frame, f"🤖 silahkan bertanya - {operator_name} !!", 20).pack(pady=(20, 10))

    # Frame input
    input_frame = ttkb.LabelFrame(scrollable_frame,text="tanyakan seputar IT", padding=15)
    input_frame.pack(pady=20)

    input_frame.columnconfigure(0, minsize=120)

    # Baris 1: Pertanyaan
    create_styled_label(input_frame, "Pertanyaan").grid(row=0, column=0, sticky="e", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=0, column=1, sticky="w", padx=(5, 15), pady=5)
    entry_pertanyaan = ttkb.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_pertanyaan.grid(row=0, column=2, pady=5, sticky="w")
    entry_pertanyaan.bind("<Return>", lambda event: tanya())

    # Baris 2: Jawaban
    create_styled_label(input_frame, "Jawaban").grid(row=1, column=0, sticky="e", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=1, column=1, sticky="w", padx=(5, 15), pady=5)
    text_jawaban = tk.Text(input_frame, height=10, width=50, font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=5, pady=5)
    text_jawaban.grid(row=1, column=2, pady=5, sticky="w")
    text_jawaban.config(state="disabled")

    # Frame tombol
    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(pady=20)

    progress = ttkb.Progressbar(button_frame, mode="indeterminate", bootstyle=INFO)

    def tanya():
        pertanyaan = entry_pertanyaan.get().strip()
        if not pertanyaan:
            status_label.config(text="❌ Pertanyaan tidak boleh kosong!", fg="red")
            return

        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        status_label.config(text="⏳ Memproses pertanyaan...", fg="blue")

        try:
            jawaban = qa(pertanyaan)
            text_jawaban.config(state="normal")
            text_jawaban.delete("1.0", tk.END)
            text_jawaban.insert(tk.END, jawaban)
            text_jawaban.config(state="disabled")
            status_label.config(text="✅ Pertanyaan berhasil diproses", fg="green")
        except Exception as e:
            status_label.config(text=f"❌ Gagal memproses pertanyaan: {str(e)}", fg="red")
            logging.error(f"Error saat memproses pertanyaan: {str(e)}")
        finally:
            progress.stop()
            progress.grid_forget()

    def muat_ulang_vectorstore():
        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        status_label.config(text="⏳ Memuat ulang vectorstore...", fg="blue")

        try:
            load_pdf_and_create_vectorstore()
            # Perbarui asisten dengan vectorstore yang baru
            global qa
            qa = create_assistant()
            status_label.config(text="✅ Vectorstore berhasil dimuat ulang", fg="green")
        except Exception as e:
            status_label.config(text=f"❌ Gagal memuat ulang vectorstore: {str(e)}", fg="red")
            logging.error(f"Error saat memuat ulang vectorstore: {str(e)}")
        finally:
            progress.stop()
            progress.grid_forget()

    btn_kirim = ttkb.Button(button_frame, text="📤 Kirim Pertanyaan", command=tanya, bootstyle=SUCCESS)
    btn_kirim.grid(row=0, column=0, padx=5)
    create_tooltip(btn_kirim, "Kirim pertanyaan ke asisten")

    btn_muat_ulang = ttkb.Button(button_frame, text="🔄 Muat Ulang Vectorstore", command=muat_ulang_vectorstore, bootstyle=WARNING)
    btn_muat_ulang.grid(row=0, column=1, padx=5)
    create_tooltip(btn_muat_ulang, "Muat ulang vectorstore dari PDF")

    btn_kembali = ttkb.Button(button_frame, text="🔙 Kembali", command=lambda: [assistant_frame.pack_forget(), frame_pilihan.pack(expand=True, fill="both")], bootstyle=SECONDARY)
    btn_kembali.grid(row=0, column=2, padx=5)
    create_tooltip(btn_kembali, "Kembali ke menu utama")

    # Status label
    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

def open_memo_manager():
    frame_pilihan.pack_forget()
    frame_memo.pack(expand=True, fill="both")
    try:
        memo_manager.setup_memo_frame(frame_memo, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor memo_manager: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Memo Manager: {str(e)}")

# --- Widget untuk Login ---
login_container = tk.Frame(frame_login, bd=2, relief="groove")
login_container.place(relx=0.5, rely=0.5, anchor="center")

label_judul = tk.Label(login_container, text="Monitoring SAPP", font=("Helvetica", 24, "bold"))
label_judul.pack(pady=(30, 10))

login_frame = ttkb.LabelFrame(login_container, text="Login", padding=20)
login_frame.pack(padx=30, pady=10)

label_nama = create_styled_label(login_frame, "Masukkan Nama Anda:")
label_nama.grid(row=0, column=0, sticky="w", pady=5, padx=10)

entry_nama = ttkb.Entry(login_frame, font=("Helvetica", 12), width=25)
entry_nama.grid(row=0, column=1, pady=5)
entry_nama.bind("<Return>", lambda event: tombol_masuk())

btn_masuk = ttkb.Button(login_frame, text="Masuk", bootstyle=PRIMARY, command=tombol_masuk)
btn_masuk.grid(row=1, column=0, columnspan=2, pady=10)

status_label = tk.Label(login_container, text="", font=("Helvetica", 10))
status_label.pack(pady=(0, 20))

# --- Widget untuk Pilihan ---
pilihan_container = tk.Frame(frame_pilihan)
pilihan_container.pack(expand=True)

label_selamat = tk.Label(pilihan_container, text="", font=("Helvetica", 16, "bold"))
label_selamat.pack(pady=20)

button_frame = tk.Frame(pilihan_container)
button_frame.pack(pady=20)

# Menggunakan ttkb.Button dengan bootstyle
btn_recap = ttkb.Button(button_frame, text="Recap Zabbix", command=open_recap_zabbix, bootstyle=SUCCESS, width=15)
btn_recap.grid(row=0, column=0, padx=10, pady=10)
create_tooltip(btn_recap, "Buat rekap monitoring Zabbix")

btn_report = ttkb.Button(button_frame, text="Report Email", command=open_report_email, bootstyle=INFO, width=15)
btn_report.grid(row=0, column=1, padx=10, pady=10)
create_tooltip(btn_report, "Kirim laporan via email")

btn_assistant = ttkb.Button(button_frame, text="Assistant", command=open_assistant, bootstyle=WARNING, width=15)
btn_assistant.grid(row=0, column=2, padx=10, pady=10)
create_tooltip(btn_assistant, "Dapatkan bantuan dari asisten virtual")

btn_memo = ttkb.Button(button_frame, text="Memo", command=open_memo_manager, bootstyle=PRIMARY, width=15)
btn_memo.grid(row=0, column=3, padx=10, pady=10)
create_tooltip(btn_memo, "Catat dan kelola memo")

btn_kembali = ttkb.Button(button_frame, text="Kembali", command=kembali_login, bootstyle=SECONDARY, width=15)
btn_kembali.grid(row=1, column=1, padx=10, pady=10)
create_tooltip(btn_kembali, "Kembali ke halaman login")

btn_keluar = ttkb.Button(button_frame, text="Keluar", command=keluar_aplikasi, bootstyle=DANGER, width=15)
btn_keluar.grid(row=1, column=2, padx=10, pady=10)
create_tooltip(btn_keluar, "Keluar dari aplikasi")

window.mainloop()