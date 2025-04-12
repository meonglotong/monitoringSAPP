import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from ttkthemes import ThemedTk
import importlib
import re
import logging
import recap_zabbix
import report_email
import memo_manager
from assistant.assistant_rag import create_assistant

logging.basicConfig(filename="app.log", level=logging.ERROR)

print("Mulai inisialisasi window")

window = ThemedTk(theme="arc")
window.title("Monitoring SAPP")
window.geometry("1280x720")
window.state("zoomed")
window.configure(bg="#f5f6f5")
print("Window dibuat")

operator_name = ""

frame_login = tk.Frame(window, bg="#f5f6f5")
frame_login.pack(expand=True, fill="both")
print("Frame login dibuat dan ditampilkan")

frame_pilihan = tk.Frame(window, bg="#f5f6f5")
frame_recap = tk.Frame(window, bg="#f5f6f5")
frame_email = tk.Frame(window, bg="#f5f6f5")
frame_memo = tk.Frame(window, bg="#f5f6f5")

def is_valid_name(name):
    return bool(re.match(r"^[a-zA-Z\s]{1,20}$", name))

def tombol_masuk():
    global operator_name
    nama = entry_nama.get().strip()
    print(f"Tombol masuk diklik, nama: {nama}")
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
    print("Kembali ke login")
    frame_pilihan.pack_forget()
    frame_login.pack(expand=True, fill="both")
    entry_nama.delete(0, tk.END)
    status_label.config(text="")

def keluar_aplikasi():
    print("Keluar aplikasi")
    if messagebox.askyesno("Keluar", "Apakah Anda yakin ingin keluar?"):
        window.quit()

def kembali_pilihan():
    print("Kembali ke pilihan dari recap/email/memo")
    frame_recap.pack_forget()
    frame_email.pack_forget()
    frame_memo.pack_forget()
    frame_pilihan.pack(expand=True, fill="both")

def open_recap_zabbix():
    print("Membuka recap zabbix")
    frame_pilihan.pack_forget()
    frame_recap.pack(expand=True, fill="both")
    try:
        recap_zabbix.setup_recap_frame(frame_recap, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor recap_zabbix: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Recap Zabbix: {str(e)}")

def open_report_email():
    print("Membuka report email")
    frame_pilihan.pack_forget()
    frame_email.pack(expand=True, fill="both")
    try:
        report_email.setup_email_frame(frame_email, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor report_email: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Report Email: {str(e)}")

def open_assistant():
    print("Membuka Asisten Virtual")
    frame_pilihan.pack_forget()
    assistant_frame = tk.Frame(window, bg="#f5f6f5")
    assistant_frame.pack(expand=True, fill="both")

    # Buat asisten virtual
    qa = create_assistant()

    def tanya():
        pertanyaan = entry_pertanyaan.get()
        if not pertanyaan.strip():
            return
        jawaban = qa(pertanyaan)  # Gunakan fungsi tanya dari create_assistant()
        hasil_text.insert(tk.END, f"🧑: {pertanyaan}\n🤖: {jawaban}\n\n")
        entry_pertanyaan.delete(0, tk.END)

    label = tk.Label(assistant_frame, text="Tanya Asisten", font=("Helvetica", 16), bg="#f5f6f5")
    label.pack(pady=10)

    hasil_text = tk.Text(assistant_frame, height=20, wrap="word", font=("Helvetica", 12))
    hasil_text.pack(padx=20, pady=10, fill="both", expand=True)

    entry_pertanyaan = tk.Entry(assistant_frame, font=("Helvetica", 12))
    entry_pertanyaan.pack(padx=20, pady=(10, 0), fill="x")
    entry_pertanyaan.bind("<Return>", lambda event: tanya())

    btn_kirim = ttk.Button(assistant_frame, text="Kirim", command=tanya)
    btn_kirim.pack(pady=(5, 20))

    btn_kembali = ttk.Button(assistant_frame, text="Kembali", command=lambda: [assistant_frame.pack_forget(), frame_pilihan.pack(expand=True, fill="both")])
    btn_kembali.pack()

def open_memo_manager():
    print("Membuka memo manager")
    frame_pilihan.pack_forget()
    frame_memo.pack(expand=True, fill="both")
    try:
        memo_manager.setup_memo_frame(frame_memo, operator_name, kembali_pilihan)
    except ImportError as e:
        logging.error(f"Gagal mengimpor memo_manager: {str(e)}")
        messagebox.showerror("Error", f"Gagal membuka Memo Manager: {str(e)}")

# --- Widget untuk Login ---
login_container = tk.Frame(frame_login, bg="white", bd=2, relief="groove")
login_container.place(relx=0.5, rely=0.5, anchor="center")

label_judul = tk.Label(login_container, text="Monitoring SAPP", font=("Helvetica", 24, "bold"), bg="white")
label_judul.pack(pady=(30, 10))

login_frame = tk.LabelFrame(login_container, text="Login", font=("Helvetica", 12), bg="white", padx=20, pady=20)
login_frame.pack(padx=30, pady=10)

from ui_utils import create_styled_label
label_nama = create_styled_label(login_frame, "Masukkan Nama Anda:", bg_color="white")
label_nama.grid(row=0, column=0, sticky="w", pady=5, padx=10)

entry_nama = tk.Entry(login_frame, font=("Helvetica", 12), width=25)
entry_nama.grid(row=0, column=1, pady=5)
entry_nama.bind("<Return>", lambda event: tombol_masuk())

btn_masuk = ttk.Button(login_frame, text="Masuk", command=tombol_masuk)
btn_masuk.grid(row=1, column=0, columnspan=2, pady=10)

status_label = tk.Label(login_container, text="", font=("Helvetica", 10), bg="white")
status_label.pack(pady=(0, 20))

# --- Widget untuk Pilihan ---
pilihan_container = tk.Frame(frame_pilihan, bg="#f5f6f5")
pilihan_container.pack(expand=True)

label_selamat = tk.Label(pilihan_container, text="", font=("Helvetica", 16, "bold"), bg="#f5f6f5")
label_selamat.pack(pady=20)

button_frame = tk.Frame(pilihan_container, bg="#f5f6f5")
button_frame.pack(pady=20)

from ui_utils import create_styled_button
btn_recap = create_styled_button(button_frame, "Recap Zabbix", open_recap_zabbix, "#3498db", tooltip_text="Buat rekap monitoring Zabbix", width=15)
btn_recap.grid(row=0, column=0, padx=10, pady=10)

btn_report = create_styled_button(button_frame, "Report Email", open_report_email, "#2ecc71", tooltip_text="Kirim laporan via email", width=15)
btn_report.grid(row=0, column=1, padx=10, pady=10)

btn_assistant = create_styled_button(button_frame, "Assistant", open_assistant, "#e67e22", tooltip_text="Dapatkan bantuan dari asisten virtual", width=15)
btn_assistant.grid(row=0, column=2, padx=10, pady=10)

btn_memo = create_styled_button(button_frame, "Memo", open_memo_manager, "#f1c40f", tooltip_text="Catat dan kelola memo", width=15)
btn_memo.grid(row=0, column=3, padx=10, pady=10)

btn_kembali = create_styled_button(button_frame, "Kembali", kembali_login, "#e74c3c", tooltip_text="Kembali ke halaman login", width=15)
btn_kembali.grid(row=1, column=1, padx=10, pady=10)

btn_keluar = create_styled_button(button_frame, "Keluar", keluar_aplikasi, "#95a5a6", tooltip_text="Keluar dari aplikasi", width=15)
btn_keluar.grid(row=1, column=2, padx=10, pady=10)

print("Memulai mainloop")
window.mainloop()

if __name__ == "__main__":
    asisten = create_assistant()
    pertanyaan = "Apa itu AI?"
    jawaban = asisten(pertanyaan)
    print("🤖:", jawaban)
