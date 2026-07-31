# KolayBarkod — Donanım Kurulum Rehberi

## Gereksinimler
- Python 3.10+ (python.org)
- TEM terazi: aynı Wi-Fi ağında olmalı
- Argox 214 veya Zebra GC420T: USB veya LAN bağlı

---

## 1. TEM Terazinin IP'sini Bul

**Yöntem A — Terazi menüsünden:**
Terazi ekranında: Ayarlar → Ağ → IP Adresi

**Yöntem B — Modem admin panelinden:**
Tarayıcıda 192.168.1.1 veya 192.168.0.1 aç
Bağlı cihazlar listesinde "TEM" veya terazi adını bul

**Yöntem C — Windows komut satırından:**
```
arp -a
```
Listede bilinmeyen IP'leri dene: `ping 192.168.1.xxx`

---

## 2. terazi_servisi.py Yapılandır

Dosyayı Not Defteri ile aç, şu satırları düzenle:

```python
TERAZI_MOD   = "tcp"           # tcp | seri | demo
TERAZI_IP    = "192.168.1.100" # ← TEM terazinin gerçek IP'si
TERAZI_PORT  = 8000            # TEM dokümantasyonuna bak (genelde 8000)
```

**Seri port kullanıyorsan:**
```python
TERAZI_MOD  = "seri"
SERI_PORT   = "COM3"  # Aygıt Yöneticisi'nden kontrol et
SERI_BAUD   = 9600
```

**Test etmek için önce demo modunu dene:**
```python
TERAZI_MOD = "demo"
```

---

## 3. yazici_servisi.py Yapılandır

### Argox 214 — USB bağlıysa:
```python
"argox": {
    "mod": "usb_raw",
    "usb_yol": r"\\.\USB001",  # veya USB002, USB003
}
```

### Argox 214 — LAN bağlıysa:
```python
"argox": {
    "mod": "tcp",
    "ip": "192.168.1.101",  # Argox'un IP'si
    "port": 9100,
}
```

### Zebra GC420T — USB:
```python
"zebra": {
    "mod": "usb_raw",
    "usb_yol": r"\\.\USB002",
}
```

### Zebra GC420T — LAN:
```python
"zebra": {
    "mod": "tcp",
    "ip": "192.168.1.102",
    "port": 9100,
}
```

**USB yolunu bulmak için:**
Aygıt Yöneticisi → Yazdırma Kuyruğu → Yazıcı adına sağ tık → Özellikler → Port

---

## 4. Başlatma

`BASLAT.bat` dosyasına çift tıkla.
2 yeni pencere açılır:
- Mavi pencere = Terazi servisi
- Mor pencere = Yazıcı servisi

---

## 5. Test

**Terazi testi:**
Tarayıcıda aç: http://localhost:8765 (WebSocket test)

**Yazıcı testi:**
Tarayıcı adres çubuğuna yaz:
http://localhost:9200/test/zebra
http://localhost:9200/test/argox

Yazıcıdan test etiketi çıkmalı.

**Servis durumu:**
http://localhost:9200/durum

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Terazi bağlanamıyor | IP'yi kontrol et, aynı ağda mı? |
| USB yazıcı bulunamıyor | USB001 yerine USB002 dene |
| LAN yazıcı yanıt vermiyor | Yazıcı IP'sini `ping` ile test et |
| Port meşgul hatası | Başka bir servis 8765/9200 kullanıyor olabilir |
| Baud rate hatası | 9600 yerine 4800 veya 19200 dene |

---

## Windows Başlangıcına Ekleme (İsteğe Bağlı)

BASLAT.bat dosyasını şu klasöre kopyala:
```
C:\Users\KULLANICIADI\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```
Artık Windows açılınca otomatik başlar.
