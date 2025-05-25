# Tugas-ETS-Pemrograman-Jaringan-C-50252221138

### Farrel Akmalazmi Nugraha
### 5025221138

---

## File Transfer Client-Server dengan Concurrency (ThreadPool & ProcessPool)
Repository ini berisi implementasi aplikasi client-server berbasis socket Python untuk transfer file besar (upload/download) dengan dukungan concurrency menggunakan:
- ThreadPoolExecutor (server_threadpool.py)
- ProcessPoolExecutor (server_processpool.py)
- Client concurrent menggunakan thread atau process pool (client_pool.py)

## Fitur Utama
- Transfer file besar (10MB, 50MB, 100MB) dengan protokol sederhana berbasis socket TCP.
- Encoding data menggunakan Base64 agar aman dikirim secara text.
- Server mampu menangani banyak client secara simultan menggunakan thread pool atau process pool.
- Client mendukung stress test dengan banyak worker (concurrency) menggunakan thread atau process pool.
- Monitoring sederhana pada server: jumlah operasi sukses/gagal dicetak secara berkala.
- Folder terpisah untuk file server dan file client (upload dan download).

## 🚀 Cara Menjalankan Program
### 🖥️ 1. Jalankan Server

Masuk ke **mesin1**, lalu jalankan:

#### a. Versi Thread Pool:
```bash
python3 server_threadpool.py [jumlah_worker]
```

#### b. Versi Process Pool:
```bash
python3 server_processpool.py [jumlah_worker]
```

Contoh:
```bash
python3 server_threadpool.py 5
```

### 🧪 2. Jalankan Client Stress Test

Masuk ke **mesin2**, lalu jalankan:

```bash
python3 client_pool.py [upload/download] [10MB|50MB|100MB] [jumlah_worker_client] [thread/process]
```

Contoh:
```bash
python3 client_pool.py upload 50MB 5 thread
python3 client_pool.py download 100MB 50 process
```

--- 

## 🧠 Penjelasan Logika Program

### 🧵 server_threadpool.py
- Menggunakan `ThreadPoolExecutor` untuk menangani koneksi client secara concurrent.
- Operasi:
  - `LIST`: mengembalikan daftar file.
  - `UPLOAD`: menerima file yang di-encode dengan Base64, disimpan di `server_files/`.
  - `DOWNLOAD`: mengirim file sebagai Base64 dengan penanda akhir `__END__`.

### 🧪 server_processpool.py
- Koneksi diterima di thread, lalu tiap perintah (upload/download/list) dikirim ke `ProcessPoolExecutor`.
- Upload menggunakan file `.b64` sementara.
- Proses pool memproses file, lalu hasil dikirim kembali.

### 💻 client_pool.py
- Mendukung upload dan download file menggunakan socket TCP.
- Melakukan stress test secara concurrent menggunakan:
  - `ThreadPoolExecutor`
  - `ProcessPoolExecutor`
- Mengukur:
  - Waktu rata-rata per client
  - Throughput (bytes/second)
  - Jumlah worker yang sukses/gagal
- Menampilkan progress dengan `tqdm`.


## 📊 Rencana Stress Test

| Dimensi          | Nilai                                 |
|------------------|----------------------------------------|
| Operasi          | Upload, Download                      |
| Ukuran File      | 10MB, 50MB, 100MB                     |
| Worker Client    | 1, 5, 50                              |
| Worker Server    | 1, 5, 50                              |
| **Total Kombinasi** | **2 × 3 × 3 × 3 = 54 uji**            |

Output stress test akan mencakup:
- Rata-rata waktu eksekusi per client
- Throughput (kecepatan transfer)
- Jumlah client/server yang sukses dan gagal

---

## 📂 Struktur Folder

```bash
📁 progjar-ets/
├── client_pool.py               # Client & stress tester
├── server_threadpool.py         # Server versi ThreadPool
├── server_processpool.py        # Server versi ProcessPool
├── client_files/                # File yang akan diupload (test_10mb.txt, dll)
├── client_downloads/            # Hasil file yang didownload
├── server_files/                # Tempat penyimpanan file di sisi server
```

---

### Penjelasan Lengkap Server dengan Thread Pool (server_threadpool.py)

Pada `server_threadpool.py`, server menggunakan konsep thread pool untuk menangani banyak koneksi client secara bersamaan. Server mendengarkan pada alamat `0.0.0.0` port `8989` dan menggunakan `buffer 16KB` untuk komunikasi data. Saat client terkoneksi, sebuah thread dari thread pool akan dipakai untuk melayani komunikasi tersebut, sehingga server dapat menangani puluhan hingga ratusan client secara paralel tanpa membuat thread baru untuk setiap client yang masuk.

Server menempatkan semua file di dalam folder `server_files`. Client dapat mengirim perintah seperti `LIS`, `UPLOAD <filename`>, dan `DOWNLOAD <filename>`. Perintah `LIST` akan mengirim daftar file yang tersedia pada folder `server_file`s ke client. Untuk `UPLOAD`, client mengirimkan data file dalam format base64 secara bertahap, server menerima data tersebut dan menulis hasil decode `base64` ke file. Sedangkan pada `DOWNLOAD`, server membaca file, mengubahnya ke format `base64`, dan mengirimkannya ke client dalam potongan data sampai selesai.

Server juga menjaga statistik jumlah operasi yang berhasil dan gagal untuk monitoring, yang diperbarui secara thread-safe menggunakan lock. Dengan model thread pool ini, server tetap responsif meskipun sedang memproses banyak permintaan file sekaligus, terutama yang melibatkan transfer file besar.


--- 


### Penjelasan Lengkap server_processpool.py (Server dengan Process Pool)

Pada `server_processpool.py`, server diatur untuk menangani banyak koneksi client secara simultan dengan menggunakan kombinasi threading dan process pool. Ketika server menerima koneksi, sebuah thread baru dibuat untuk mengelola komunikasi dengan client tersebut, tetapi proses berat seperti membaca dan menulis file besar dilakukan dalam process pool yang terpisah. Ini bertujuan untuk memanfaatkan multi-core CPU, sehingga operasi yang membutuhkan waktu lama (misalnya encoding/decoding Base64 file besar) tidak menghambat thread utama server.

Server mendengarkan di alamat 0.0.0.0 pada port 8989 dan menggunakan buffer sebesar 16KB untuk transfer data. Semua file disimpan dalam folder server_files. Setelah menerima perintah dari client, server mengirimkan tugas ke process pool untuk menjalankan operasi `LIST`, `UPLOAD`, dan `DOWNLOAD`. Pada operasi `UPLOAD`, server menerima data `base64` yang dikirim client, kemudian mendekode dan menyimpannya ke file. Pada operasi `DOWNLOAD`, server membaca file, melakukan encoding `base64` secara keseluruhan, lalu mengirim hasil encoding dalam potongan data ke client. Status keberhasilan dan kegagalan koneksi dilacak dengan variabel global yang diakses secara aman menggunakan lock.

Setiap 10 detik, server menampilkan statistik jumlah operasi yang berhasil dan gagal sebagai monitoring sederhana. Pendekatan ini cocok untuk server yang perlu menangani operasi IO dan CPU intensive sekaligus, sambil menjaga respon tetap cepat.

---

### Penjelasan Lengkap client_pool.py (Client dengan Thread/Process Pool)

Pada  `client_pool.py,` client bisa melakukan operasi upload atau download file secara bersamaan (concurrent) menggunakan thread pool atau process pool, sesuai pilihan user. Program ini menerima argumen dari command line untuk menentukan operasi (upload atau download), ukuran file (10MB, 50MB, atau 100MB), jumlah pekerja (workers), dan mode concurrency (thread atau process).

Untuk upload, client membuka file dari folder client_files, membaca dan mengirim potongan data yang sudah di-encode base64 ke server. Untuk download, client menerima data encoded base64 dari server, lalu mendekode dan menyimpannya di folder client_downloads. Selama transfer, progress bar interaktif dari library tqdm ditampilkan agar user dapat melihat progres upload/download.

Dengan concurrency, client dapat menjalankan banyak upload/download sekaligus yang berguna untuk stress test performa server dengan berbagai kombinasi jumlah workers dan mode concurrency.

