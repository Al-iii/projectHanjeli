from datetime import date, timedelta
from math import isfinite

from sklearn.linear_model import LinearRegression


class ModelPertumbuhan:
    def __init__(self):
        self.model = LinearRegression()
        self.tanggal_awal = None
        self.tanggal_terakhir = None

    def latih(self, pengamatan):
        """
        pengamatan: list pasangan (tanggal, tinggi_cm).
        Semua pengamatan harus berasal dari SATU bibit.
        Tanggal menggunakan format YYYY-MM-DD.
        """
        data = sorted(
            (date.fromisoformat(tanggal), float(tinggi))
            for tanggal, tinggi in pengamatan
        )

        # Batas awal aplikasi, bukan jaminan kecukupan data.
        if len({tanggal for tanggal, _ in data}) < 3:
            raise ValueError("Butuh minimal 3 tanggal pengamatan berbeda.")

        if len({tanggal for tanggal, _ in data}) != len(data):
            raise ValueError("Gunakan satu pengukuran per tanggal.")

        if any(not isfinite(tinggi) or tinggi <= 0 for _, tinggi in data):
            raise ValueError("Tinggi harus berupa angka positif.")

        tanggal_awal = data[0][0]

        # X = selisih hari sejak pengamatan pertama.
        # y = tinggi yang benar-benar diukur.
        X = [[(tanggal - tanggal_awal).days] for tanggal, _ in data]
        y = [tinggi for _, tinggi in data]

        self.model.fit(X, y)
        self.tanggal_awal = tanggal_awal
        self.tanggal_terakhir = data[-1][0]

        return self

    def prediksi(self, hari_ke_depan=3):
        if self.tanggal_awal is None:
            raise ValueError("Latih model terlebih dahulu.")

        if not isinstance(hari_ke_depan, int) or hari_ke_depan < 1:
            raise ValueError("Jumlah hari harus bilangan bulat positif.")

        tanggal_target = self.tanggal_terakhir + timedelta(
            days=hari_ke_depan
        )
        selisih_hari = (tanggal_target - self.tanggal_awal).days
        tinggi = float(self.model.predict([[selisih_hari]])[0])

        return {
            "tanggal_prediksi": tanggal_target.isoformat(),
            "tinggi_prediksi_cm": round(tinggi, 2),
            "tren_cm_per_hari": round(float(self.model.coef_[0]), 3),
        }