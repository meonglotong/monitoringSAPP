import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import re
import logging
from tkinter import messagebox, filedialog

load_dotenv()
EMAIL_PENGIRIM = os.getenv("EMAIL_PENGIRIM")
PASSWORD_EMAIL = os.getenv("PASSWORD_EMAIL")

logging.basicConfig(filename="app.log", level=logging.ERROR)

def is_valid_email(email):
    pattern = r"^[a-zA-Z0.9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def setup_email_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    main_container = tk.Frame(frame)
    main_container.pack(expand=True, fill="both")

    # Menggunakan ukuran kanvas yang sama seperti recap_zabbix.py
    canvas_frame = tk.Frame(main_container, width=1920, height=1080)
    canvas_frame.pack(side="top", padx=0, pady=20, expand=False)
    canvas_frame.pack_propagate(False)

    canvas = tk.Canvas(canvas_frame, width=1920, height=1080, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttkb.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview, bootstyle=SECONDARY)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = tk.Frame(canvas)
    # Menempatkan scrollable_frame pada posisi X=500, Y=50 dengan anchor="nw"
    canvas.create_window((500, 50), window=scrollable_frame, anchor="nw")

    # Memperbarui scrollregion tanpa mengatur ulang posisi scrollable_frame
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    from ui_utils import create_styled_label, create_tooltip
    create_styled_label(scrollable_frame, f"📧 Report Email - {operator_name}", 20).pack(pady=(20, 10))

    input_frame = ttkb.LabelFrame(scrollable_frame, text="Email Settings", padding=15)
    input_frame.pack(pady=20)

    # Mengatur lebar minimum kolom 0 agar label memiliki lebar yang konsisten
    input_frame.columnconfigure(0, minsize=120)  # Sesuaikan minsize sesuai kebutuhan

    # Baris 1: To (Penerima)
    create_styled_label(input_frame, "To (Penerima)").grid(row=0, column=0, sticky="w", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=0, column=1, sticky="w", padx=(5, 15), pady=5)  # Tambah jarak dengan padx
    entry_to = ttkb.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_to.grid(row=0, column=2, pady=5, sticky="w")

    # Baris 2: CC
    create_styled_label(input_frame, "CC").grid(row=1, column=0, sticky="w", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=1, column=1, sticky="w", padx=(5, 15), pady=5)
    entry_cc = ttkb.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_cc.grid(row=1, column=2, pady=5, sticky="w")

    # Baris 3: Subject
    create_styled_label(input_frame, "Subject").grid(row=2, column=0, sticky="w", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=2, column=1, sticky="w", padx=(5, 15), pady=5)
    entry_subject = ttkb.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_subject.grid(row=2, column=2, pady=5, sticky="w")

    # Baris 4: Body (Isi Email)
    create_styled_label(input_frame, "Body (Isi Email)").grid(row=3, column=0, sticky="w", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=3, column=1, sticky="w", padx=(5, 15), pady=5)
    text_body = tk.Text(input_frame, height=6, width=50, font=("Segoe UI", 11), borderwidth=1, relief="solid")
    text_body.grid(row=3, column=2, pady=5, sticky="w")

    # Baris 5: Lampiran
    create_styled_label(input_frame, "Lampiran").grid(row=4, column=0, sticky="w", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=4, column=1, sticky="w", padx=(5, 15), pady=5)
    lampiran_path = tk.StringVar()
    entry_lampiran = ttkb.Entry(input_frame, textvariable=lampiran_path, font=("Segoe UI", 11), width=50)
    entry_lampiran.grid(row=4, column=2, sticky="w", pady=5)

    def pilih_lampiran():
        folder_path = os.path.join(os.getcwd(), "zabbix recap")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = filedialog.askopenfilename(initialdir=folder_path, title="Pilih Lampiran",
                                               filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if file_path:
            lampiran_path.set(file_path)
            status_label.config(text=f"Lampiran dipilih: {os.path.basename(file_path)}", fg="green")

    btn_pilih = ttkb.Button(input_frame, text="Pilih File", command=pilih_lampiran, bootstyle=INFO)
    btn_pilih.grid(row=5, column=2)
    create_tooltip(btn_pilih, "Pilih file untuk dilampirkan")

    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(pady=20)

    progress = ttkb.Progressbar(button_frame, mode="indeterminate", bootstyle=INFO)

    def kirim_email():
        to = entry_to.get().strip()
        cc = entry_cc.get().strip()
        subject = entry_subject.get().strip()
        body = text_body.get("1.0", tk.END).strip()
        attachment = lampiran_path.get().strip()

        if not to or not subject:
            status_label.config(text="❌ Isi To dan Subject tidak boleh kosong!", fg="red")
            return

        all_recipients = [email.strip() for email in (to.split(",") + cc.split(",")) if email.strip()]
        if not all(is_valid_email(email) for email in all_recipients):
            status_label.config(text="❌ Alamat email tidak valid!", fg="red")
            return

        progress.grid(row=1, column=0, columnspan=2, pady=5)
        progress.start()
        status_label.config(text="⏳ Mengirim email...", fg="blue")

        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_PENGIRIM
            msg["To"] = to
            msg["Cc"] = cc
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if attachment and os.path.exists(attachment):
                filename = os.path.basename(attachment)
                with open(attachment, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    msg.attach(part)

            smtp = smtplib.SMTP("smtp.gmail.com", 587)
            smtp.starttls()
            smtp.login(EMAIL_PENGIRIM, PASSWORD_EMAIL)
            smtp.sendmail(EMAIL_PENGIRIM, all_recipients, msg.as_string())
            smtp.quit()

            status_label.config(text=f"✅ Email berhasil dikirim ke {to}", fg="green")
        except smtplib.SMTPAuthenticationError:
            status_label.config(text="❌ Kredensial email salah!", fg="red")
            logging.error("Autentikasi gagal untuk %s", EMAIL_PENGIRIM)
        except smtplib.SMTPException as e:
            status_label.config(text=f"❌ Error SMTP: {str(e)}", fg="red")
            logging.error("Error SMTP: %s", str(e))
        except FileNotFoundError:
            status_label.config(text="❌ Lampiran tidak ditemukan!", fg="red")
            logging.error("Lampiran tidak ditemukan: %s", attachment)
        except Exception as e:
            status_label.config(text=f"❌ Gagal mengirim email: {str(e)}", fg="red")
            logging.error("Gagal mengirim email: %s", str(e))
        finally:
            progress.stop()
            progress.grid_forget()

    btn_kirim = ttkb.Button(button_frame, text="📤 Kirim", command=kirim_email, bootstyle=SUCCESS)
    btn_kirim.grid(row=0, column=0, padx=5)
    create_tooltip(btn_kirim, "Kirim email dengan lampiran")

    btn_kembali = ttkb.Button(button_frame, text="🔙 Kembali", command=kembali_callback, bootstyle=SECONDARY)
    btn_kembali.grid(row=0, column=1, padx=5)
    create_tooltip(btn_kembali, "Kembali ke menu utama")

    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

if __name__ == "__main__":
    from ui_utils import get_theme
    root = ttkb.Window(themename=get_theme())
    root.geometry("1920x1080")  # Menyesuaikan ukuran window seperti recap_zabbix.py
    root.title("Report Email")
    frame = tk.Frame(root)
    frame.pack(expand=True, fill=tk.BOTH)
    setup_email_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()