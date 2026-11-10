# KolayBarkod

Tek sayfalık POS / stok uygulaması. Canlı adres: kolaybarkod.kolaycafe.com (GitHub Pages, `main` dalı).

- `index.html` — tüm arayüz ve ekran mantığı (HTML + CSS + JS tek dosyada)
- `kb_supabase_client.js` — Supabase veri katmanı (Supabase projesi: `sjfcdthwlwmbdmcevobv`, tablolar `kb_` önekli, çok kiracılı/RLS)
- `terazi_servisi.py`, `yazici_servisi.py`, `BASLAT.bat` — mağaza bilgisayarında çalışan yerel terazi (ws://localhost:8765) ve etiket yazıcısı (http://localhost:9200) servisleri

Kurallar
- **Her oturumun başında, dosyalara dokunmadan önce `git pull` yap.** Bu depo hem yerel bilgisayardan hem bulut oturumlarından güncelleniyor; eski kopya üstüne yazmak değişiklikleri kaybettirir. İş bitince commit + push yap.
- Birimler `BIRIMLER` listesinde: sayılan (adet, dizi, demet…) tıklayınca 1 ekler; kg/gr tartılı; lt/ml/metre miktar sorar. Ekranda "₺/kg" gibi sabit birim yazma, `fmtFiyat` / `fmtMiktar` kullan.
- Terazi ve yazıcı mağaza ayarına bağlı: `kb_magazalar.ayarlar` → `{ terazi: bool, yazici: bool }` (Ayarlar: sol alttaki mağaza adı).
- Supabase bir sorguda en fazla 1000 satır döner — listelerde `range()` ile sayfala.
- Ürün silme = `aktif=false`; aynı barkodla yeniden ekleme eski kaydı geri açar.
- Önemli değişikliklerden sonra test et (Playwright + sahte Supabase yanıtlarıyla ekranlar denenebilir).
