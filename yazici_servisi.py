"""
KolayBarkod — Termal Yazıcı Yazdırma Servisi
=============================================
Argox 214 ve Zebra GC420T için ZPL/PPLA etiket yazdırma.

Kurulum:
  pip install flask flask-cors

Çalıştırma:
  python yazici_servisi.py

Tarayıcıdan kullanım:
  POST http://localhost:9200/yazdir
  Body: { "zpl": "^XA...^XZ", "yazici": "argox" }

NOT: Zebra için ayrıca Zebra BrowserPrint'i de kurabilirsin
     (zebra.com/browserprint) — bu servis ikisini de destekler.
"""

import json
import logging
import socket
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("KolayBarkod-Yazici")

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    log.error("flask/flask-cors eksik → pip install flask flask-cors")
    sys.exit(1)

# ── YAPILANDIRMA ─────────────────────────────────────────────
YAZICILAR = {
    "argox": {
        "mod":  "usb_raw",   # "usb_raw" | "tcp" | "lpt"
        "ip":   "192.168.1.101",
        "port": 9100,        # Argox LAN portu (genelde 9100)
        "usb_yol": r"\\.\USB001",  # Windows USB raw yolu
    },
    "zebra": {
        "mod":  "tcp",       # Zebra GC420T genelde LAN veya USB
        "ip":   "192.168.1.102",
        "port": 9100,        # Zebra standart ZPL portu
        "usb_yol": r"\\.\USB002",
    }
}
SERVIS_PORT = 9200
# ─────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*",
                   "file://*", "null"])


def tcp_yazdir(ip: str, port: int, zpl: str) -> bool:
    """TCP/LAN üzerinden ZPL gönder (Argox LAN / Zebra LAN)"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((ip, port))
            s.sendall(zpl.encode("utf-8"))
            log.info(f"TCP yazdırma başarılı → {ip}:{port}")
            return True
    except Exception as e:
        log.error(f"TCP yazdırma hatası: {e}")
        return False


def usb_raw_yazdir(usb_yol: str, zpl: str) -> bool:
    """Windows USB raw port üzerinden ZPL gönder"""
    try:
        with open(usb_yol, "wb") as f:
            f.write(zpl.encode("utf-8"))
        log.info(f"USB raw yazdırma başarılı → {usb_yol}")
        return True
    except Exception as e:
        log.error(f"USB raw hatası: {e}")
        # Alternatif: copy komutu ile
        try:
            zpl_dosya = Path("temp_etiket.zpl")
            zpl_dosya.write_text(zpl, encoding="utf-8")
            result = subprocess.run(
                ["copy", "/b", str(zpl_dosya), usb_yol],
                shell=True, capture_output=True
            )
            zpl_dosya.unlink(missing_ok=True)
            if result.returncode == 0:
                log.info("USB copy komutu başarılı")
                return True
        except Exception as e2:
            log.error(f"USB copy hatası: {e2}")
        return False


def yazici_yazdir(yazici_adi: str, zpl: str) -> dict:
    """Yazıcıya ZPL gönder, sonucu döndür"""
    yazici = YAZICILAR.get(yazici_adi)
    if not yazici:
        return {"basarili": False, "hata": f"Yazıcı bulunamadı: {yazici_adi}"}

    mod = yazici["mod"]
    if mod == "tcp":
        ok = tcp_yazdir(yazici["ip"], yazici["port"], zpl)
    elif mod == "usb_raw":
        ok = usb_raw_yazdir(yazici["usb_yol"], zpl)
    else:
        return {"basarili": False, "hata": f"Bilinmeyen mod: {mod}"}

    return {"basarili": ok, "hata": None if ok else "Yazdırma başarısız"}


# ── ZPL ETIKET ŞABLONLARI ────────────────────────────────────
def zpl_urun_etiketi(
    urun_adi: str,
    agirlik_g: float,
    fiyat_tl: float,
    barkod: str,
    skt: str = "",
    boyut: str = "50x30"
) -> str:
    """
    Ürün etiketi ZPL kodu oluştur.
    Desteklenen boyutlar: 50x30, 60x40, 80x50 mm
    DPI: 203 (Argox 214 ve Zebra GC420T varsayılan)
    """
    DPI = 203
    MM_PER_INCH = 25.4

    def mm2dot(mm): return int(mm * DPI / MM_PER_INCH)

    boyut_map = {
        "50x30": (50, 30),
        "60x40": (60, 40),
        "80x50": (80, 50),
    }
    gen_mm, yuk_mm = boyut_map.get(boyut, (50, 30))
    gen = mm2dot(gen_mm)
    yuk = mm2dot(yuk_mm)

    # Fiyat formatla
    fiyat_str = f"{fiyat_tl:.2f} TL"
    agirlik_str = f"{agirlik_g:.0f}g" if agirlik_g > 0 else ""
    skt_str = f"SKT: {skt}" if skt else ""

    # Ürün adını büyük harf, 20 karakter sınırla
    adi = urun_adi.upper()[:22]

    zpl = f"""^XA
^PW{gen}
^LL{yuk}
^CI28

^FO10,8^A0N,18,18^FD{adi}^FS
^FO10,30^A0N,14,14^FD{agirlik_str}^FS
^FO{gen-120},28^A0N,22,22^FD{fiyat_str}^FS

^FO10,52^BY2,3,40^BCN,40,N,N^FD{barkod}^FS

^FO10,{yuk-18}^A0N,11,11^FD{barkod}^FS
"""
    if skt_str:
        zpl += f"^FO{gen-90},{yuk-18}^A0N,11,11^FD{skt_str}^FS\n"

    zpl += "^XZ"
    return zpl


def zpl_fiyat_etiketi(urun_adi: str, fiyat_tl: float, birim: str = "kg") -> str:
    """Raf fiyat etiketi (barkod yok, sadece fiyat)"""
    return f"""^XA
^PW300^LL150^CI28
^FO10,10^A0N,20,20^FD{urun_adi.upper()[:18]}^FS
^FO10,40^A0N,32,32^FD{fiyat_tl:.2f} TL/{birim}^FS
^FO10,85^GB280,2,2^FS
^FO10,95^A0N,14,14^FDkolaybarkod.com^FS
^XZ"""


def zpl_test_sayfasi() -> str:
    """Yazıcı test etiketi"""
    return """^XA
^PW400^LL200^CI28
^FO20,20^A0N,24,24^FDKOLAYBARKOD TEST^FS
^FO20,60^A0N,16,16^FDYazici calisiyor!^FS
^FO20,85^A0N,14,14^FDArgox 214 / Zebra GC420T^FS
^FO20,110^BY2,3,40^BCN,40,N,N^FD1234567890^FS
^XZ"""


# ── HTTP UÇLARI ───────────────────────────────────────────────
@app.route("/yazdir", methods=["POST"])
def yazdir():
    """
    Etiket yazdır.
    Body (JSON):
      { "zpl": "...", "yazici": "argox" }
      veya
      { "sablonAdi": "urun", "yazici": "zebra", "veri": {...} }
    """
    data = request.get_json()
    if not data:
        return jsonify({"basarili": False, "hata": "JSON body gerekli"}), 400

    yazici = data.get("yazici", "zebra")

    # Ham ZPL gönderildiyse direkt kullan
    if "zpl" in data:
        zpl = data["zpl"]
    elif "sablonAdi" in data:
        sablon = data["sablonAdi"]
        veri = data.get("veri", {})
        if sablon == "urun":
            zpl = zpl_urun_etiketi(
                urun_adi=veri.get("urunAdi", "ÜRÜN"),
                agirlik_g=veri.get("agirlikG", 0),
                fiyat_tl=veri.get("fiyatTl", 0),
                barkod=veri.get("barkod", "0000000000000"),
                skt=veri.get("skt", ""),
                boyut=veri.get("boyut", "50x30")
            )
        elif sablon == "fiyat":
            zpl = zpl_fiyat_etiketi(
                urun_adi=veri.get("urunAdi", "ÜRÜN"),
                fiyat_tl=veri.get("fiyatTl", 0),
                birim=veri.get("birim", "kg")
            )
        elif sablon == "test":
            zpl = zpl_test_sayfasi()
        else:
            return jsonify({"basarili": False, "hata": f"Bilinmeyen şablon: {sablon}"}), 400
    else:
        return jsonify({"basarili": False, "hata": "zpl veya sablonAdi gerekli"}), 400

    sonuc = yazici_yazdir(yazici, zpl)
    log.info(f"Yazdırma: {yazici} → {'OK' if sonuc['basarili'] else 'HATA'}")
    return jsonify(sonuc)


@app.route("/yazicilar", methods=["GET"])
def yazicilar_listesi():
    """Mevcut yazıcı yapılandırmalarını döndür"""
    return jsonify({
        "yazicilar": list(YAZICILAR.keys()),
        "yapilandirma": {
            k: {"mod": v["mod"], "ip": v.get("ip", ""), "port": v.get("port", "")}
            for k, v in YAZICILAR.items()
        }
    })


@app.route("/test/<yazici_adi>", methods=["GET"])
def test_yazdir(yazici_adi):
    """Yazıcıya test sayfası yazdır"""
    zpl = zpl_test_sayfasi()
    sonuc = yazici_yazdir(yazici_adi, zpl)
    return jsonify(sonuc)


@app.route("/durum", methods=["GET"])
def durum():
    return jsonify({"servis": "calisıyor", "yazicilar": list(YAZICILAR.keys())})


if __name__ == "__main__":
    log.info("─" * 50)
    log.info("KolayBarkod Yazıcı Servisi başlatılıyor")
    log.info(f"  Port: http://localhost:{SERVIS_PORT}")
    log.info(f"  Yazıcılar: {', '.join(YAZICILAR.keys())}")
    log.info("─" * 50)
    app.run(host="localhost", port=SERVIS_PORT, debug=False)
