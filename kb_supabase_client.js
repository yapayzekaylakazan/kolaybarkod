// ============================================================
// KolayBarkod — Supabase Veri Katmanı
// Bu bloğu index.html'deki <script> içine ekle
// ============================================================

// ── YAPILANDIRMA ─────────────────────────────────────────────
const SUPABASE_URL  = 'https://sjfcdthwlwmbdmcevobv.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNqZmNkdGh3bHdtYmRtY2V2b2J2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE4MDA3OTYsImV4cCI6MjA4NzM3Njc5Nn0.B--4Quy58qdU1IK48U-pr25hKoesqViMR0QvxNBiRbs';
// ─────────────────────────────────────────────────────────────

// Supabase client (CDN'den yüklenir — index.html head'ine ekle)
// <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
const { createClient } = supabase;
const sb = createClient(SUPABASE_URL, SUPABASE_ANON);

// Aktif mağaza ID (login sonrası set edilir)
let MAGAZA_ID = null;

// ============================================================
// AUTH
// ============================================================
async function girisYap(email, sifre) {
  const captchaToken = document.querySelector('[name="h-captcha-response"]')?.value;
  const { data, error } = await sb.auth.signInWithPassword({
    email,
    password: sifre,
    options: { captchaToken }
  });
  if (error) {
    // Hata durumunda captcha'yı sıfırla ki kullanıcı tekrar çözebilsin
    if (typeof hcaptcha !== 'undefined') hcaptcha.reset();
    throw error;
  }
  await magazaYukle();
  return data;
}

async function cikisYap() {
  await sb.auth.signOut();
  MAGAZA_ID = null;
  localStorage.removeItem('kb_magaza_id');
  window.location.reload();
}

async function magazaYukle() {
  const { data, error } = await sb
    .from('kb_magazalar')
    .select('id, magaza_adi, plan, aktif')
    .single();
  if (error || !data) throw new Error('Mağaza bulunamadı');
  MAGAZA_ID = data.id;
  localStorage.setItem('kb_magaza_id', MAGAZA_ID);
  return data;
}

// ============================================================
// ÜRÜNLER
// ============================================================
async function urunleriGetir(arama = '', kategori = '') {
  let q = sb.from('kb_urunler')
    .select('*')
    .eq('magaza_id', MAGAZA_ID)
    .eq('aktif', true)
    .order('urun_adi');

  if (arama) q = q.ilike('urun_adi', `%${arama}%`);
  if (kategori) q = q.eq('kategori', kategori);

  const { data, error } = await q;
  if (error) throw error;
  return data;
}

async function urunEkle(urun) {
  const { data, error } = await sb.from('kb_urunler').insert({
    magaza_id: MAGAZA_ID,
    ...urun
  }).select().single();
  if (error) throw error;
  return data;
}

async function urunGuncelle(id, degerler) {
  const { data, error } = await sb.from('kb_urunler')
    .update(degerler)
    .eq('id', id)
    .eq('magaza_id', MAGAZA_ID)
    .select().single();
  if (error) throw error;
  return data;
}

async function urunSil(id) {
  const { error } = await sb.from('kb_urunler')
    .update({ aktif: false })
    .eq('id', id)
    .eq('magaza_id', MAGAZA_ID);
  if (error) throw error;
}

async function barkoduBul(barkod) {
  const { data, error } = await sb.from('kb_urunler')
    .select('*')
    .eq('magaza_id', MAGAZA_ID)
    .eq('barkod', barkod)
    .eq('aktif', true)
    .single();
  if (error) return null;
  return data;
}

// ============================================================
// SATIŞ
// ============================================================
async function satisKaydet(sepet, odemeYontemi, nakit = 0, kart = 0) {
  const toplam = sepet.reduce((s, i) => s + i.toplam, 0);

  // 1. Satış başlığı
  const { data: satis, error: satisErr } = await sb.from('kb_satislar').insert({
    magaza_id: MAGAZA_ID,
    toplam_tutar: toplam,
    odeme_yontemi: odemeYontemi,
    nakit_tutar: nakit,
    kart_tutar: kart,
    para_ustu: Math.max(0, nakit - toplam)
  }).select().single();
  if (satisErr) throw satisErr;

  // 2. Satış kalemleri
  const kalemler = sepet.map(item => ({
    satis_id: satis.id,
    magaza_id: MAGAZA_ID,
    urun_id: item.urunId,
    urun_adi: item.urunAdi,
    barkod: item.barkod,
    miktar: item.miktar,
    birim: item.birim,
    birim_fiyat: item.birimFiyat,
    toplam: item.toplam,
    kdv_orani: item.kdvOrani || 8
  }));

  const { error: kalemErr } = await sb.from('kb_satis_kalemleri').insert(kalemler);
  if (kalemErr) throw kalemErr;

  // 3. Stok düş (her kalem için)
  for (const item of sepet) {
    if (item.urunId) {
      await sb.rpc('kb_stok_dusu', {
        p_urun_id: item.urunId,
        p_miktar: item.miktar,
        p_satis_id: satis.id
      });
    }
  }

  return satis;
}

// ============================================================
// STOK
// ============================================================
async function stokGirisi(urunId, miktar, aciklama = '') {
  // Mevcut stok
  const { data: urun } = await sb.from('kb_urunler')
    .select('stok, fiyat').eq('id', urunId).single();

  const yeniStok = (urun?.stok || 0) + miktar;

  await sb.from('kb_urunler')
    .update({ stok: yeniStok }).eq('id', urunId);

  await sb.from('kb_stok_hareketleri').insert({
    magaza_id: MAGAZA_ID,
    urun_id: urunId,
    hareket_tipi: 'giris',
    miktar,
    onceki_stok: urun?.stok || 0,
    sonraki_stok: yeniStok,
    birim_fiyat: urun?.fiyat || 0,
    aciklama
  });
}

async function kritikStoklariGetir() {
  const { data: urunler, error } = await sb.from('kb_urunler')
    .select('*')
    .eq('magaza_id', MAGAZA_ID)
    .eq('aktif', true);
  if (error) return [];
  return urunler.filter(u => u.stok < u.min_stok);
}

// ============================================================
// FİRE / ÇÖP
// ============================================================
async function fireKaydet(urunId, urunAdi, kayipTipi, miktarKg, notlar = '') {
  // Önce ürün fiyatını bul
  const { data: urun } = await sb.from('kb_urunler')
    .select('stok, fiyat').eq('id', urunId).single();

  const tahminiDeger = (urun?.fiyat || 0) * miktarKg;
  const yeniStok = Math.max(0, (urun?.stok || 0) - miktarKg);

  // Fire kaydı
  const { data, error } = await sb.from('kb_fire_kayitlari').insert({
    magaza_id: MAGAZA_ID,
    urun_id: urunId,
    urun_adi: urunAdi,
    kayip_tipi: kayipTipi,
    miktar_kg: miktarKg,
    tahmini_deger: tahminiDeger,
    notlar
  }).select().single();
  if (error) throw error;

  // Stok güncelle
  await sb.from('kb_urunler')
    .update({ stok: yeniStok }).eq('id', urunId);

  // Stok hareketi
  await sb.from('kb_stok_hareketleri').insert({
    magaza_id: MAGAZA_ID,
    urun_id: urunId,
    hareket_tipi: kayipTipi,
    miktar: miktarKg,
    onceki_stok: urun?.stok || 0,
    sonraki_stok: yeniStok,
    birim_fiyat: urun?.fiyat || 0,
    toplam_tutar: tahminiDeger,
    referans_id: data.id
  });

  return data;
}

// ============================================================
// CARİ HESAP
// ============================================================
async function carileriGetir(tip = null) {
  let q = sb.from('kb_cari_hesaplar')
    .select('*')
    .eq('magaza_id', MAGAZA_ID)
    .eq('aktif', true)
    .order('ad_soyad');
  if (tip) q = q.eq('cari_tipi', tip);
  const { data, error } = await q;
  if (error) throw error;
  return data;
}

async function cariHareket(cariId, hareketTipi, tutar, aciklama = '', referansId = null) {
  // Bakiyeyi güncelle
  const { data: cari } = await sb.from('kb_cari_hesaplar')
    .select('bakiye').eq('id', cariId).single();

  const yeniBakiye = (cari?.bakiye || 0) + tutar;

  await sb.from('kb_cari_hesaplar')
    .update({ bakiye: yeniBakiye }).eq('id', cariId);

  await sb.from('kb_cari_hareketler').insert({
    magaza_id: MAGAZA_ID,
    cari_id: cariId,
    hareket_tipi: hareketTipi,
    tutar,
    bakiye_sonrasi: yeniBakiye,
    aciklama,
    referans_id: referansId
  });
}

// ============================================================
// RAPORLAR
// ============================================================
async function gunlukRaporGetir(tarih = null) {
  const hedefTarih = tarih || new Date().toISOString().split('T')[0];
  const { data, error } = await sb.from('kb_gunluk_rapor')
    .select('*')
    .eq('magaza_id', MAGAZA_ID)
    .eq('tarih', hedefTarih)
    .single();
  if (error) return null;
  return data;
}

async function haftalikSatislariGetir() {
  const yediGunOnce = new Date();
  yediGunOnce.setDate(yediGunOnce.getDate() - 7);

  const { data, error } = await sb.from('kb_satislar')
    .select('toplam_tutar, odeme_yontemi, created_at')
    .eq('magaza_id', MAGAZA_ID)
    .eq('iptal', false)
    .gte('created_at', yediGunOnce.toISOString())
    .order('created_at');
  if (error) return [];
  return data;
}

async function enCokSatanlariGetir(limit = 10) {
  const { data, error } = await sb.rpc('kb_en_cok_satanlar', {
    p_magaza_id: MAGAZA_ID,
    p_limit: limit
  });
  if (error) return [];
  return data;
}

// ============================================================
// SKT TAKİP
// ============================================================
async function sktYaklasanlariGetir(gunSayisi = 30) {
  const simdi = new Date();
  const bitis = new Date();
  bitis.setDate(bitis.getDate() + gunSayisi);

  // YYYY-MM formatını karşılaştır
  const simdiFmt = simdi.toISOString().slice(0, 7);
  const bitisFmt = bitis.toISOString().slice(0, 7);

  const { data, error } = await sb.from('kb_urunler')
    .select('id, urun_adi, stok, skt, kategori')
    .eq('magaza_id', MAGAZA_ID)
    .eq('aktif', true)
    .not('skt', 'is', null)
    .lte('skt', bitisFmt)
    .gte('stok', 0.001)
    .order('skt');
  if (error) return [];
  return data;
}

// ============================================================
// REALTIME — Stok değişikliklerini anlık takip et
// ============================================================
function realtimeBaslat() {
  sb.channel('kb_stok')
    .on('postgres_changes', {
      event: 'UPDATE',
      schema: 'public',
      table: 'kb_urunler',
      filter: `magaza_id=eq.${MAGAZA_ID}`
    }, (payload) => {
      // Stok güncellenince UI'ı yenile
      console.log('[Realtime] Stok güncellendi:', payload.new.urun_adi, payload.new.stok);
      // renderStock() fonksiyonu varsa çağır
      if (typeof renderStock === 'function') renderStock();
      if (typeof updateBadges === 'function') updateBadges();
    })
    .subscribe();
}
