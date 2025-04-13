# Monitoring SAPP
![image](https://github.com/user-attachments/assets/603b6674-dbfc-416f-9a89-5a4a12d53a88)
![sapp feature](https://github.com/user-attachments/assets/870718ac-a8a6-4348-b9f2-f5051ef12d31)

**Monitoring SAPP** adalah aplikasi berbasis desktop menggunakan Tkinter yang memungkinkan operator untuk mengelola dan memonitor Zabbix, mengirim laporan email, mengelola memo, dan berinteraksi dengan asisten virtual berbasis RAG (Retrieval-Augmented Generation).

## Fitur Utama

1. **Login Operator**  
   Operator harus memasukkan nama mereka untuk masuk ke aplikasi.

2. **Recap Zabbix**  
   Membuat rekap monitoring Zabbix dari data yang diambil dari server Zabbix.

3. **Report Email**  
   Mengirim laporan via email berdasarkan template yang dapat dikustomisasi.

4. **Memo Manager**  
   Menyediakan fungsionalitas untuk menulis, melihat, dan menghapus memo. Memo disimpan sebagai file teks di direktori lokal.

5. **Asisten Virtual**  
   Asisten virtual berbasis Retrieval-Augmented Generation (RAG) yang dapat memberikan jawaban atas pertanyaan yang diajukan operator, dengan menggunakan PDF sebagai sumber data untuk meningkatkan kualitas jawaban.

---

## Langkah Instalasi

### Persyaratan

Pastikan Anda memiliki Python versi 3.11 atau lebih tinggi. Anda juga memerlukan beberapa pustaka Python untuk menjalankan aplikasi ini.

1. **Install Python Dependencies**

   Instal semua pustaka yang diperlukan menggunakan `pip`:

   ```bash
   pip install -r requirements.txt
2. **Setup Lingkungan**
   Pastikan Anda memiliki akses ke Zabbix server (untuk fitur recap Zabbix) dan konfigurasi server email yang benar untuk fitur email.

  - **Zabbix Recap**: Pastikan Zabbix server sudah terhubung dan dikonfigurasi dengan benar di file recap_zabbix.py.
  - **Email Report**: Siapkan pengaturan email di file report_email.py (seperti SMTP server, pengaturan login, dll).

3. **Menyiapkan Asisten Virtual (RAG)**

  - **PDF Sumber Data**: Letakkan file PDF yang ingin Anda gunakan untuk asisten virtual di dalam folder assistant/data/ dengan nama knowledge.pdf.
  - **Vectorstore**: Sistem menggunakan FAISS untuk menyimpan vektor dari PDF. Pada pertama kali aplikasi dijalankan, vectorstore akan dibuat dari file PDF yang ada.

4. **Memulai Aplikasi**
   Untuk memulai aplikasi, jalankan file app.py:

  ```bash
  python app.py
