# Deteksi Tanaman Jagung — Kornrows

## Status (25 November 2026)

**Checkpoint jagung belum ditemukan. Inferensi tanaman nyata belum berfungsi.**
Halaman `/prediktor/tanaman-jagung/` menampilkan **Model jagung belum tersedia**.
Halaman penyakit daun `/prediktor/jagung/` tetap memakai modelnya sendiri.
Tidak ada penggantian ke COCO, model penyakit daun, training, atau prediksi palsu.

## Audit sumber dan bobot

Sumber: https://github.com/andre-kotze/kornrows, branch `master`, commit
`b0c4c857233e3bf76d56df81b83d16fabb3929f2`. Salinan lokal di `vendor/kornrows/`
(diabaikan Git), dipersiapkan satu kali, tidak diunduh saat request.
Lisensi sumber: GNU GPL v3 pada berkas `LICENSE` (tetap ada dalam checkout).

Yang diperiksa: README.md, korn.yaml, detect.py, hubconf.py, find_kornrows.py,
main.py, requirements.txt, LICENSE, .gitattributes, skrip download_weights.sh,
utils/downloads.py, notes.ipynb, serta contoh korn.jpg.

Hasil pencarian:

- Tree commit tidak memiliki checkpoint `.pt`, `.onnx`, atau `.weights`.
- `git log --all --format= --name-only -- '*.pt' '*.onnx' '*.weights'` pada
  riwayat master yang di-clone tidak menemukan berkas bobot.
- API `https://api.github.com/repos/andre-kotze/kornrows/releases` mengembalikan
  daftar kosong. `git lfs ls-files` kosong dan `.gitattributes` tidak memuat
  aturan LFS; tidak ditemukan pointer bobot untuk diunduh.
- README menyebut `cornmodem864i12002`, `kornmodel960m`, dan
  `kornmodel960l_1200`, tetapi tidak memberikan berkas atau URL checkpoint.
- Skrip unduh bawaan menunjuk model YOLOv5 umum dari Ultralytics, bukan
  checkpoint jagung. Model tersebut tidak dipakai.
- Tautan README dan situs resmi pembuat yang tercantum di profil GitHub,
  https://andregis.com, tidak menyediakan tautan bobot Kornrows yang ditemukan
  dalam pemeriksaan ini. Pencarian web nama checkpoint juga tidak menemukannya.

Yang diperlukan: **berkas PyTorch terlatih `best.pt` atau `last.pt` dari salah
satu run jagung di atas**, atau tautan unduhan resmi pembuat beserta informasi
run/kelas dan versi runtime. `best.pt` adalah nama tujuan lokal yang dipilih
integrasi ini, bukan klaim bahwa file bernama itu diterbitkan pembuat.
Simpan di `weights/kornrows/best.pt`, atau atur `KORNROWS_WEIGHTS`.
**SHA-256 bobot belum dapat dicatat karena file belum tersedia.** Setelah mendapat
file resmi, catat URL, identitas run, dan hasil `Get-FileHash ... -Algorithm SHA256`.
Gunakan checkpoint dari sumber yang dipercaya: format `.pt` legacy memuat objek
Python melalui pickle. Upload pengguna hanya menerima gambar, bukan checkpoint.

## Makna kelas dan batas kemampuan

`korn.yaml` menetapkan `nc: 1`, `names: ["cc"]`. README menyebut detektor pusat
tanaman jagung. Nama asli **cc** dipertahankan; repo tidak menjelaskan kepanjangan
singkatan secara eksplisit. `detect.py` menghasilkan kotak dan confidence,
sedangkan `find_kornrows.get_centroids()` membaca pusat kotak format YOLO.
Integrasi menghitung pusat `(x1+x2)/2, (y1+y2)/2`; ini bukan model keypoint.

Koordinat ditampilkan dalam **piksel**, asal kiri atas gambar setelah normalisasi
orientasi. Kode analisis barisan upstream membalik sumbu Y untuk grafik; konvensi
grafik itu tidak diterapkan pada overlay foto di sini. Tidak ada konversi ke cm,
analisis barisan, tinggi, pertumbuhan, atau rekomendasi penyiraman.

Kode analisis menyebut citra DJI dan altitude XMP, sehingga foto lapangan dari
atas dengan pusat tanaman terpisah adalah jenis input yang disarankan berdasarkan
alur kode, bukan hasil uji model. `korn.jpg` telah diperiksa: foto seseorang di
antara jagung dari samping, **bukan contoh beranotasi yang memvalidasi deteksi
pusat dari atas**. Contoh bus/zidane merupakan bawaan YOLOv5. Foto validasi jagung
berlabel yang sesuai belum tersedia dalam repo.

## Runtime terpisah

Venv Django tidak diubah. Gunakan Python 3.12 untuk `.venv-kornrows` dengan versi
di `requirements-kornrows.txt`. Torch 2.5.1 dipilih untuk loader objek checkpoint
legacy (`models.experimental.attempt_load`); jangan memakai `ultralytics.YOLO`
atau menaikkan Torch tanpa menguji checkpoint. Kompatibilitas dengan **checkpoint
jagung tertentu** baru dapat diverifikasi setelah bobot diterima.

PowerShell dari root proyek, untuk setup ulang setelah clone:

```powershell
.\venv\Scripts\python.exe scripts\setup_kornrows_source.py
py -3.12 -m venv .venv-kornrows
.\.venv-kornrows\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv-kornrows\Scripts\python.exe -m pip install -r requirements-kornrows.txt
# Setelah menerima bobot resmi:
New-Item -ItemType Directory -Force weights\kornrows
# Salin checkpoint resmi ke weights\kornrows\best.pt
Get-FileHash weights\kornrows\best.pt -Algorithm SHA256
```

Adapter menjalankan `scripts/kornrows_runner.py` dengan `subprocess.run`, daftar
argumen, `shell=False`, input JSON di stdin, output JSON pada direktori sementara,
capture stderr, serta timeout. `cwd` hanya untuk anak proses; Django tidak
memanggil `os.chdir()` atau mengimpor `models`/`utils` upstream. Model dimuat
sekali per proses inferensi/request; belum ada layanan persisten untuk caching.
Repo/bobot tidak diunduh ulang. Fallback downloader upstream dinonaktifkan pada
loader, dan kelas selain `cc`/head selain deteksi satu kelas ditolak.
Import upstream juga mencoba mengunduh font Arial pada rank default. Adapter
menetapkan `RANK=1` hanya pada proses inferensi untuk melewati unduhan tersebut;
tidak menjalankan training/distributed. Overlay dibuat oleh Pillow di Django,
sehingga font dan Annotator upstream tidak diperlukan.

Preprocessing mengikuti deteksi YOLOv5: RGB, letterbox, CHW float 0–1, NMS,
dan rescale kotak ke gambar asli. Output `class_id`, `xyxy`, confidence diperiksa
kembali di Django sebelum anotasi. Runner juga menghasilkan hash bobot dalam
output JSON. Nama kelas saja bukan bukti provenance bobot; sumber resmi tetap
harus diverifikasi saat memasang checkpoint.

| Environment variable | Default |
| --- | --- |
| KORNROWS_REPO | vendor/kornrows |
| KORNROWS_WEIGHTS | weights/kornrows/best.pt |
| KORNROWS_PYTHON | .venv-kornrows/Scripts/python.exe |
| KORNROWS_DEVICE | cpu |
| KORNROWS_CONFIDENCE | 0.25 (percobaan, bukan jaminan akurasi) |
| KORNROWS_IMAGE_SIZE | 960 (32–2048; disesuaikan stride oleh runtime) |
| KORNROWS_TIMEOUT | 120 detik |

Path relatif dihitung dari `settings.BASE_DIR`; path absolut juga diterima.
GPU opsional memerlukan build Torch CUDA dan GPU yang kompatibel, lalu set
`KORNROWS_DEVICE=0`. Runtime yang dipasang adalah CPU; GPU belum diuji.
Restart Django setelah mengganti environment variables.

## Menjalankan halaman

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py runserver
```

Buka http://127.0.0.1:8000/prediktor/tanaman-jagung/ . Tidak perlu migrasi.
Halaman tetap bisa dibuka dan unggahan divalidasi meskipun model belum tersedia;
tidak ada hasil deteksi atau berkas media yang dibuat dalam kondisi itu.

Gambar JPEG/PNG/WebP diverifikasi berdasarkan isi, maksimal 10 MB, 6000 piksel
per sisi, dan 20 megapiksel. Animasi dan gambar rusak ditolak. Orientasi EXIF
dinormalisasi. Gambar asli untuk tampilan dienkode ulang RGB JPEG tanpa metadata
(bukan salinan byte identik). Hasil berhasil disimpan di
`media/kornrows/<UUID>/original.jpg` dan `annotated.jpg`. Tidak ada riwayat database
atau perubahan Pot/Bibit/Pengamatan; berkas media tetap ada sampai dibersihkan
manual. Berkas sebagian dibersihkan bila penyimpanan gagal.

## Verifikasi

- `manage.py check`: lulus; `makemigrations --check --dry-run`: tidak ada perubahan.
- `manage.py test`: 34 tes lulus, termasuk 11 tes Kornrows.
- Runtime Python 3.12 terpisah sudah dipasang lokal. Impor `attempt_load`, head
  `Detect`, letterbox, NMS, rescale, dan pemilihan CPU berhasil dengan Torch
  2.5.1+cpu / torchvision 0.20.1+cpu / NumPy 1.26.4. Uji impor memblokir koneksi
  socket untuk memastikan tidak bergantung pada unduhan; ini bukan inferensi.
  `pip check` runtime: tidak ada dependensi rusak.
- Halaman dibuka di browser lokal: navigasi, formulir, dan status model belum
  tersedia tampil dengan gaya dashboard. Tampilan hasil diuji lewat mock/test
  client; belum ada hasil nyata untuk pemeriksaan visual anotasi model.
- Jalur **nyata tanpa bobot** diuji: GET/POST menampilkan model belum tersedia,
  subprocess tidak dijalankan dan media tidak disimpan.
- Mock: deteksi berhasil/kosong, label/confidence/pusat, nama file unik, error
  inferensi, timeout, exit nonzero, penolakan kelas lain, cleanup file sebagian,
  dan protokol JSON. Mock tidak membuktikan pemuatan bobot atau akurasi.
- Unggahan invalid, field kosong, ukuran/dimensi/piksel, orientasi, CSRF, pointer
  Git LFS, serta kelangsungan halaman penyakit daun diuji.
- Tidak ada inferensi nyata jagung, evaluasi akurasi, maupun uji GPU karena
  checkpoint belum tersedia. Tidak ada klaim jumlah tanaman sebenarnya.

## Berkas integrasi

Baru: `prediktor/kornrows_inference.py`, `prediktor/test_kornrows.py`,
`prediktor/templates/prediktor/kornrows.html`, `scripts/kornrows_runner.py`,
`scripts/setup_kornrows_source.py`, `requirements-kornrows.txt`, dokumen ini.
Diubah: `.gitignore`, `hanjeli/settings.py`, `prediktor/forms.py`, `views.py`,
`urls.py`, template beranda, sidebar `admin/templates/base.html`, serta dashboard.
Checkout sumber dan venv inference adalah artefak lokal yang diabaikan Git.
