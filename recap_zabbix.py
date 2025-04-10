import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging

logging.basicConfig(filename="app.log", level=logging.ERROR)

def parse_duration(duration_str):
    total_seconds = 0
    duration_str = str(duration_str).lower()
    matches = re.findall(r"(\d+)\s*([a-zA-Z]+)", duration_str)
    for val, unit in matches:
        val = int(val)
        if unit == "m" and "d" in duration_str:
            total_seconds += val * 30 * 86400
        elif unit == "d":
            total_seconds += val * 86400
        elif unit == "h":
            total_seconds += val * 3600
        elif unit == "m" and "h" in duration_str:
            total_seconds += val * 60
        elif unit == "s":
            total_seconds += val
    return total_seconds

def calculate_duration(start_time, status):
    current_date = datetime.now()
    for fmt in ("%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"):
        try:
            start_date = datetime.strptime(start_time, fmt)
            break
        except ValueError:
            continue
    
    if status == "PROBLEM":
        delta = current_date - start_date
        total_seconds = int(delta.total_seconds())
    else:
        total_seconds = 0
    
    return total_seconds * 1000

def standardize_duration(total_ms):
    ms = total_ms
    months = ms // (30 * 86400000)
    days = (ms % (30 * 86400000)) // 86400000
    hours = (ms % 86400000) // 3600000
    minutes = (ms % 3600000) // 60000

    duration_parts = []
    if months > 0:
        duration_parts.append(f"{months} bulan")
    if days > 0:
        duration_parts.append(f"{days} hari")
    if hours > 0:
        duration_parts.append(f"{hours} jam")
    if minutes > 0:
        duration_parts.append(f"{minutes} menit")
    return " ".join(duration_parts) if duration_parts else "0 menit"

def format_date(date_str):
    for fmt in ("%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%d-%b-%Y %H:%M"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return str(date_str)

def get_shift_date_range(shift, date_str):
    try:
        d = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
        shifts = {"A": [6, 15, 0, False], "C": [14, 23, 0, False], "M": [22, 7, 1, False], "D": [0, 23, 0, True]}
        start_hour, end_hour, next_day, is_full_day = shifts.get(shift, [0, 23, 0, True])
        start = d.replace(hour=start_hour, minute=0)
        end = d.replace(hour=end_hour, minute=59 if is_full_day else 0)
        if next_day:
            end = end.replace(day=d.day + 1)
        fmt = "%d/%m/%Y %H:%M"
        return f"{start.strftime(fmt)} - {end.strftime(fmt)}"
    except Exception as e:
        logging.error(f"Error parsing shift date: {str(e)}")
        return "Tanggal tidak valid"

def get_shift_header(shift):
    headers = {
        "A": "Selamat sore, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift A",
        "C": "Selamat malam, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift C",
        "M": "Selamat pagi, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift M",
        "D": "Selamat malam, berikut rekap daily problem Zabbix monitoring IFG",
    }
    return headers.get(shift, "Selamat malam, berikut rekap problem Zabbix monitoring IFG")

def analyze_csv(files, shift, operator_name):
    all_rows = []
    seen_problems = set()
    first_date = None

    for file in files:
        try:
            df = pd.read_csv(file, encoding="utf-8")
            df.columns = df.columns.str.strip()
            required_columns = {'Host', 'Time', 'Status', 'Duration', 'Problem', 'Tags'}
            if not required_columns.issubset(df.columns):
                messagebox.showerror("Error", f"Kolom berikut hilang di CSV: {required_columns - set(df.columns)}")
                return None, None

            for _, row in df.iterrows():
                if row["Status"] not in ["PROBLEM", "RESOLVED"]:
                    continue
                duration_ms = parse_duration(row["Duration"])
                if duration_ms < 3600000:
                    continue
                problem_key = f"{row['Host']}-{row['Time']}-{row['Problem']}"
                if problem_key not in seen_problems:
                    seen_problems.add(problem_key)
                    all_rows.append(row)
                    if first_date is None:
                        first_date = row["Time"]
        except FileNotFoundError:
            messagebox.showerror("Error", f"File {file} tidak ditemukan")
            return None, None
        except Exception as e:
            logging.error(f"Gagal membaca file {file}: {str(e)}")
            messagebox.showerror("Error", f"Gagal membaca file {file}: {str(e)}")
            return None, None

    if not all_rows:
        messagebox.showwarning("Peringatan", "Tidak ada data yang memenuhi kriteria (durasi >= 1 jam)!")
        return "", None

    problem_groups = {}
    for row in all_rows:
        status = "Belum Resolved" if row["Status"] == "PROBLEM" else "Resolved"
        tags = str(row["Tags"])
        ticket_match = re.search(r"__zbx_jira_issuekey: (IFG-\d+)", tags)
        ticket_id = ticket_match.group(1) if ticket_match else "IFG-Unknown"
        duration_ms = calculate_duration(row["Time"], row["Status"])
        entry = f"- {row['Host']}  Durasi: {standardize_duration(duration_ms)} (start {format_date(row['Time'])})  *{status}*  Ticket ID: {ticket_id}"
        problem = str(row["Problem"]).strip()

        if "Windows: FS" in problem and "Space is critically low" in problem:
            problem = "Windows: Space is critically low"
        elif "Space is critically low" in problem:
            problem = "Space is critically low"

        if problem not in problem_groups:
            problem_groups[problem] = []
        problem_groups[problem].append(entry)

    report = f"{get_shift_header(shift)}\n{get_shift_date_range(shift, first_date)}\n\n"
    for problem, entries in problem_groups.items():
        report += f"{problem}\n" + "\n".join(entries) + "\n\n"
    report += f"Terima kasih\nFDS Monitoring - {operator_name}"
    return report, problem_groups

def export_to_pdf(files, shift, operator_name):
    report, problem_groups = analyze_csv(files, shift, operator_name)
    if not report:
        return

    output_folder = os.path.join(os.getcwd(), "zabbix recap")
    os.makedirs(output_folder, exist_ok=True)
    file_name = f"Zabbix_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    output_path = os.path.join(output_folder, file_name)

    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()

        centered_title = styles['Title']
        centered_title.alignment = 1
        centered_normal = styles['Normal']
        centered_normal.alignment = 1
        centered_heading = styles['Heading2']
        centered_heading.alignment = 1

        story = [
            Paragraph("IFG Zabbix Monitoring Issue Summary", centered_title),
            Paragraph(f"Period: {get_shift_date_range(shift, pd.read_csv(files[0]).iloc[0]['Time'])}", centered_normal),
            Paragraph(f"Created By: FDS Monitoring - {operator_name}", centered_normal),
            Spacer(1, 12)
        ]

        def create_table(title, entries):
            if not entries:
                return
            story.append(Paragraph(title, centered_heading))
            table_data = [["Host", "Duration", "Time Start", "Ticket ID", "Status"]]
            for entry in entries:
                match = re.match(r"- (.*?)  Durasi: (.*?) \(start (.*?)\)  \*(.*?)\*  Ticket ID: (.*)", entry)
                if match:
                    host, duration, start_time, status, ticket_id = match.groups()
                    table_data.append([host, duration, start_time, ticket_id, status])
                else:
                    table_data.append([entry, "", "", "", ""])
            table = Table(table_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

        for problem, entries in problem_groups.items():
            create_table(problem, entries)

        doc.build(story)
        messagebox.showinfo("Sukses", f"PDF berhasil disimpan di:\n{output_path}")
    except Exception as e:
        logging.error(f"Gagal mengekspor PDF: {str(e)}")
        messagebox.showerror("Error", f"Gagal mengekspor PDF: {str(e)}")

def setup_recap_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    frame.configure(bg="#f5f6f5")
    main_container = tk.Frame(frame, bg="#f5f6f5")
    main_container.pack(expand=True, fill="both")

    canvas_frame = tk.Frame(main_container, bg="#f5f6f5", width=800, height=650)
    canvas_frame.pack(side="top", padx=(100,0), pady=20, expand=False)
    canvas_frame.pack_propagate(False)

    canvas = tk.Canvas(canvas_frame, bg="#f5f6f5", width=800, height=650, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollable_frame = tk.Frame(canvas, bg="#f5f6f5")
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    from ui_utils import create_styled_label
    create_styled_label(scrollable_frame, "🛠️ Recap Zabbix", 20).pack(pady=(20, 10))

    input_frame = tk.LabelFrame(scrollable_frame, text="Input Data", font=("Segoe UI", 12, "bold"), bg="#f5f6f5", fg="#34495e", padx=15, pady=10, bd=2, relief="groove")
    input_frame.pack(pady=20)

    create_styled_label(input_frame, "📁 Pilih File CSV:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    files_var = []
    def upload_files():
        files = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if files:
            files_var.clear()
            files_var.extend(files)
            status_label.config(text=f"{len(files)} file diunggah ✅", fg="green")
    from ui_utils import create_styled_button
    create_styled_button(input_frame, "Unggah File", upload_files, "#3498db", tooltip_text="Unggah file CSV untuk analisis").grid(row=0, column=1, pady=5, padx=5)

    create_styled_label(input_frame, "⏱️ Pilih Shift:", bg_color="#f5f6f5").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    shift_var = tk.StringVar(value="D")
    ttk.Combobox(input_frame, textvariable=shift_var, values=["A", "C", "M", "D"], width=10).grid(row=1, column=1, pady=5)

    report_frame = tk.Frame(scrollable_frame, bg="#f5f6f5")
    report_frame.pack(pady=10)
    report_text = tk.Text(report_frame, height=18, width=100, font=("Consolas", 10), borderwidth=1, relief="solid", padx=5, pady=5, wrap=tk.WORD)
    text_scroll = tk.Scrollbar(report_frame, command=report_text.yview)
    report_text.configure(yscrollcommand=text_scroll.set)
    text_scroll.pack(side="right", fill="y")
    report_text.pack(side="left", fill="x")

    button_frame = tk.Frame(scrollable_frame, bg="#f5f6f5")
    button_frame.pack(pady=20)
    progress = ttk.Progressbar(button_frame, mode="indeterminate")

    def generate_report():
        if not files_var:
            status_label.config(text="❌ Silakan unggah file CSV!", fg="red")
            return
        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        report, _ = analyze_csv(files_var, shift_var.get(), operator_name)
        if report is not None:
            report_text.delete(1.0, tk.END)
            report_text.insert(tk.END, report)
            status_label.config(text="✅ Laporan berhasil dibuat", fg="green")
        progress.stop()
        progress.grid_forget()

    def save_pdf():
        if not files_var:
            status_label.config(text="❌ Silakan unggah file CSV!", fg="red")
            return
        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        export_to_pdf(files_var, shift_var.get(), operator_name)
        progress.stop()
        progress.grid_forget()

    create_styled_button(button_frame, "📝 Generate Report", generate_report, "#2ecc71", tooltip_text="Buat laporan dari data CSV").grid(row=0, column=0, padx=5)
    create_styled_button(button_frame, "📄 Export to PDF", save_pdf, "#e67e22", tooltip_text="Ekspor laporan ke PDF").grid(row=0, column=1, padx=5)
    create_styled_button(button_frame, "🔙 Kembali", kembali_callback, "#e74c3c", tooltip_text="Kembali ke menu utama").grid(row=0, column=2, padx=5)

    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Zabbix Recap")
    root.geometry("1280x720")
    frame = tk.Frame(root, bg="#f5f6f5")
    frame.pack(expand=True, fill=tk.BOTH)
    setup_recap_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()