from prediktor.ml_pertumbuhan import ModelPertumbuhan

# DATA CONTOH BUATAN, ganti dengan pengukuran asli satu bibit.
pengamatan = [
    ("2026-11-01", 10),
    ("2026-11-04", 13),
    ("2026-11-07", 16),
    ("2026-11-10", 19),
]

model = ModelPertumbuhan()
model.latih(pengamatan)

hasil = model.prediksi(hari_ke_depan=3)

print("Tanggal prediksi:", hasil["tanggal_prediksi"])
print("Perkiraan tinggi:", hasil["tinggi_prediksi_cm"], "cm")
print("Tren pertumbuhan:", hasil["tren_cm_per_hari"], "cm/hari")