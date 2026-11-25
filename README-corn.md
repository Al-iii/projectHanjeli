# Deteksi daun jagung

Pembaruan 25 November 2026: halaman kini memiliki pilihan model lama dan YOLO11
wjxn13. Catatan `result.json` menyimpan identitas model dan hasil tiap unggahan.
Lihat [README-corn-yolo11.md](README-corn-yolo11.md) untuk konfigurasi baru dan
bukti inferensi nyata. Catatan verifikasi di bawah adalah pengujian awal model lama.

Halaman: http://127.0.0.1:8000/prediktor/jagung/ . Navigasi tersedia pada dashboard,
sidebar administrasi, dan halaman unggah hanjeli. Hasil hanya prediksi model untuk
foto daun jagung, bukan diagnosis pasti atau model hanjeli. Tidak ada pelatihan ulang.

## Menjalankan (PowerShell dari root proyek)

Venv yang ada sudah memiliki semua dependensi; tidak perlu memasang ulang.

```powershell
# Hanya jika bobot belum tersedia (misalnya setelah clone):
.\venv\Scripts\python.exe scripts\download_corn_weights.py
# Hanya jika Ultralytics belum tersedia:
.\venv\Scripts\python.exe -m pip install -r requirements-corn.txt
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test prediktor
.\venv\Scripts\python.exe manage.py runserver
```

Tidak ada migrasi baru. requirements.txt lama tidak diubah: beberapa versinya tidak
sama dengan venv, sehingga jangan menggunakannya untuk memperbarui semua paket.
Versi pengujian: Django 5.2.19, Pillow 13.0.0, Ultralytics 8.4.202,
PyTorch 2.15.0+cpu. Inferensi membutuhkan dependensi transitif Ultralytics
(termasuk Torch, NumPy, OpenCV); FastAPI/Roboflow dari proyek sumber tidak diperlukan.

## Bobot dan asal model

- Repositori: https://github.com/HassanCodesIt/corn-leaf-disease-detection
- Commit yang diperiksa: `fe0ef7bce7dbb2890b3374836e9970c841b17219`.
- Berkas: `weights/corn/corn_Leaf_model.pt`, 18.476.182 byte, bobot biner nyata,
  bukan pointer Git LFS; pemuatan dan inferensi berhasil.
- SHA-256: `bdab3208322293a16fd80610d3cff160983e9bb6b4e0c04eb0a0f9ba57c18b8c`.
- URL unduhan dipatok ke commit di `scripts/download_corn_weights.py`; hash
  diperiksa sebelum penulisan berkas.
- README sumber menyatakan MIT, tetapi tidak ada berkas LICENSE terpisah pada
  tree commit tersebut. Pernyataan README itu tidak memverifikasi hak dataset
  atau memberi lisensi ulang dependensi Ultralytics.
- Sumber menyebut YOLOv8n. Pemeriksaan bobot menghasilkan `task='detect'` dengan
  tepat **7** label berikut (penomoran/lista naratif README tidak konsisten):

| ID | model.names |
| --- | --- |
| 0 | brown_spot |
| 1 | corn_rust |
| 2 | corn_smut |
| 3 | downy_mildew |
| 4 | grey_leaf_spot |
| 5 | healthy |
| 6 | leaf_blight |

Label ditampilkan tanpa terjemahan. Nilai confidence tidak dikalibrasi sebagai
peluang diagnosis yang benar. Jumlah deteksi adalah jumlah kotak, bukan tanaman.

## Konfigurasi dan penyimpanan

Environment variables dibaca di `hanjeli/settings.py`:

| Variabel | Default |
| --- | --- |
| CORN_YOLO_WEIGHTS | weights/corn/corn_Leaf_model.pt, relatif terhadap BASE_DIR |
| CORN_YOLO_CONFIDENCE | 0.25, nilai awal percobaan |
| CORN_YOLO_DEVICE | cpu |

Path absolut juga diterima. CPU merupakan default yang telah diuji. Untuk GPU,
gunakan `CORN_YOLO_DEVICE=0` hanya setelah memastikan Torch CUDA dan perangkat
kompatibel; environment ini CPU-only, GPU belum diuji. Konfigurasi device salah
menghasilkan pesan gagal dan traceback pada log server. Restart server setelah
mengubah konfigurasi atau mengganti bobot pada path yang sama.

Model dimuat lazy dan digunakan ulang per proses. Lock melindungi pemuatan dan
prediksi terhadap request bersamaan. Bobot hilang tidak memicu unduhan model umum.
Layanan berada di `prediktor/corn_inference.py`, terpisah dari views dan regresi.

Form memeriksa isi JPEG/PNG/WebP, ukuran maksimal 10 MB, 6000 piksel per sisi,
20 juta piksel, decode penuh, serta menolak animasi/gambar rusak. Nama dan ekstensi
unggahan tidak digunakan. Gambar asli untuk tampilan dinormalisasi orientasinya
dan dienkode ulang ke RGB JPEG tanpa metadata, bukan salinan byte-for-byte.
Gambar ini dan anotasi disimpan di `media/corn/<UUID>/original.jpg` dan
`annotated.jpg`. Hasil terstruktur kini disimpan bersama identitas model dalam
`result.json`; tidak ada riwayat database, dan tidak menulis Pot, Bibit, atau Pengamatan.
Berkas tetap tersimpan sampai dibersihkan manual; refresh POST menjalankan ulang
deteksi. Folder media tersebut dan bobot diabaikan Git secara spesifik.

## Verifikasi dan batasan (24 November 2026)

- `manage.py check`: tidak ada masalah.
- `manage.py test`: seluruh 14 tes lulus (13 tes fitur jagung, 1 tes proyek
  yang sudah ada). `makemigrations --check --dry-run`: tidak ada perubahan.
  `git diff --check`: bersih.
- Pengujian form/view mencakup gambar valid, nama ekstensi palsu, orientasi EXIF,
  isi palsu/rusak, format, ukuran/dimensi/piksel, CSRF, file unik, label/confidence,
  hasil kosong, bobot hilang, log error, dan pembersihan setelah penyimpanan gagal.
  Pengujian view memakai mock inferensi untuk mengisolasi cabang hasil/error.
- Inferensi CPU nyata dijalankan pada foto jagung PlantVillage yang repositorinya
  menyatakan open access: [RS_Rust 1563.JPG](https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/raw/color/Corn_%28maize%29___Common_rust_/RS_Rust%201563.JPG).
  Referensi dataset: https://github.com/spMohanty/PlantVillage-Dataset,
  Mohanty, Hughes, Salathe (2016), DOI 10.3389/fpls.2016.01419.
  Salinan lokal: `weights/corn/samples/corn-rust.jpg`; anotasi:
  `weights/corn/samples/annotated.jpg` (keduanya tidak masuk Git).
- Pada confidence 0.25 foto tersebut menghasilkan **0 deteksi**. Unggahan nyata
  melalui Django test client memberi HTTP 200 serta gambar hasil dan pesan kosong.
- Gambar putih sintetis 640x640 justru menghasilkan satu deteksi `healthy`
  dengan confidence sekitar **77.96%**. Ini false positive pada input non-daun;
  model tidak boleh dianggap memvalidasi keberadaan daun atau kesehatan tanaman.
- Percobaan ini memverifikasi jalur inferensi, **bukan mengukur akurasi**. Belum
  ada evaluasi dataset terpisah, uji GPU, atau uji beban/concurrency end-to-end.
- Pemeriksaan browser visual tidak dapat dijalankan: tool browser gagal sebelum
  tersambung karena metadata sandbox (`missing field sandboxPolicy`). HTML,
  URL, CSRF, serta hasil unggahan diperiksa lewat Django test client. Tata letak
  memakai grid responsif Bootstrap yang sama dengan dashboard administrasi.

Inferensi ulang pada contoh lokal:

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from PIL import Image; from prediktor.corn_inference import detect; a,d=detect(Image.open('weights/corn/samples/corn-rust.jpg').convert('RGB')); print(d)"
```
