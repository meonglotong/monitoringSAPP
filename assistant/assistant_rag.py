import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
import logging
import sys
sys.path.append("c:/ARMIN")
from ui_utils import get_theme, create_styled_label, create_tooltip

logging.basicConfig(level=logging.INFO)

DB_FAISS_PATH = "assistant/data/db_faiss"
PDF_PATH = "assistant/data/knowledge.pdf"

def load_pdf_and_create_vectorstore():
    if not os.path.exists(PDF_PATH):
        logging.error(f"PDF file not found: {PDF_PATH}")
        raise FileNotFoundError(f"PDF file not found: {PDF_PATH}")

    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load_and_split()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.from_documents(documents, embeddings)
    db.save_local(DB_FAISS_PATH)
    logging.info("Vektor berhasil disimpan.")
    return db

def load_vectorstore():
    if not os.path.exists(DB_FAISS_PATH):
        logging.error(f"FAISS database not found: {DB_FAISS_PATH}")
        raise FileNotFoundError(f"FAISS database not found: {DB_FAISS_PATH}")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)

def create_assistant():
    if not os.path.exists(DB_FAISS_PATH):
        logging.info("Membuat vectorstore baru dari PDF...")
        retriever = load_pdf_and_create_vectorstore().as_retriever()
    else:
        logging.info("Memuat vectorstore yang sudah ada...")
        retriever = load_vectorstore().as_retriever()

    llm = OllamaLLM(model="gemma:2b")

    prompt = PromptTemplate.from_template(""" 
Kamu adalah asisten AI yang cerdas dan menjawab dalam bahasa Indonesia.
Jawablah pertanyaan berdasarkan konteks berikut.
Jika konteks tidak membantu, tetap jawab sesuai pengetahuan umum.

Konteks:
{context}

Pertanyaan:
{question}

Jawaban:
""")

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt}
    )

    def tanya(pertanyaan: str) -> str:
        try:
            response = qa.invoke({"query": pertanyaan})
            jawaban = response if isinstance(response, str) else response.get("result", "")

            # Fallback jika jawaban tidak memadai
            fallback_cues = ["I cannot answer", "context does not", "tidak tersedia"]
            if any(cue.lower() in jawaban.lower() for cue in fallback_cues) or jawaban.strip() == "":
                jawaban = llm.invoke(pertanyaan)
            return jawaban
        except Exception as e:
            logging.error(f"Error saat memproses pertanyaan: {str(e)}")
            return f"Gagal memproses pertanyaan: {str(e)}"

    return tanya

def setup_assistant_frame(frame, operator_name, kembali_callback):
    for widget in frame.winfo_children():
        widget.destroy()

    # Inisialisasi asisten
    try:
        tanya = create_assistant()
    except Exception as e:
        logging.error(f"Gagal menginisialisasi asisten: {str(e)}")
        # Tampilkan pesan error dan kembali ke menu utama
        tk.messagebox.showerror("Error", f"Gagal menginisialisasi asisten: {str(e)}")
        kembali_callback()
        return

    main_container = tk.Frame(frame)
    main_container.pack(expand=True, fill="both")

    # Menggunakan ukuran kanvas yang lebih kecil agar terpusat
    canvas_frame = tk.Frame(main_container, width=800, height=650)
    canvas_frame.pack(side="top", padx=0, pady=20, expand=False)
    canvas_frame.pack_propagate(False)

    canvas = tk.Canvas(canvas_frame, width=800, height=650, bd=0, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttkb.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview, bootstyle=SECONDARY)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = tk.Frame(canvas)
    # Menempatkan scrollable_frame di tengah kanvas
    canvas_width = 800  # Sesuai dengan ukuran kanvas
    canvas.create_window((canvas_width // 2, 0), window=scrollable_frame, anchor="n")

    # Memperbarui scrollregion tanpa mengatur ulang posisi scrollable_frame
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    from ui_utils import create_styled_label, create_tooltip
    # Mengubah judul menjadi "Tanya Asisten"
    create_styled_label(scrollable_frame, "Tanya Asisten", 20).pack(pady=(20, 10), anchor="center")

    input_frame = ttkb.LabelFrame(scrollable_frame, text="Tanya Asisten", padding=15)
    input_frame.pack(pady=20, anchor="center")

    # Mengatur lebar minimum kolom 0 agar label memiliki lebar yang konsisten
    input_frame.columnconfigure(0, minsize=120)

    # Baris 1: Pertanyaan
    create_styled_label(input_frame, "Pertanyaan").grid(row=0, column=0, sticky="e", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=0, column=1, sticky="w", padx=(5, 15), pady=5)
    entry_pertanyaan = ttkb.Entry(input_frame, font=("Segoe UI", 11), width=50)
    entry_pertanyaan.grid(row=0, column=2, pady=5, sticky="w")

    # Baris 2: Jawaban
    create_styled_label(input_frame, "Jawaban").grid(row=1, column=0, sticky="e", padx=(10, 5), pady=5)
    create_styled_label(input_frame, ":").grid(row=1, column=1, sticky="w", padx=(5, 15), pady=5)
    text_jawaban = tk.Text(input_frame, height=10, width=50, font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=5, pady=5)
    text_jawaban.grid(row=1, column=2, pady=5, sticky="w")
    text_jawaban.config(state="disabled")  # Membuat readonly

    button_frame = tk.Frame(scrollable_frame)
    button_frame.pack(pady=20, anchor="center")

    progress = ttkb.Progressbar(button_frame, mode="indeterminate", bootstyle=INFO)

    def kirim_pertanyaan():
        pertanyaan = entry_pertanyaan.get().strip()
        if not pertanyaan:
            # Karena status label dihapus, gunakan messagebox untuk pesan error
            tk.messagebox.showerror("Error", "Pertanyaan tidak boleh kosong!")
            return

        progress.grid(row=1, column=0, columnspan=2, pady=5)
        progress.start()

        try:
            jawaban = tanya(pertanyaan)
            text_jawaban.config(state="normal")
            text_jawaban.delete("1.0", tk.END)
            text_jawaban.insert(tk.END, jawaban)
            text_jawaban.config(state="disabled")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Gagal memproses pertanyaan: {str(e)}")
            logging.error(f"Error saat memproses pertanyaan: {str(e)}")
        finally:
            progress.stop()
            progress.grid_forget()

    btn_kirim = ttkb.Button(button_frame, text="Kirim", command=kirim_pertanyaan, bootstyle=SUCCESS)
    btn_kirim.grid(row=0, column=0, padx=5)
    create_tooltip(btn_kirim, "Kirim pertanyaan ke asisten")

    btn_kembali = ttkb.Button(button_frame, text="Kembali", command=kembali_callback, bootstyle=SECONDARY)
    btn_kembali.grid(row=0, column=1, padx=5)
    create_tooltip(btn_kembali, "Kembali ke menu utama")

if __name__ == "__main__":
    from ui_utils import get_theme
    root = ttkb.Window(themename=get_theme())
    root.geometry("1920x1080")  # Menyesuaikan dengan ukuran window di app.py
    root.title("AI Assistant")
    frame = tk.Frame(root)
    frame.pack(expand=True, fill=tk.BOTH)
    setup_assistant_frame(frame, "Test Operator", lambda: print("Kembali"))
    root.mainloop()