# Demo Portföy Test Senaryosu — 100.000 TRY

Bu senaryo demo hesabın işlem geçmişi boşken uygulanır. Amaç; sermaye, alım, dönüşüm, satış, komisyon, bakiye bağımlılıkları ve rapor hesaplarını uçtan uca doğrulamaktır.

Senaryonun ledger matematiği `tests/portfolio-regression.test.js` içinde otomatik
olarak doğrulanır. Otomatik test; 12 ara/final bakiye, maliyet/KZ, komisyon,
kronolojik sıra, hesap izolasyonu, revision/cancellation ve idempotent retry
kontrollerini kapsar. Bu belgeyle yapılan ekran testi; form özetlerini, gerçek
Supabase RLS akışını ve Dashboard/Portföy/İşlemler/Raporlar sunumunu ayrıca doğrular.

## Sabit Test Piyasa Değerleri

Demo market snapshot:

- USD/TRY: `47.40`
- BTC/USD: `64,800`
- ETH/USD: `1,920`
- URA/USD: `37.50`

Tüm adımlarda USD/TRY alanına `47.40` gir. İşlem tarih/saatlerini sıralı olacak şekilde aynı gün içinde ilerletebilirsin.

## 1 — Yatırım Bütçesi Girişi

Sermaye ekranı:

- Hareket: `Yatırım Bütçesi Girişi [CASH_IN]`
- Para birimi: `TRY`
- Tutar: `100000`
- USD/TRY: `47.40`
- Masraf: `0 TRY`
- Banka/Borsa: `Test Banka → Test Borsa`

Beklenen bakiye: `100,000 TRY`.

## 2 — TRY ile BTC Alımı, Komisyonlu

Alım ekranı:

- Kaynak: `TRY`
- Alınan: `BTC`
- Alım miktarı: `0.008 BTC`
- Birim fiyat: `3,000,000 TRY/BTC`
- Komisyon: `24 TRY`
- USD/TRY: `47.40`
- Platform: `Test Borsa`

İşlem tutarı `24,000 TRY`, toplam kaynak düşüşü `24,024 TRY` olmalı.

Beklenen bakiye: `75,976 TRY`, `0.008 BTC`.

## 3 — TRY ile ETH Alımı, Komisyonsuz

- Kaynak: `TRY`
- Alınan: `ETH`
- Alım miktarı: `0.25 ETH`
- Birim fiyat: `90,000 TRY/ETH`
- Komisyon: `0 TRY`
- USD/TRY: `47.40`

Beklenen bakiye: `53,476 TRY`, `0.008 BTC`, `0.25 ETH`.

## 4 — TRY → USD Dönüşümü

Dönüşüm ekranı:

- Kaynak: `TRY`
- Hedef: `USD`
- Dönüştürülen miktar: `12000 TRY`
- TRY/USD paritesi: `0.0210970464135` (`1 TRY = 0.0210970464135 USD`)
- Komisyon varlığı: `USD`
- Komisyon: `0`
- Net USD: yaklaşık `253.164556962 USD`
- USD/TRY: `47.40`

Beklenen bakiye: `41,476 TRY`, `253.164556962 USD`, `0.008 BTC`, `0.25 ETH`.

## 5 — USD ile BTC Alımı, Komisyonlu

- Kaynak: `USD`
- Alınan: `BTC`
- Alım miktarı: `0.003 BTC`
- Birim fiyat: `63,000 USD/BTC`
- Komisyon: `0.189 USD`
- USD/TRY: `47.40`

İşlem tutarı `189 USD`, toplam USD düşüşü `189.189 USD`.

Beklenen USD: yaklaşık `63.975556962 USD`.
Beklenen BTC: `0.011 BTC`.

## 6 — İlk URA Alımı, Komisyonlu

- Kaynak: `TRY`
- Alınan: `URA`
- Alım miktarı: `12 URA`
- Birim fiyat: `1,720 TRY/URA`
- Komisyon: `20.64 TRY`
- USD/TRY: `47.40`

İşlem tutarı `20,640 TRY`, toplam düşüş `20,660.64 TRY`.

Beklenen bakiye: `20,815.36 TRY`, `12 URA`.

## 7 — ETH → BTC Dönüşümü, Hedef Komisyonlu

- Kaynak: `ETH`
- Hedef: `BTC`
- Dönüştürülen miktar: `0.10 ETH`
- ETH/BTC paritesi: `0.0295`
- ETH işlem fiyatı (USD): `1920`
- Komisyon varlığı: `BTC`
- Komisyon: `0.00000295 BTC`
- Hesaplanan brüt hedef: `0.00295 BTC`
- Beklenen net hedef: `0.00294705 BTC`
- USD/TRY: `47.40`

Beklenen ETH: `0.15 ETH`.
Beklenen BTC: `0.01394705 BTC`.

## 8 — BTC → ETH Dönüşümü, Kaynak Komisyonlu

- Kaynak: `BTC`
- Hedef: `ETH`
- Dönüştürülen işlem miktarı: `0.004 BTC`
- BTC/ETH paritesi: `33.80`
- BTC işlem fiyatı (USD): `64800`
- Komisyon varlığı: `BTC`
- Komisyon: `0.000004 BTC`
- Toplam BTC bakiye düşüşü: `0.004004 BTC`
- Net hedef: `0.1352 ETH`
- USD/TRY: `47.40`

Beklenen BTC: `0.00994305 BTC`.
Beklenen ETH: `0.2852 ETH`.

## 9 — İkinci URA Alımı, Komisyonsuz

- Kaynak: `TRY`
- Alınan: `URA`
- Alım miktarı: `4 URA`
- Birim fiyat: `1,760 TRY/URA`
- Komisyon: `0 TRY`
- USD/TRY: `47.40`

Beklenen TRY: `13,775.36 TRY`.
Beklenen URA: `16 URA`.

## 10 — URA Satışı / Kısmi Çıkış

Satış ekranı:

- Satılan: `URA`
- Satış karşılığı: `TRY`
- Satılan miktar: `6 URA`
- Birim satış fiyatı: `1,850 TRY/URA`
- Komisyon: `11.10 TRY`
- Brüt tutar: `11,100 TRY`
- Net tutar: `11,088.90 TRY`
- USD/TRY: `47.40`

Beklenen TRY: `24,864.26 TRY`.
Beklenen URA: `10 URA`.

## 11 — BTC Satışı, Komisyonlu

- Satılan: `BTC`
- Satış karşılığı: `TRY`
- Satılan miktar: `0.002 BTC`
- Birim satış fiyatı: `3,120,000 TRY/BTC`
- Komisyon: `6.24 TRY`
- Brüt tutar: `6,240 TRY`
- Net tutar: `6,233.76 TRY`
- USD/TRY: `47.40`

Beklenen TRY: `31,098.02 TRY`.
Beklenen BTC: `0.00794305 BTC`.

## 12 — Sermaye Çıkışı

- Hareket: `Sermaye Çıkışı [CASH_OUT]`
- Para birimi: `TRY`
- Tutar: `25,000 TRY`
- USD/TRY: `47.40`
- Masraf: `0 TRY`

### Beklenen Nihai Bakiyeler

- TRY: `6,098.02`
- USD: `63.975556962`
- BTC: `0.00794305`
- ETH: `0.2852`
- URA: `10`

## Nihai Kontrol Değerleri

Demo snapshot fiyatları değişmediği sürece yaklaşık olarak:

- Portföy değeri: `1,629.919408 USD` = `77,258.18 TRY`
- Net sermaye: `1,582.278481 USD` = `75,000 TRY`
- Toplam K/Z: `47.640927 USD` = `2,258.18 TRY`
- Gerçekleşen K/Z: yaklaşık `19.269019 USD` = `913.35 TRY`
- Gerçekleşmemiş K/Z: yaklaşık `28.371908 USD` = `1,344.83 TRY`
- Toplam komisyon: yaklaşık `1.946955 USD` = `92.29 TRY`
- İşlem sayısı: `12`

Yuvarlama nedeniyle ekranda son basamaklarda küçük farklar kabul edilebilir. Bakiyelerde belirgin fark varsa ilgili işlem adımının özet ekranı ve İşlem Geçmişi kaydı incelenmelidir.

## Test Sonunda Paylaşılacak Görüntüler

1. Dashboard
2. Portföy
3. İşlem Geçmişi
4. Raporlar
5. Dönüşüm veya Satış özet pencerelerinden en az bir örnek

Display birimini önce `TRY`, sonra `USD` seçerek Dashboard ve Raporlar ekranlarını kontrol et. Yenileme sonrası seçimin korunması gerekir.
