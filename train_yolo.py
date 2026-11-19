from pathlib import Path
from ultralytics import YOLO


# Menunjuk ke file konfigurasi dataset
DATA_YAML = Path(__file__).resolve().parent / "dataset_hanjeli" / "data.yaml"


def main():
    # Memuat model YOLO pralatih versi kecil
    model = YOLO("yolo26n.pt")

    # Melatihnya menggunakan dataset hanjeli kita
    model.train(
        data=str(DATA_YAML),
        epochs=50,
        imgsz=640,
        batch=4,
        workers=0,
        project="runs/hanjeli",
        name="deteksi_awal",
    )


if __name__ == "__main__":
    main()