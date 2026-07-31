-- ============================================================
-- KolayBarkod — Supabase Şema
-- Proje: sjfcdthwlwmbdmcevobv (KolayCafe ile ortak)
-- Prefix: kb_
-- ============================================================

-- ── 1. MAĞAZALAR (tenant tablosu) ───────────────────────────
CREATE TABLE IF NOT EXISTS kb_magazalar (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  magaza_adi      TEXT NOT NULL,
  yetkili_adi     TEXT,
  telefon         TEXT,
  email           TEXT,
  adres           TEXT,
  vergi_no        TEXT,
  sehir           TEXT,
  sektor          TEXT DEFAULT 'kuruyemis', -- kuruyemis | baharat | genel
  plan            TEXT DEFAULT 'free',      -- free | pro | elite
  plan_bitis      TIMESTAMPTZ,
  aktif           BOOLEAN DEFAULT true,
  gecici_sifre    TEXT,
  ayarlar         JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 2. ÜRÜNLER ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_urunler (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  barkod          TEXT,
  urun_adi        TEXT NOT NULL,
  kategori        TEXT DEFAULT 'Genel',
  birim           TEXT DEFAULT 'kg',        -- kg | adet | litre
  fiyat           NUMERIC(10,2) NOT NULL DEFAULT 0,
  kdv_orani       NUMERIC(4,2) DEFAULT 8,
  stok            NUMERIC(10,3) DEFAULT 0,
  min_stok        NUMERIC(10,3) DEFAULT 1,
  skt             TEXT,                     -- YYYY-MM formatında
  aciklama        TEXT,
  aktif           BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE(magaza_id, barkod)
);

-- ── 3. STOK HAREKETLERİ ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_stok_hareketleri (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  urun_id         UUID NOT NULL REFERENCES kb_urunler(id) ON DELETE CASCADE,
  hareket_tipi    TEXT NOT NULL,  -- giris | cikis | satis | fire | cop | kayip | sayim
  miktar          NUMERIC(10,3) NOT NULL,
  onceki_stok     NUMERIC(10,3),
  sonraki_stok    NUMERIC(10,3),
  birim_fiyat     NUMERIC(10,2),
  toplam_tutar    NUMERIC(10,2),
  aciklama        TEXT,
  referans_id     UUID,           -- satis_id veya fire_id
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 4. SATIŞLAR ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_satislar (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  satis_no        SERIAL,
  toplam_tutar    NUMERIC(10,2) NOT NULL DEFAULT 0,
  kdv_tutari      NUMERIC(10,2) DEFAULT 0,
  indirim         NUMERIC(10,2) DEFAULT 0,
  odeme_yontemi   TEXT DEFAULT 'nakit',  -- nakit | kart | karma
  nakit_tutar     NUMERIC(10,2) DEFAULT 0,
  kart_tutar      NUMERIC(10,2) DEFAULT 0,
  para_ustu       NUMERIC(10,2) DEFAULT 0,
  cari_id         UUID,
  notlar          TEXT,
  iptal           BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 5. SATIŞ KALEMLERİ ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_satis_kalemleri (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  satis_id        UUID NOT NULL REFERENCES kb_satislar(id) ON DELETE CASCADE,
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  urun_id         UUID REFERENCES kb_urunler(id) ON DELETE SET NULL,
  urun_adi        TEXT NOT NULL,         -- snapshot — ürün silinse bile kalsın
  barkod          TEXT,
  miktar          NUMERIC(10,3) NOT NULL,
  birim           TEXT DEFAULT 'kg',
  birim_fiyat     NUMERIC(10,2) NOT NULL,
  toplam          NUMERIC(10,2) NOT NULL,
  kdv_orani       NUMERIC(4,2) DEFAULT 8
);

-- ── 6. CARİ HESAPLAR ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_cari_hesaplar (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  cari_tipi       TEXT DEFAULT 'musteri',  -- musteri | toptanci | tedarikci
  ad_soyad        TEXT NOT NULL,
  firma_adi       TEXT,
  telefon         TEXT,
  email           TEXT,
  adres           TEXT,
  vergi_no        TEXT,
  bakiye          NUMERIC(10,2) DEFAULT 0, -- + alacak, - borç
  kredi_limiti    NUMERIC(10,2) DEFAULT 0,
  notlar          TEXT,
  aktif           BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 7. CARİ HAREKETLER ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_cari_hareketler (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  cari_id         UUID NOT NULL REFERENCES kb_cari_hesaplar(id) ON DELETE CASCADE,
  hareket_tipi    TEXT NOT NULL,  -- satis | tahsilat | iade | duzeltme
  tutar           NUMERIC(10,2) NOT NULL,
  bakiye_sonrasi  NUMERIC(10,2),
  aciklama        TEXT,
  referans_id     UUID,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 8. FİRE / ÇÖP KAYITLARI ─────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_fire_kayitlari (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  urun_id         UUID REFERENCES kb_urunler(id) ON DELETE SET NULL,
  urun_adi        TEXT NOT NULL,
  kayip_tipi      TEXT NOT NULL,  -- fire | cop | kayip | iade
  miktar_kg       NUMERIC(10,3) NOT NULL,
  tahmini_deger   NUMERIC(10,2),
  tarih           DATE DEFAULT CURRENT_DATE,
  notlar          TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ── 9. ETİKET ŞABLONLARI ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_etiket_sablonlari (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  magaza_id       UUID NOT NULL REFERENCES kb_magazalar(id) ON DELETE CASCADE,
  sablon_adi      TEXT NOT NULL,
  boyut           TEXT DEFAULT '50x30',   -- 50x30 | 60x40 | 80x50
  yazici_tipi     TEXT DEFAULT 'zebra',   -- zebra | argox
  zpl_sablon      TEXT,                   -- ZPL şablon metni
  aktif           BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- FOREIGN KEY DÜZELTMESİ (satislar → cari önce oluşturulmalı)
-- ============================================================
ALTER TABLE kb_satislar
  ADD CONSTRAINT fk_satis_cari
  FOREIGN KEY (cari_id) REFERENCES kb_cari_hesaplar(id) ON DELETE SET NULL;

-- ============================================================
-- İNDEKSLER
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_kb_urunler_magaza    ON kb_urunler(magaza_id);
CREATE INDEX IF NOT EXISTS idx_kb_urunler_barkod    ON kb_urunler(barkod);
CREATE INDEX IF NOT EXISTS idx_kb_satislar_magaza   ON kb_satislar(magaza_id);
CREATE INDEX IF NOT EXISTS idx_kb_satislar_tarih    ON kb_satislar(created_at);
CREATE INDEX IF NOT EXISTS idx_kb_stok_magaza       ON kb_stok_hareketleri(magaza_id);
CREATE INDEX IF NOT EXISTS idx_kb_stok_urun         ON kb_stok_hareketleri(urun_id);
CREATE INDEX IF NOT EXISTS idx_kb_cari_magaza       ON kb_cari_hesaplar(magaza_id);
CREATE INDEX IF NOT EXISTS idx_kb_fire_magaza       ON kb_fire_kayitlari(magaza_id);
CREATE INDEX IF NOT EXISTS idx_kb_fire_tarih        ON kb_fire_kayitlari(tarih);
CREATE INDEX IF NOT EXISTS idx_kb_magazalar_user    ON kb_magazalar(user_id);

-- ============================================================
-- UPDATED_AT TRİGGER (urunler için)
-- ============================================================
CREATE OR REPLACE FUNCTION kb_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER kb_urunler_updated_at
  BEFORE UPDATE ON kb_urunler
  FOR EACH ROW EXECUTE FUNCTION kb_set_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Tabloları etkinleştir
ALTER TABLE kb_magazalar          ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_urunler            ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_stok_hareketleri   ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_satislar           ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_satis_kalemleri    ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_cari_hesaplar      ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_cari_hareketler    ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_fire_kayitlari     ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_etiket_sablonlari  ENABLE ROW LEVEL SECURITY;

-- kb_magazalar: sadece kendi mağazanı gör
CREATE POLICY kb_magaza_select ON kb_magazalar
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY kb_magaza_insert ON kb_magazalar
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY kb_magaza_update ON kb_magazalar
  FOR UPDATE USING (user_id = auth.uid());

-- Yardımcı fonksiyon: kullanıcının magaza_id'sini döndür
CREATE OR REPLACE FUNCTION kb_magaza_id()
RETURNS UUID AS $$
  SELECT id FROM kb_magazalar WHERE user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Ürünler
CREATE POLICY kb_urun_all ON kb_urunler
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Stok hareketleri
CREATE POLICY kb_stok_all ON kb_stok_hareketleri
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Satışlar
CREATE POLICY kb_satis_all ON kb_satislar
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Satış kalemleri
CREATE POLICY kb_kalem_all ON kb_satis_kalemleri
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Cari hesaplar
CREATE POLICY kb_cari_all ON kb_cari_hesaplar
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Cari hareketler
CREATE POLICY kb_cari_har_all ON kb_cari_hareketler
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Fire kayıtları
CREATE POLICY kb_fire_all ON kb_fire_kayitlari
  FOR ALL USING (magaza_id = kb_magaza_id());

-- Etiket şablonları
CREATE POLICY kb_etiket_all ON kb_etiket_sablonlari
  FOR ALL USING (magaza_id = kb_magaza_id());

-- ============================================================
-- STOK OTOMATIK DÜŞME FONKSİYONU
-- Satış yapılınca stok otomatik güncellenir
-- ============================================================
CREATE OR REPLACE FUNCTION kb_stok_dusu(
  p_urun_id   UUID,
  p_miktar    NUMERIC,
  p_satis_id  UUID DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
  v_onceki NUMERIC;
  v_sonraki NUMERIC;
  v_fiyat NUMERIC;
  v_magaza UUID;
BEGIN
  SELECT stok, fiyat, magaza_id
    INTO v_onceki, v_fiyat, v_magaza
    FROM kb_urunler
   WHERE id = p_urun_id;

  v_sonraki := GREATEST(0, v_onceki - p_miktar);

  UPDATE kb_urunler
     SET stok = v_sonraki, updated_at = now()
   WHERE id = p_urun_id;

  INSERT INTO kb_stok_hareketleri
    (magaza_id, urun_id, hareket_tipi, miktar, onceki_stok, sonraki_stok, birim_fiyat, toplam_tutar, referans_id)
  VALUES
    (v_magaza, p_urun_id, 'satis', p_miktar, v_onceki, v_sonraki, v_fiyat, v_fiyat * p_miktar, p_satis_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- GÜNLÜK RAPOR VIEW
-- ============================================================
CREATE OR REPLACE VIEW kb_gunluk_rapor AS
SELECT
  s.magaza_id,
  DATE(s.created_at) AS tarih,
  COUNT(s.id)                                    AS satis_sayisi,
  SUM(s.toplam_tutar)                            AS toplam_ciro,
  AVG(s.toplam_tutar)                            AS ortalama_sepet,
  SUM(CASE WHEN s.odeme_yontemi='nakit' THEN s.toplam_tutar ELSE 0 END) AS nakit,
  SUM(CASE WHEN s.odeme_yontemi='kart'  THEN s.toplam_tutar ELSE 0 END) AS kart,
  SUM(CASE WHEN s.odeme_yontemi='karma' THEN s.toplam_tutar ELSE 0 END) AS karma
FROM kb_satislar s
WHERE s.iptal = false
GROUP BY s.magaza_id, DATE(s.created_at);

-- ============================================================
-- EN ÇOK SATANLAR FONKSİYONU
-- ============================================================
CREATE OR REPLACE FUNCTION kb_en_cok_satanlar(
  p_magaza_id UUID,
  p_limit     INT DEFAULT 10
)
RETURNS TABLE (
  urun_adi      TEXT,
  barkod        TEXT,
  toplam_miktar NUMERIC,
  toplam_tutar  NUMERIC
) AS $$
  SELECT
    sk.urun_adi,
    sk.barkod,
    SUM(sk.miktar) AS toplam_miktar,
    SUM(sk.toplam) AS toplam_tutar
  FROM kb_satis_kalemleri sk
  JOIN kb_satislar s ON s.id = sk.satis_id
  WHERE sk.magaza_id = p_magaza_id
    AND s.iptal = false
  GROUP BY sk.urun_adi, sk.barkod
  ORDER BY toplam_miktar DESC
  LIMIT p_limit;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ============================================================
-- DEMO MAĞAZA VERİSİ (isteğe bağlı — test için)
-- Supabase'de auth.users'a kayıt olmadan önce ÇALIŞTIRMA
-- Kayıt olduktan sonra user_id'yi güncelleyebilirsin
-- ============================================================
/*
INSERT INTO kb_magazalar (magaza_adi, yetkili_adi, sehir, sektor, plan)
VALUES ('Demo Baharat Mağazası', 'Test Kullanıcı', 'Aydın', 'baharat', 'pro');
*/
