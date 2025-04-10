import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import re
import logging

load_dotenv()
EMAIL_PENGIRIM = os.getenv("EMAIL_PENGIRIM")
PASSWORD_EMAIL = os.getenv("PASSWORD_EMAIL")

logging.basicConfig(filename="app.log", level=logging.ERROR)

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def setup_email_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    frame.configure(bg="#f5f6f5")

    main_container = tk.Frame(frame, bg="#f5f6f5", width=900, height=700)
    main_container.place(relx=0.5, rely=0.5, anchor="center")
    main_container.pack_propagate(False)

    from ui_utils import create_styled_label
    create_styled_label(main_container, f"📧 Report Email - {operator_name}", 20).pack(pady=(20, 10))

    input_frame = tk.LabelFrame(main_container, text="Email Settings", font=("Segoe UI", 12, "bold"),
                                bg="#f5f6f5", fg="#34495e", padx=15, pady=15, bd=2, relief="groove")
    input_frame.pack(pady=10)

    create_styled_label(input_frame, "To (Penerima):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    entry_to = tk.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_to.grid(row=0, column=1, pady=5)

    create_styled_label(input_frame, "CC:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    entry_cc = tk.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_cc.grid(row=1, column=1, pady=5)

    create_styled_label(input_frame, "Subject:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    entry_subject = tk.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_subject.grid(row=2, column=1, pady=5)

    create_styled_label(input_frame, "Body (Isi Email):").grid(row=3, column=0, sticky="nw", padx=10, pady=5)
    text_body = tk.Text(input_frame, height=8, width=60, font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=5, pady=5)
    text_body.grid(row=3, column=1, pady=5)

    create_styled_label(input_frame, "Lampiran:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
    lampiran_path = tk.StringVar()
    entry_lampiran = tk.Entry(input_frame, textvariable=lampiran_path, font=("Segoe UI", 11), width=38)
    entry_lampiran.grid(row=4, column=1, sticky="w", pady=5)

    def pilih_lampiran():
        folder_path = os.path.join(os.getcwd(), "zabbix recap")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = filedialog.askopenfilename(initialdir=folder_path, title="Pilih Lampiran",
                                               filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if file_path:
            lampiran_path.set(file_path)
            status_label.config(text=f"Lampiran dipilih: {os.path.basename(file_path)}", fg="green")

    from ui_utils import create_styled_button
    create_styled_button(input_frame, "Pilih File", pilih_lampiran, "#3498db", tooltip_text="Pilih file untuk dilampirkan").grid(row=4, column=2, padx=5, pady=5)

    button_frame = tk.Frame(main_container, bg="#f5f6f5")
    button_frame.pack(pady=15)

    progress = ttk.Progressbar(button_frame, mode="indeterminate")

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

    create_styled_button(button_frame, "📤 Kirim", kirim_email, "#2ecc71", tooltip_text="Kirim email dengan lampiran").grid(row=0, column=0, padx=5)
    create_styled_button(button_frame, "🔙 Kembali", kembali_callback, "#e74c3c", tooltip_text="Kembali ke menu utama").grid(row=0, column=1, padx=5)

    status_label = create_styled_label(main_container, "")
    status_label.pack(pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x720")
    root.title("Report Email")
    frame = tk.Frame(root, bg="#f5f6f5")
    frame.pack(expand=True, fill=tk.BOTH)
    setup_email_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()