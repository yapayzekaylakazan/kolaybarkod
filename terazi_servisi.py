"""
KolayBarkod — TEM Terazi WebSocket Köprü Servisi
=================================================
Bu servis:
  1. TEM teraziye TCP/UDP ile bağlanır (ağ üzerinden)
  2. Okunan ağırlığı WebSocket üzerinden tarayıcıya iletir
  3. Tarayıcı ws://localhost:8765 adresine bağlanır

Kurulum:
  pip install websockets pyserial

Çalıştırma:
  python terazi_servisi.py

Yapılandırma (aşağıdaki sabitleri düzenle):
  TERAZI_IP    → TEM terazinin IP adresi (modem admin panelinden bak)
  TERAZI_PORT  → TEM terazinin TCP portu (genelde 8000 veya 4001)
  TERAZI_MOD   → "tcp" veya "seri" (seri port için COM3 gibi)
  SERI_PORT    → Seri port modu için COM portu (örn: "COM3")
  SERI_BAUD    → Seri baud rate (TEM için genelde 9600)
"""

import asyncio
import json
import logging
import re
import socket
import threading
import time
from datetime import datetime

# ── YAPILANDIRMA ─────────────────────────────────────────────
TERAZI_MOD   = "tcp"        # "tcp" | "seri" | "demo"
TERAZI_IP    = "192.168.1.100"  # TEM terazinin IP adresi
TERAZI_PORT  = 8000         # TEM TCP portu (cihaz dokümantasyonuna bak)
SERI_PORT    = "COM3"       # Seri mod için COM portu
SERI_BAUD    = 9600         # Seri baud rate
WS_PORT      = 8765         # WebSocket portu (tarayıcı buraya bağlanır)
OKUMA_ARASI  = 0.3          # Saniyede kaç kez oku (0.3 = ~3/sn)
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("KolayBarkod-Terazi")

try:
    import websockets
except ImportError:
    log.error("websockets modülü eksik → pip install websockets")
    exit(1)

# Anlık durum
durum = {
    "agirlik": 0.000,
    "birim": "kg",
    "stabil": False,
    "bagli": False,
    "hata": None,
    "son_guncelleme": None
}

bagli_istemciler = set()


# ── AĞIRLIK AYIKLAMA ─────────────────────────────────────────
def agirlik_ayikla(veri: bytes) -> float | None:
    """
    TEM terazi farklı protokoller kullanabilir.
    Yaygın formatlar aşağıda denenir sırayla.
    """
    try:
        metin = veri.decode("ascii", errors="ignore").strip()
    except Exception:
        return None

    # Format 1: "ST,GS,+0001.234kg" (standart terazi protokolü)
    m = re.search(r"[+\-]?\s*(\d+\.?\d*)\s*kg", metin, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # Format 2: "+001234g" → gram → kg'a çevir
    m = re.search(r"[+\-]?\s*(\d+\.?\d*)\s*g\b", metin, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 1000.0

    # Format 3: Sadece sayı "1.234"
    m = re.search(r"(\d+\.\d{3})", metin)
    if m:
        return float(m.group(1))

    # Format 4: "000123" → son 5 hane gram
    m = re.search(r"(\d{6})", metin)
    if m:
        return int(m.group(1)[-5:]) / 1000.0

    return None


# ── TCP OKUYUCU ───────────────────────────────────────────────
def tcp_okuyucu():
    log.info(f"TCP modu → {TERAZI_IP}:{TERAZI_PORT}")
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((TERAZI_IP, TERAZI_PORT))
                s.settimeout(2)
                durum["bagli"] = True
                durum["hata"] = None
                log.info("Terazi TCP bağlantısı kuruldu")
                while True:
                    try:
                        veri = s.recv(64)
                        if not veri:
                            break
                        agirlik = agirlik_ayikla(veri)
                        if agirlik is not None:
                            durum["agirlik"] = round(agirlik, 3)
                            durum["stabil"] = True
                            durum["son_guncelleme"] = datetime.now().isoformat()
                    except socket.timeout:
                        # Terazi veri göndermiyorsa istek gönder
                        try:
                            s.send(b"\x05")  # ENQ — veri talep karakteri
                        except Exception:
                            break
                    time.sleep(OKUMA_ARASI)
        except ConnectionRefusedError:
            durum["bagli"] = False
            durum["hata"] = f"Bağlantı reddedildi: {TERAZI_IP}:{TERAZI_PORT}"
            log.warning(durum["hata"])
        except socket.timeout:
            durum["bagli"] = False
            durum["hata"] = "Bağlantı zaman aşımı"
            log.warning(durum["hata"])
        except Exception as e:
            durum["bagli"] = False
            durum["hata"] = str(e)
            log.error(f"TCP hatası: {e}")
        time.sleep(3)


# ── SERİ PORT OKUYUCU ─────────────────────────────────────────
def seri_okuyucu():
    try:
        import serial
    except ImportError:
        log.error("pyserial eksik → pip install pyserial")
        return

    log.info(f"Seri mod → {SERI_PORT} @ {SERI_BAUD} baud")
    while True:
        try:
            with serial.Serial(SERI_PORT, SERI_BAUD, timeout=2) as ser:
                durum["bagli"] = True
                durum["hata"] = None
                log.info(f"Seri port açıldı: {SERI_PORT}")
                while True:
                    satir = ser.readline()
                    if satir:
                        agirlik = agirlik_ayikla(satir)
                        if agirlik is not None:
                            durum["agirlik"] = round(agirlik, 3)
                            durum["stabil"] = True
                            durum["son_guncelleme"] = datetime.now().isoformat()
        except Exception as e:
            durum["bagli"] = False
            durum["hata"] = str(e)
            log.error(f"Seri hata: {e}")
        time.sleep(3)


# ── DEMO MODU ─────────────────────────────────────────────────
def demo_okuyucu():
    """Gerçek terazi yokken test için rastgele ağırlık üretir"""
    import random
    log.warning("DEMO MODU — gerçek terazi bağlı değil")
    agirliklar = [0.250, 0.500, 0.324, 0.175, 1.200, 0.050]
    i = 0
    while True:
        durum["agirlik"] = agirliklar[i % len(agirliklar)]
        durum["bagli"] = True
        durum["stabil"] = True
        durum["son_guncelleme"] = datetime.now().isoformat()
        i += 1
        time.sleep(2)


# ── WEBSOCKET SUNUCU ──────────────────────────────────────────
async def ws_handler(websocket):
    bagli_istemciler.add(websocket)
    ip = websocket.remote_address[0]
    log.info(f"Tarayıcı bağlandı: {ip} (toplam: {len(bagli_istemciler)})")
    try:
        # Bağlanınca hemen mevcut durumu gönder
        await websocket.send(json.dumps(durum))
        # Sonraki mesajları dinle (örn: tare komutu)
        async for mesaj in websocket:
            try:
                komut = json.loads(mesaj)
                if komut.get("komut") == "tare":
                    durum["agirlik"] = 0.000
                    log.info("Tare komutu alındı — sıfırlandı")
                    await websocket.send(json.dumps({"tare": True, **durum}))
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    finally:
        bagli_istemciler.discard(websocket)
        log.info(f"Tarayıcı ayrıldı: {ip}")


async def yayin_dongusu():
    """Her OKUMA_ARASI saniyede bağlı tüm istemcilere ağırlık yayınlar"""
    onceki = -1
    while True:
        await asyncio.sleep(OKUMA_ARASI)
        if bagli_istemciler and durum["agirlik"] != onceki:
            mesaj = json.dumps(durum)
            kapali = set()
            for ws in bagli_istemciler.copy():
                try:
                    await ws.send(mesaj)
                except Exception:
                    kapali.add(ws)
            bagli_istemciler -= kapali
            onceki = durum["agirlik"]


async def ana():
    # Terazi okuyucuyu ayrı thread'de başlat
    if TERAZI_MOD == "tcp":
        t = threading.Thread(target=tcp_okuyucu, daemon=True)
    elif TERAZI_MOD == "seri":
        t = threading.Thread(target=seri_okuyucu, daemon=True)
    else:
        t = threading.Thread(target=demo_okuyucu, daemon=True)
    t.start()

    # WebSocket sunucusunu başlat
    log.info(f"WebSocket sunucu başlatılıyor: ws://localhost:{WS_PORT}")
    async with websockets.serve(ws_handler, "localhost", WS_PORT):
        log.info("─" * 50)
        log.info("KolayBarkod Terazi Servisi hazır!")
        log.info(f"  Mod   : {TERAZI_MOD.upper()}")
        if TERAZI_MOD == "tcp":
            log.info(f"  Terazi: {TERAZI_IP}:{TERAZI_PORT}")
        elif TERAZI_MOD == "seri":
            log.info(f"  Port  : {SERI_PORT} @ {SERI_BAUD}")
        log.info(f"  WS    : ws://localhost:{WS_PORT}")
        log.info("─" * 50)
        await yayin_dongusu()


if __name__ == "__main__":
    try:
        asyncio.run(ana())
    except KeyboardInterrupt:
        log.info("Servis durduruldu")
