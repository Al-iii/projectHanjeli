# Pilihan model penyakit daun jagung: YOLO11 wjxn13

## Status dan sumber

Bobot resmi berhasil diunduh, dimuat, dan menjalankan inferensi CPU nyata pada
25 November 2026. Model ini ditambahkan pada halaman penyakit daun yang sama:
http://127.0.0.1:8000/prediktor/jagung/ . Pilih **YOLO11 — wjxn13**.
Model lama HassanCodesIt tetap menjadi pilihan default untuk kompatibilitas.
Kornrows, modul pertumbuhan, serta data Pot/Bibit/Pengamatan tidak diubah.

- Repo: https://github.com/wjxn13/corn-leaf-disease-detector, branch `main`.
- Commit: `a662066aa41977c0eb1efd1b278a49a87c300fbe`.
- URL biner: https://media.githubusercontent.com/media/wjxn13/corn-leaf-disease-detector/a662066aa41977c0eb1efd1b278a49a87c300fbe/best.pt
- Lokasi: `weights/corn_leaf_yolo11/best.pt` (tidak menimpa bobot lama).
- Ukuran: **19.175.123 byte**.
- SHA-256: `c60b9bf7c9e85270fbc4656adc976f07a2cb082607366f373717003d42c47686`.
- `.gitattributes` menggunakan Git LFS. File raw GitHub adalah pointer; file
  media.githubusercontent.com yang dipasang merupakan biner, dengan ukuran/hash
  cocok terhadap pointer resmi. Metadata disimpan di `weights/corn_leaf_yolo11/SOURCE.json`.
- LICENSE upstream adalah MIT, copyright 2026 wjxn13; salinan disimpan di
  `weights/corn_leaf_yolo11/LICENSE`. README menyatakan bobot juga dirilis MIT.
  Dataset dan dependensi tetap memiliki lisensinya masing-masing.

README, LICENSE, .gitattributes, local_predict.py dan app.py telah diperiksa.
Kedua skrip menggunakan `ultralytics.YOLO('best.pt')` dengan confidence 0.5.
Skrip desktop mengecilkan sisi terpanjang ke 1024 sebelum inferensi. Integrasi
ini mempertahankan resolusi asli tervalidasi dan memakai preprocessing YOLO
`imgsz=640`, sehingga anotasi/koordinat sesuai gambar asli yang dinormalisasi.
Tidak menyalin aplikasi desktop atau FastAPI upstream ke Django.

## Task dan kelas aktual dari bobot

`model.task == 'detect'`. Label berikut berasal dari `model.names`, bukan asumsi
urutan pada README; tidak ada terjemahan tampilan tambahan.

| ID | Label |
| --- | --- |
| 0 | Corn__CommonRust |
| 1 | Corn__GrayLeafSpot |
| 2 | Corn__Healthy |
| 3 | Corn__NorthernLeafBlight |

Foto yang sesuai adalah foto dekat satu daun jagung dengan latar sederhana.
Foto tanaman utuh dari atas/lingkungan kompleks dapat menyebabkan salah deteksi.
Confidence bukan persentase akurasi. Label Healthy tetap prediksi model;
hasil tanpa kotak tidak menyatakan daun sehat. Tidak ada estimasi tinggi,
kebutuhan penyiraman, ataupun dosis pengobatan.

## Dependensi dan menjalankan

Venv proyek sudah kompatibel; **tidak ada paket yang diubah**. Versi pengujian:
Ultralytics 8.4.202, Torch 2.15.0+cpu, Pillow 13.0.0, Django 5.2.19.
`requirements-corn.txt` yang sudah ada mencatat Ultralytics. Tidak perlu
menginstal FastAPI/Tkinter dari aplikasi sumber maupun runtime Kornrows.

```powershell
# Hanya saat bobot belum tersedia, misalnya setelah clone:
.\venv\Scripts\python.exe scripts\download_corn_yolo11_weights.py
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py runserver
```

Downloader mematok commit, menolak pointer, serta memeriksa ukuran dan SHA-256
sebelum menulis file. Tidak ada unduhan bobot otomatis pada request pengguna.
Bobot hilang/gagal dimuat tidak memicu penggantian ke model lain.

| Model | Path | Confidence | Device |
| --- | --- | --- | --- |
| Model lama | CORN_YOLO_WEIGHTS | CORN_YOLO_CONFIDENCE (0.25) | CORN_YOLO_DEVICE (cpu) |
| YOLO11 | CORN_YOLO11_WEIGHTS | CORN_YOLO11_CONFIDENCE (0.5) | CORN_YOLO11_DEVICE (cpu) |

Path relatif berbasis BASE_DIR; path absolut juga didukung. Model dimuat lazy,
cache terpisah per ID/path/mtime/ukuran, dengan lock untuk model bersama.
GPU hanya jika Torch dan perangkat kompatibel; environment yang diuji CPU-only.
Restart server setelah mengubah environment variables atau bobot.

## Hasil dan catatan riwayat

Form validasi gambar yang sama tetap dipakai: JPEG/PNG/WebP, maksimal 10 MB,
6000 piksel per sisi, 20 megapiksel, verifikasi/decode penuh, koreksi EXIF,
penolakan animasi dan isi bukan gambar, CSRF, serta nama UUID.

Setiap unggahan berhasil menyimpan tiga file:

- `media/corn/<UUID>/` untuk model lama.
- `media/corn_leaf_yolo11/<UUID>/` untuk YOLO11.
- Dalam setiap folder: `original.jpg`, `annotated.jpg`, `result.json`.

JSON merupakan **catatan riwayat berbasis berkas**, bukan model database atau
halaman daftar riwayat. Isinya waktu, ID/nama model, sumber/commit, SHA-256 bobot
yang dimuat, task/names aktual, threshold/device, path gambar, dan deteksi
terstruktur. Tautan JSON tersedia pada hasil. Tidak ada migrasi atau perubahan
Pengamatan hanjeli. Jika menggunakan checkpoint khusus lewat environment,
metadata source_commit tetap menunjuk sumber integrasi; SHA-256 aktual adalah
identitas file yang digunakan, bukan klaim checkpoint khusus berasal dari commit itu.

Gambar asli dinormalisasi ke RGB JPEG tanpa metadata. File disimpan sampai
dibersihkan manual; refresh POST melakukan inferensi baru. Jika ada kegagalan
penyimpanan, file yang sudah dibuat pada request itu dibersihkan.

## Bukti inferensi nyata

Foto yang sudah tersedia lokal: `weights/corn/samples/corn-rust.jpg`, sumber:
https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/raw/color/Corn_(maize)___Common_rust_/RS_Rust%201563.JPG
Dataset PlantVillage, Mohanty/Hughes/Salathe (2016), DOI 10.3389/fpls.2016.01419.
Tidak mengunduh dataset Kaggle karena foto dekat daun sudah tersedia.

YOLO11, CPU, confidence 0.5, ukuran inferensi 640:

- **1 kotak**, ID 0, `Corn__CommonRust`, confidence **0.8825692534 (88,26%)**.
- Kotak xyxy pada gambar 256x256: sekitar `[7.31, 0.37, 239.13, 255.82]`.
- Anotasi tahap awal: `media/corn_leaf_yolo11/verification/annotated.jpg`.
- Detail: `media/corn_leaf_yolo11/verification/result.json`.
- Unggahan nyata melalui Django test client: HTTP 200; anotasi
  `media/corn_leaf_yolo11/b8023dc7ec444746a396c4366b679df3/annotated.jpg`,
  dengan `result.json` beridentitas model di folder yang sama.
- Model lama juga diuji melalui POST nyata, HTTP 200, 0 kotak pada confidence
  0.25. Kedua hasil tetap terpisah; tidak ada fallback atau hasil buatan.

Anotasi YOLO11 telah diperiksa visual. Hasil satu foto **bukan ukuran akurasi**,
belum ada evaluasi dataset independen atau uji GPU.
Unggahan melalui browser lokal (form dan CSRF nyata) juga berhasil: pilihan
YOLO11 tetap terlihat, satu deteksi 88,26%, gambar asli/anotasi termuat, dan
tautan JSON tersedia. Hasil browser berada di
`media/corn_leaf_yolo11/6e607c7c8c92405e9ee8af76bc23117a/`.

## Pengujian dan berkas perubahan

`manage.py check`: bersih. `manage.py test`: **41 tes lulus**.
`makemigrations --check --dry-run`: tidak ada perubahan.
Tes mencakup pemilihan/penolakan ID model, unggahan invalid, CSRF, orientasi,
ukuran/dimensi, bobot hilang, pointer LFS, task salah, error inferensi, cache
terpisah, identitas JSON, file unik, hasil kosong, dan cleanup kegagalan simpan.
Tes unit memakai mock loader/hasil untuk cabang tertentu; bukti inferensi nyata
adalah percobaan yang diuraikan terpisah di atas.

Diubah: `.gitignore`, `hanjeli/settings.py`, `prediktor/corn_inference.py`,
`prediktor/forms.py`, `prediktor/views.py`, `prediktor/tests.py`,
`prediktor/templates/prediktor/jagung.html`, dan `README-corn.md`.
Baru: `prediktor/test_leaf_models.py`, `scripts/download_corn_yolo11_weights.py`,
`weights/corn_leaf_yolo11/SOURCE.json`, salinan LICENSE, dan dokumen ini.
Perubahan Kornrows yang sebelumnya belum di-commit tetap dipertahankan.
