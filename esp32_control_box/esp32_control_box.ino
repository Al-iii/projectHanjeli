/**
 * @file    esp32_control_box.ino
 * @brief   Firmware ESP32 untuk Control Box Smart Agriculture Hanjeli.
 *
 * Fungsi utama:
 *   - Membaca data dari sensor DHT22 (suhu), BH1750 (intensitas cahaya),
 *     dan sensor kapasitif tanah/analog (soil moisture) pada 3 titik.
 *   - Membungkus data ke format JSON.
 *   - Mem-publish data ke MQTT broker secara berkala setiap INTERVAL_PUBLISH ms.
 *
 * Dependensi Library (install via Arduino Library Manager):
 *   - PubSubClient  by Nick O'Leary      v2.8+  : Klien MQTT
 *   - ArduinoJson   by Benoit Blanchon   v6.x   : Serialisasi JSON
 *   - DHT sensor library by Adafruit     v1.4+  : Driver DHT22
 *   - BH1750        by Christopher Laws  v1.3+  : Driver sensor cahaya
 *
 * Board setting di Arduino IDE:
 *   Tools → Board → ESP32 Arduino → "ESP32 Dev Module"
 *   Tools → Upload Speed → 115200
 *
 * Wiring:
 *   DHT22       → DATA: GPIO 4  (3.3V & GND)
 *   BH1750      → SDA: GPIO 21, SCL: GPIO 22  (I2C default ESP32)
 *   Soil Pin 1  → GPIO 34  (input-only ADC1_CH6)
 *   Soil Pin 2  → GPIO 35  (input-only ADC1_CH7)
 *   Soil Pin 3  → GPIO 32  (ADC1_CH4)
 *
 * FIX LOG:
 *   [1] Ganti StaticJsonDocument (deprecated ArduinoJson v7) → JsonDocument
 *   [2] map() return long, bukan float → gunakan mapFloat() sendiri
 *   [3] LED_BUILTIN tidak selalu terdefinisi di semua board ESP32 → definisikan manual
 *   [4] publish() versi (topic, payload, length) pakai tipe byte* → cast (const uint8_t*)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <BH1750.h>
#include <Wire.h>

// ============================================================
// KONFIGURASI — Sesuaikan bagian ini sebelum di-upload
// ============================================================

// --- Jaringan WiFi ---
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";

// --- MQTT Broker ---
const char* MQTT_BROKER   = "broker.emqx.io";
const int   MQTT_PORT     = 1883;

// CLIENT_ID harus unik per perangkat — gunakan nama lokasi/serial
const char* MQTT_CLIENT_ID = "hanjeli-esp32-kebun-01";

// --- Topik MQTT ---
// Ganti "AABBCCDDEEFF" dengan MAC Address ESP32 Anda (tanpa tanda ':')
const char* TOPIK_SENSOR = "pertanian/sensor/AABBCCDDEEFF";
const char* TOPIK_STATUS = "pertanian/status/AABBCCDDEEFF";

// --- Identitas Perangkat (harus cocok dengan data di Django) ---
const char* MAC_ADDRESS = "AA:BB:CC:DD:EE:FF";   // ← format dengan ':'
const char* NAMA_BOX    = "Control Box Kebun 01";
const char* LOKASI_BOX  = "Kebun Blok A";

// --- Pin & Sensor ---
#define PIN_DHT22  4
#define TIPE_DHT   DHT22
#define PIN_SOIL_1 34
#define PIN_SOIL_2 35
#define PIN_SOIL_3 32

// FIX [3]: LED_BUILTIN tidak selalu terdefinisi di semua varian ESP32.
// ESP32 Dev Module: GPIO 2. Ganti sesuai board Anda jika berbeda.
#ifndef LED_BUILTIN
  #define LED_BUILTIN 2
#endif

// --- Interval Publish ---
// 30.000 ms = data dikirim setiap 30 detik
const unsigned long INTERVAL_PUBLISH = 30000;

// --- Kalibrasi ADC Soil Sensor ---
// Ukur nilai ADC ini langsung di lapangan:
//   ADC_KERING : tempelkan sensor di udara bebas
//   ADC_BASAH  : celupkan sensor ke dalam air bersih
const int ADC_KERING = 3000;
const int ADC_BASAH  = 1000;

// ============================================================
// INISIALISASI OBJEK GLOBAL
// ============================================================

DHT          sensor_dht(PIN_DHT22, TIPE_DHT);
BH1750       sensor_cahaya;
WiFiClient   wifi_client;
PubSubClient mqtt_client(wifi_client);

unsigned long waktu_publish_terakhir = 0;

// ============================================================
// FUNGSI HELPER
// ============================================================

/**
 * @brief Pemetaan linear nilai float dari satu rentang ke rentang lain.
 *
 * FIX [2]: Fungsi bawaan Arduino map() hanya mengembalikan tipe `long`
 * (integer), sehingga jika diassign ke float akan kehilangan presisi.
 * Fungsi ini menggantikannya dengan perhitungan floating-point penuh.
 *
 * @param nilai    Nilai input yang akan dipetakan.
 * @param dari_min Batas bawah rentang input.
 * @param dari_max Batas atas rentang input.
 * @param ke_min   Batas bawah rentang output.
 * @param ke_max   Batas atas rentang output.
 * @return float   Nilai yang sudah dipetakan ke rentang output.
 */
float mapFloat(float nilai, float dari_min, float dari_max, float ke_min, float ke_max) {
  return (nilai - dari_min) * (ke_max - ke_min) / (dari_max - dari_min) + ke_min;
}

/**
 * @brief Mengkonversi nilai ADC mentah sensor tanah menjadi persen kelembaban.
 *
 * Semakin rendah nilai ADC → semakin basah tanah (sensor kapasitif).
 * Hasil di-clamp ke rentang 0–100%.
 *
 * @param nilai_adc Nilai ADC mentah (0–4095 untuk ESP32 12-bit).
 * @return float    Persentase kelembaban (0.0 – 100.0).
 */
float konversiKelembabanPersen(int nilai_adc) {
  // Gunakan mapFloat() bukan map() agar hasil float presisi
  float persen = mapFloat((float)nilai_adc,
                          (float)ADC_KERING, (float)ADC_BASAH,
                          0.0f, 100.0f);
  // Clamp agar tidak keluar rentang valid
  if (persen < 0.0f)   persen = 0.0f;
  if (persen > 100.0f) persen = 100.0f;
  return persen;
}

/**
 * @brief Menghubungkan ESP32 ke jaringan WiFi.
 *
 * Blocking sampai berhasil. LED berkedip selama proses koneksi.
 */
void hubungkanWiFi() {
  Serial.print("[WiFi] Menghubungkan ke: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN)); // Kedipkan LED
  }

  digitalWrite(LED_BUILTIN, HIGH); // LED solid = WiFi terhubung
  Serial.println("\n[WiFi] Berhasil terhubung!");
  Serial.print("[WiFi] IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("[WiFi] MAC Address: ");
  Serial.println(WiFi.macAddress()); // Tampilkan MAC aktual untuk konfigurasi
}

/**
 * @brief Menghubungkan ESP32 ke MQTT broker dengan retry otomatis.
 *
 * Setelah connect berhasil, langsung publish pesan status ONLINE
 * dengan flag retain=true agar broker menyimpannya untuk subscriber baru.
 */
void hubungkanMQTT() {
  while (!mqtt_client.connected()) {
    Serial.print("[MQTT] Menghubungkan ke ");
    Serial.print(MQTT_BROKER);
    Serial.print("...");

    if (mqtt_client.connect(MQTT_CLIENT_ID)) {
      Serial.println(" Berhasil!");

      // FIX [1]: Gunakan JsonDocument (bukan StaticJsonDocument yang deprecated di ArduinoJson v7)
      JsonDocument doc_status;
      doc_status["mac_address"] = MAC_ADDRESS;
      doc_status["status"]      = "ONLINE";

      char buffer_status[128];
      serializeJson(doc_status, buffer_status);

      // publish(topic, payload, retain) — overload dengan retain flag
      mqtt_client.publish(TOPIK_STATUS, buffer_status, true);
      Serial.println("[MQTT] Status ONLINE dipublish (retained).");

    } else {
      Serial.print(" Gagal (kode: ");
      Serial.print(mqtt_client.state());
      Serial.println("). Coba lagi 5 detik...");
      delay(5000);
    }
  }
}

/**
 * @brief Membaca semua sensor lalu menyusun dan mem-publish payload JSON.
 *
 * Format JSON yang dipublish ke topik TOPIK_SENSOR:
 * {
 *   "mac_address"       : "AA:BB:CC:DD:EE:FF",
 *   "nama"              : "Control Box Kebun 01",
 *   "lokasi"            : "Kebun Blok A",
 *   "suhu"              : 28.5,
 *   "intensitas_cahaya" : 1234.5,
 *   "kelembaban_titik1" : 65.3,
 *   "kelembaban_titik2" : 70.1,
 *   "kelembaban_titik3" : 68.8
 * }
 */
void bacaDanPublishSensor() {
  // ---- Baca DHT22 (Suhu) ----
  float suhu = sensor_dht.readTemperature();
  if (isnan(suhu)) {
    Serial.println("[Sensor] WARNING: Gagal baca DHT22. Periksa wiring GPIO 4.");
    suhu = -99.0f; // Nilai sentinel = error baca
  }

  // ---- Baca BH1750 (Intensitas Cahaya) ----
  float intensitas_cahaya = sensor_cahaya.readLightLevel();
  if (intensitas_cahaya < 0) {
    Serial.println("[Sensor] WARNING: Gagal baca BH1750. Periksa koneksi I2C.");
    intensitas_cahaya = -1.0f;
  }

  // ---- Baca Soil Sensor 3 Titik (ADC → %) ----
  int   adc1 = analogRead(PIN_SOIL_1);
  int   adc2 = analogRead(PIN_SOIL_2);
  int   adc3 = analogRead(PIN_SOIL_3);
  float kelembaban1 = konversiKelembabanPersen(adc1);
  float kelembaban2 = konversiKelembabanPersen(adc2);
  float kelembaban3 = konversiKelembabanPersen(adc3);

  // Cetak ke Serial Monitor untuk debugging
  Serial.printf("[Sensor] Suhu: %.2f C | Cahaya: %.2f lux\n",
                suhu, intensitas_cahaya);
  Serial.printf("[Soil]   T1: %.1f%% (ADC:%d) | T2: %.1f%% (ADC:%d) | T3: %.1f%% (ADC:%d)\n",
                kelembaban1, adc1, kelembaban2, adc2, kelembaban3, adc3);

  // ---- Susun JSON ----
  // FIX [1]: JsonDocument (bukan StaticJsonDocument — deprecated di v7)
  JsonDocument doc;
  doc["mac_address"]        = MAC_ADDRESS;
  doc["nama"]               = NAMA_BOX;
  doc["lokasi"]             = LOKASI_BOX;
  doc["suhu"]               = serialized(String(suhu, 2));
  doc["intensitas_cahaya"]  = serialized(String(intensitas_cahaya, 2));
  doc["kelembaban_titik1"]  = serialized(String(kelembaban1, 1));
  doc["kelembaban_titik2"]  = serialized(String(kelembaban2, 1));
  doc["kelembaban_titik3"]  = serialized(String(kelembaban3, 1));

  char   buffer[300];
  size_t panjang = serializeJson(doc, buffer);

  // ---- Publish ke MQTT ----
  // FIX [4]: publish() dengan length butuh (topic, payload, length)
  //          payload harus bertipe const uint8_t* bukan char*
  bool berhasil = mqtt_client.publish(
    TOPIK_SENSOR,
    (const uint8_t*)buffer,
    panjang,
    false   // retain = false untuk data real-time
  );

  if (berhasil) {
    Serial.printf("[MQTT] Data dipublish ke: %s (%d bytes)\n", TOPIK_SENSOR, panjang);
  } else {
    Serial.println("[MQTT] ERROR: Gagal publish! Koneksi mungkin terputus.");
  }
}

// ============================================================
// SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1000); // Beri waktu Serial Monitor untuk siap

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println("\n===================================");
  Serial.println("  Hanjeli Smart Agriculture v1.1  ");
  Serial.println("===================================");

  // ---- Init I2C & BH1750 ----
  Wire.begin(); // SDA=21, SCL=22 (default ESP32)
  if (sensor_cahaya.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("[Init] BH1750 siap.");
  } else {
    Serial.println("[Init] ERROR: BH1750 tidak terdeteksi! Periksa kabel I2C.");
  }

  // ---- Init DHT22 ----
  sensor_dht.begin();
  Serial.println("[Init] DHT22 siap.");

  // ---- Hubungkan WiFi ----
  hubungkanWiFi();

  // ---- Setup MQTT (harus setelah WiFi terhubung) ----
  mqtt_client.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt_client.setBufferSize(512); // Perbesar buffer untuk payload JSON

  // ---- Publish data pertama segera setelah boot ----
  hubungkanMQTT();
  bacaDanPublishSensor();
  waktu_publish_terakhir = millis();

  Serial.println("[Init] Setup selesai. Worker loop dimulai.");
}

// ============================================================
// LOOP
// ============================================================

void loop() {
  // Pastikan koneksi MQTT selalu aktif
  if (!mqtt_client.connected()) {
    hubungkanMQTT();
  }
  mqtt_client.loop(); // Proses packet keepalive & pesan masuk

  // Publish data sensor secara periodik
  unsigned long sekarang = millis();
  if (sekarang - waktu_publish_terakhir >= INTERVAL_PUBLISH) {
    waktu_publish_terakhir = sekarang;
    bacaDanPublishSensor();
  }
}
