import os
import re
import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging
from tkinter import messagebox, filedialog

# Impor fungsi dari zabbix_api.py
try:
    from zabbix_api import fetch_zabbix_data
except ImportError:
    fetch_zabbix_data = None
    logging.error("Failed to import fetch_zabbix_data from zabbix_api.py")

# Konfigurasi Logging
logging.basicConfig(
    filename="recap_zabbix.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Fungsi Utilitas
def parse_duration(duration_str):
    total_seconds = 0
    duration_str = str(duration_str).lower().strip()
    matches = re.findall(r"(\d+)\s*([a-zA-Z]+)", duration_str)
    for val, unit in matches:
        val = int(val)
        if unit.startswith("m") and ("bulan" in duration_str or "month" in duration_str):
            total_seconds += val * 30 * 86400
        elif unit.startswith("d"):
            total_seconds += val * 86400
        elif unit.startswith("h"):
            total_seconds += val * 3600
        elif unit.startswith("m") and ("menit" in duration_str or "minute" in duration_str or "m " in duration_str):
            total_seconds += val * 60
        elif unit.startswith("s"):
            total_seconds += val
    logging.debug(f"Parsed duration '{duration_str}' to {total_seconds} seconds")
    return total_seconds

def calculate_duration(start_time, status):
    current_date = datetime.now()
    for fmt in ("%Y-%m-%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            start_date = datetime.strptime(start_time, fmt)
            break
        except ValueError:
            continue
    else:
        logging.error(f"Invalid date format: {start_time}")
        return 0
    
    if status == "PROBLEM":
        delta = current_date - start_date
        total_seconds = int(delta.total_seconds())
    else:
        total_seconds = 0
    
    logging.debug(f"Calculated duration for '{start_time}' (status: {status}) = {total_seconds} seconds")
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
    result = " ".join(duration_parts) if duration_parts else "0 menit"
    logging.debug(f"Standardized duration {total_ms}ms to '{result}'")
    return result

def format_date(date_str):
    for fmt in (
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d-%b-%Y %H:%M"
    ):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    logging.error(f"Failed to format date: {date_str}")
    return str(date_str)

def get_shift_date_range(shift, date_str):
    try:
        d = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
        shifts = {
            "A": [6, 15, 0, False],
            "C": [14, 23, 0, False],
            "M": [22, 7, 1, False],
            "D": [0, 23, 0, True]
        }
        start_hour, end_hour, next_day, is_full_day = shifts.get(shift, [0, 23, 0, True])
        start = d.replace(hour=start_hour, minute=0)
        end = d.replace(hour=end_hour, minute=59 if is_full_day else 0)
        if next_day:
            end = end.replace(day=d.day + 1)
        fmt = "%d/%m/%Y %H:%M"
        result = f"{start.strftime(fmt)} - {end.strftime(fmt)}"
        logging.debug(f"Shift {shift} date range for {date_str}: {result}")
        return result
    except Exception as e:
        logging.error(f"Error parsing shift date '{date_str}': {str(e)}")
        return "Tanggal tidak valid"

def get_shift_header(shift):
    headers = {
        "A": "Selamat sore, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift A",
        "C": "Selamat malam, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift C",
        "M": "Selamat pagi, berikut rekap shift problem Zabbix monitoring IFG pada akhir shift M",
        "D": "Selamat malam, berikut rekap daily problem Zabbix monitoring IFG",
    }
    header = headers.get(shift, "Selamat malam, berikut rekap problem Zabbix monitoring IFG")
    logging.debug(f"Shift header for {shift}: {header}")
    return header

# Fungsi Analisis Data
def analyze_data(df, shift, operator_name):
    if df.empty:
        logging.warning("Empty DataFrame provided to analyze_data")
        return "", None

    seen_problems = set()
    problem_groups = {}
    first_date = None
    filtered_problems = []
    raw_entries = []

    # Ambil rentang shift untuk filter tanggal (opsional)
    shift_start, shift_end = None, None
    if shift == "D":
        try:
            d = datetime.now()
            shift_start = d.replace(hour=0, minute=0, second=0, microsecond=0)
            shift_end = d.replace(hour=23, minute=59, second=59, microsecond=999999)
        except Exception as e:
            logging.error(f"Error setting shift range: {e}")

    for _, row in df.iterrows():
        if row["Status"] not in ["PROBLEM", "RESOLVED"]:
            logging.debug(f"Skipping row with invalid status: {row['Status']} (Host: {row['Host']})")
            filtered_problems.append(f"Invalid status: {row['Problem']} (Host: {row['Host']})")
            continue

        # Simpan entri mentah untuk debugging
        raw_entries.append({
            "Host": row["Host"],
            "Time": row["Time"],
            "Problem": row["Problem"],
            "Status": row["Status"],
            "Duration": row["Duration"],
            "Tags": row["Tags"],
            "EventID": row.get("EventID", "N/A")
        })

        duration_ms = parse_duration(row["Duration"])
        problem_key = f"{row['Host']}-{row['Time']}-{row['Problem']}-{row.get('EventID', 'N/A')}"
        if problem_key not in seen_problems:
            seen_problems.add(problem_key)
            if first_date is None:
                first_date = row["Time"]

            status = "Belum Resolved" if row["Status"] == "PROBLEM" else "Resolved"
            tags = str(row["Tags"]).strip()
            ticket_match = re.search(
                r"__zbx_jira_issuekey\s*[:=]\s*(IFG-\d+|[\w-]+)",
                tags,
                re.IGNORECASE
            )
            ticket_id = ticket_match.group(1) if ticket_match else "IFG-Unknown"
            
            logging.debug(
                f"EventID: {row.get('EventID', 'N/A')}, "
                f"Host: {row['Host']}, "
                f"Problem: {row['Problem']}, "
                f"Tags: {tags}, "
                f"Ticket ID: {ticket_id}"
            )
            
            duration_ms = calculate_duration(row["Time"], row["Status"])
            host_display = row["Host"]
            
            entry = (
                f"- {host_display}  Durasi: {standardize_duration(duration_ms)} "
                f"(start {format_date(row['Time'])}) Ticket ID: {ticket_id} *{status}*"
            )

            # Kelompokkan problem
            problem = str(row["Problem"]).strip()
            if "Windows: FS" in problem and "Space is critically low" in problem:
                problem = "Windows: Space is critically low"
            elif "Space is critically low" in problem:
                problem = "Windows: Space is critically low"
            elif "subslot 0/0 transceiver" in problem and "Temperature" in problem:
                problem = "Temperature Issue"

            if problem not in problem_groups:
                problem_groups[problem] = []
            problem_groups[problem].append(entry)

    # Simpan entri mentah ke CSV
    try:
        pd.DataFrame(raw_entries).to_csv("zabbix_processed_data.csv", index=False)
        logging.info("Saved processed data to zabbix_processed_data.csv")
    except Exception as e:
        logging.error(f"Failed to save processed data: {e}")

    if filtered_problems:
        logging.info(f"Filtered problems: {', '.join(filtered_problems)}")
        with open("filtered_problems.txt", "w") as f:
            f.write("\n".join(filtered_problems))
        logging.info("Saved filtered problems to filtered_problems.txt")

    if not problem_groups:
        logging.warning("No problems met criteria")
        return "", None

    report = f"{get_shift_header(shift)}\n{get_shift_date_range(shift, first_date)}\n\n"
    for problem in sorted(problem_groups.keys()):
        report += f"{problem}\n" + "\n".join(sorted(problem_groups[problem])) + "\n\n"
    report += f"Terima kasih\nFDS Monitoring - {operator_name}"
    
    logging.info(f"Generated report with {len(problem_groups)} problem groups")
    return report, problem_groups

# Fungsi Ekspor PDF
def export_to_pdf(df, shift, operator_name):
    report, problem_groups = analyze_data(df, shift, operator_name)
    if not report:
        messagebox.showwarning("Peringatan", "Tidak ada data yang memenuhi kriteria!")
        logging.warning("No report generated for PDF export")
        return

    output_folder = os.path.join(os.getcwd(), "zabbix_recap")
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

        first_date = df.iloc[0]["Time"] if not df.empty else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story = [
            Paragraph("IFG Zabbix Monitoring Issue Summary", centered_title),
            Paragraph(f"Period: {get_shift_date_range(shift, first_date)}", centered_normal),
            Paragraph(f"Created By: FDS Monitoring - {operator_name}", centered_normal),
            Spacer(1, 12)
        ]

        def create_table(title, entries):
            if not entries:
                story.append(Paragraph(title, centered_heading))
                story.append(Paragraph("Tidak ada masalah untuk kategori ini.", centered_normal))
                story.append(Spacer(1, 12))
                logging.info(f"No entries for problem category: {title}")
                return
            story.append(Paragraph(title, centered_heading))
            table_data = [["Host", "Duration", "Time Start", "Ticket ID", "Status"]]
            for entry in entries:
                # Updated regex to match the correct format
                match = re.match(
                    r"- (.*?)  Durasi: (.*?) \(start (.*?)\) Ticket ID: (.*?) \*(.*?)\*",
                    entry
                )
                if match:
                    host, duration, start_time, ticket_id, status = match.groups()
                    table_data.append([host, duration, start_time, ticket_id, status])
                else:
                    logging.error(f"Failed to parse table entry: {entry}")
                    table_data.append([entry, "", "", "", "Parsing Error"])
            table = Table(table_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),  # Support text wrapping
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

        for problem in sorted(problem_groups.keys()):
            create_table(problem, sorted(problem_groups[problem]))

        doc.build(story)
        messagebox.showinfo("Sukses", f"PDF berhasil disimpan di:\n{output_path}")
        logging.info(f"PDF exported successfully to {output_path}")
    except Exception as e:
        logging.error(f"Failed to export PDF: {str(e)}")
        messagebox.showerror("Error", f"Gagal mengekspor PDF: {str(e)}")

# Fungsi UI
def create_styled_label(parent, text, font_size=12):
    return tk.Label(parent, text=text, font=("Arial", font_size, "bold"))

def create_tooltip(widget, text):
    from tkinter import Toplevel
    tooltip = None

    def show_tooltip(event):
        nonlocal tooltip
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 20
        tooltip = Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(event):
        nonlocal tooltip
        if tooltip:
            tooltip.destroy()
            tooltip = None

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)

def setup_recap_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    main_container = tk.Frame(frame)
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
    canvas.create_window((600, 20), window=scrollable_frame, anchor="nw")
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    create_styled_label(scrollable_frame, "🛠️ Recap Zabbix", 20).pack(pady=(20, 10))

    input_frame = ttkb.LabelFrame(scrollable_frame, text="Input Data", padding=15)
    input_frame.pack(pady=20)

    # Pilihan sumber data
    create_styled_label(input_frame, "📡 Sumber Data:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    data_source_var = tk.StringVar(value="API")
    data_source_combobox = ttkb.Combobox(input_frame, textvariable=data_source_var, values=["API", "CSV"], width=10)
    data_source_combobox.grid(row=0, column=1, pady=5)

    # Unggah file CSV
    create_styled_label(input_frame, "📁 Pilih File CSV:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    files_var = []
    def upload_files():
        files = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if files:
            files_var.clear()
            files_var.extend(files)
            status_label.config(text=f"{len(files)} file diunggah ✅", fg="green")
            logging.info(f"Uploaded {len(files)} CSV files")

    btn_upload = ttkb.Button(input_frame, text="Unggah File", command=upload_files, bootstyle=INFO)
    btn_upload.grid(row=1, column=1, pady=5, padx=5)
    create_tooltip(btn_upload, "Unggah file CSV untuk analisis")

    # Pilihan shift
    create_styled_label(input_frame, "⏱️ Pilih Shift:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    shift_var = tk.StringVar(value="D")
    shift_combobox = ttkb.Combobox(input_frame, textvariable=shift_var, values=["A", "C", "M", "D"], width=10)
    shift_combobox.grid(row=2, column=1, pady=5)

    report_frame = tk.Frame(scrollable_frame)
    report_frame.pack(pady=10)
    report_text = tk.Text(
        report_frame,
        height=18,
        width=100,
        font=("Consolas", 10),
        borderwidth=1,
        relief="solid",
        padx=5,
        pady=5,
        wrap=tk.WORD
    )
    text_scroll = ttkb.Scrollbar(report_frame, command=report_text.yview, bootstyle=SECONDARY)
    report_text.configure(yscrollcommand=text_scroll.set)
    text_scroll.pack(side="right", fill="y")
    report_text.pack(side="left", fill="x")

    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(pady=20)
    progress = ttkb.Progressbar(button_frame, mode="indeterminate", bootstyle=INFO)

    def generate_report():
        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        report_text.delete(1.0, tk.END)
        
        logging.info(f"Generating report with source: {data_source_var.get()}, shift: {shift_var.get()}")
        
        if data_source_var.get() == "API":
            if fetch_zabbix_data is None:
                status_label.config(text="❌ Modul zabbix_api.py tidak ditemukan!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("Report generation failed: zabbix_api.py not found")
                return
            df = fetch_zabbix_data()
            if df is None or df.empty:
                status_label.config(text="❌ Gagal mengambil data dari API!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("Report generation failed: No data from API")
                return
        else:
            if not files_var:
                status_label.config(text="❌ Silakan unggah file CSV!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("Report generation failed: No CSV files selected")
                return
            try:
                dfs = []
                for file in files_var:
                    logging.info(f"Reading CSV file: {file}")
                    df = pd.read_csv(file, encoding="utf-8")
                    df.columns = df.columns.str.strip()
                    required_columns = {'Host', 'Time', 'Status', 'Duration', 'Problem', 'Tags'}
                    if not required_columns.issubset(df.columns):
                        status_label.config(
                            text=f"Kolom berikut hilang di CSV: {required_columns - set(df.columns)}",
                            fg="red"
                        )
                        progress.stop()
                        progress.grid_forget()
                        logging.error(f"Missing columns in CSV {file}: {required_columns - set(df.columns)}")
                        return
                    dfs.append(df)
                df = pd.concat(dfs, ignore_index=True)
                logging.info(f"Combined {len(dfs)} CSV files into DataFrame with {len(df)} rows")
            except Exception as e:
                status_label.config(text=f"Gagal membaca file CSV: {str(e)}", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error(f"Failed to read CSV files: {str(e)}")
                return

        report, _ = analyze_data(df, shift_var.get(), operator_name)
        if report:
            report_text.insert(tk.END, report)
            status_label.config(text="✅ Laporan berhasil dibuat", fg="green")
            logging.info("Report generated successfully")
        else:
            status_label.config(text="⚠️ Tidak ada data yang memenuhi kriteria!", fg="orange")
            logging.warning("No data met report criteria")
        
        progress.stop()
        progress.grid_forget()

    def save_pdf():
        progress.grid(row=1, column=0, columnspan=3, pady=5)
        progress.start()
        
        logging.info(f"Exporting PDF with source: {data_source_var.get()}, shift: {shift_var.get()}")
        
        if data_source_var.get() == "API":
            if fetch_zabbix_data is None:
                status_label.config(text="❌ Modul zabbix_api.py tidak ditemukan!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("PDF export failed: zabbix_api.py not found")
                return
            df = fetch_zabbix_data()
            if df is None or df.empty:
                status_label.config(text="❌ Gagal mengambil data dari API!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("PDF export failed: No data from API")
                return
        else:
            if not files_var:
                status_label.config(text="❌ Silakan unggah file CSV!", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error("PDF export failed: No CSV files selected")
                return
            try:
                dfs = []
                for file in files_var:
                    logging.info(f"Reading CSV file for PDF: {file}")
                    df = pd.read_csv(file, encoding="utf-8")
                    df.columns = df.columns.str.strip()
                    required_columns = {'Host', 'Time', 'Status', 'Duration', 'Problem', 'Tags'}
                    if not required_columns.issubset(df.columns):
                        status_label.config(
                            text=f"Kolom berikut hilang di CSV: {required_columns - set(df.columns)}",
                            fg="red"
                        )
                        progress.stop()
                        progress.grid_forget()
                        logging.error(f"Missing columns in CSV {file}: {required_columns - set(df.columns)}")
                        return
                    dfs.append(df)
                df = pd.concat(dfs, ignore_index=True)
                logging.info(f"Combined {len(dfs)} CSV files for PDF with {len(df)} rows")
            except Exception as e:
                status_label.config(text=f"Gagal membaca file CSV: {str(e)}", fg="red")
                progress.stop()
                progress.grid_forget()
                logging.error(f"Failed to read CSV files for PDF: {str(e)}")
                return

        export_to_pdf(df, shift_var.get(), operator_name)
        progress.stop()
        progress.grid_forget()

    btn_generate = ttkb.Button(
        button_frame,
        text="📝 Generate Report",
        command=generate_report,
        bootstyle=SUCCESS
    )
    btn_generate.grid(row=0, column=0, padx=5)
    create_tooltip(btn_generate, "Buat laporan dari data")

    btn_export = ttkb.Button(
        button_frame,
        text="📄 Export to PDF",
        command=save_pdf,
        bootstyle=WARNING
    )
    btn_export.grid(row=0, column=1, padx=5)
    create_tooltip(btn_export, "Ekspor laporan ke PDF")

    btn_kembali = ttkb.Button(
        button_frame,
        text="🔙 Kembali",
        command=kembali_callback,
        bootstyle=SECONDARY
    )
    btn_kembali.grid(row=0, column=2, padx=5)
    create_tooltip(btn_kembali, "Kembali ke menu utama")

    status_label = create_styled_label(scrollable_frame, "")
    status_label.pack(pady=10)

if __name__ == "__main__":
    root = ttkb.Window(themename="litera")
    root.title("Zabbix Recap")
    root.geometry("1920x1080")
    frame = tk.Frame(root)
    frame.pack(expand=True, fill=tk.BOTH)
    setup_recap_frame(frame, "armin", lambda: print("Kembali"))
    logging.info("Application started")
    root.mainloop()