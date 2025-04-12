import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
import logging

# Setup logging
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

    # Gunakan LLM dari Ollama
    llm = OllamaLLM(model="gemma:2b")

    # Prompt bilingual
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

    # Retrieval + Prompt Custom
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
