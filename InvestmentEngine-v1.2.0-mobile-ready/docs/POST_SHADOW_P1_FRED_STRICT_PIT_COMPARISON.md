# Post-Shadow P1 — FRED Gerçek Tarihsel Veri Karşılaştırması

**Kanıt tarihi:** 2026-09-07 (Europe/Istanbul)  
**Model:** 1.2.0  
**Mode:** SHADOW  
**Realtime execution:** OFF  
**Kapsam:** ETH/BTC geçmiş yön çekirdeğinde FRED'in bugün görünen geçmişi ile geçmiş tarihte gerçekten yayımlanmış ALFRED sürümlerinin karşılaştırılması. Üretim motoru davranışı değiştirilmemiştir.

## Sonuç özeti

```text
Doğrulama komutu                        ÇALIŞTI
stderr                                  BOŞ
FRED PIT odaklı testler                 8 passed
Tüm Python testleri                     62 passed
Release check                           OK
Sonuç durumu                            VERIFICATION_COMPLETE_WITH_SOURCE_GAP
DB'ye doğrulama kaydı yazıldı mı?       HAYIR
Otomatik parametre değişikliği          HAYIR
```

Bu koşu P1'in önemli bir sorusuna gerçek veriyle ilk yanıtı verdi:

> Bugün FRED'de görünen geçmiş değerleri kullanmak yerine o tarihte gerçekten yayımlanmış ALFRED değerlerini kullansaydık ETH/BTC motorunun geçmiş değerlendirmesi değişir miydi?

İlk sonuç: **bazı günlerde iç değerlendirme değişiyor; ancak yayımlanmış edge=70 uygunluk durumu hiçbir günde değişmiyor.**

Bununla birlikte ilk 23 replay gününde ALFRED'de bulunan serilerin bile tamamı mevcut değildir. Bu nedenle 1420 günlük ham karşılaştırmanın tamamını doğrudan "saf revision etkisi" diye adlandırmak doğru değildir. Temiz revision etkisi yalnız tam tarihsel kapsama bulunan günlerde ayrıca ölçülecektir.

## Veri kaynağı durumu

Yapılandırılmış sekiz FRED serisinden yedisi ALFRED tarihsel sürüm geçmişiyle doğrulanabildi.

`SP500` için FRED API açıkça serinin ALFRED'de bulunmadığını bildirdi. Bu nedenle strict geçmiş doğrulamada bugünkü SP500 değeri geçmişe taşınmadı; seri tarihsel olarak kanıtlanamayan/eksik kaynak kabul edildi.

Bu kaynak boşluğu nedeniyle tüm 8 serinin aynı anda tam olduğu strict kapsama oranı doğal olarak sıfırdır.

ALFRED'de bulunan seriler ayrıca ölçüldüğünde:

```text
Replay günü                            1420
Tam tarihsel veri bulunan gün          1397
Tam kapsama oranı                      %98.3803
İlk tam gün                            2022-11-10
Son tam gün                            2026-09-06
Eksik tarihsel kapsamlı ilk günler     23
```

İlk 23 replay gününde ALFRED'de mevcut yedi serinin en az biri eksiktir. Bu günler artık temiz revision karşılaştırmasına dahil edilmeyecektir.

## Karşılaştırma 1 — SP500 tarihsel kaynak boşluğunun etkisi

Bu karşılaştırma bugünkü FRED geçmişini kullanmaya devam eder; yalnız ALFRED'de geçmişi bulunmayan `SP500` çıkarılır. Böylece SP500 kaynak boşluğunun tek başına etkisi ölçülür.

```text
Karşılaştırılan gün                     1420
Ortalama mutlak edge farkı              0.5475
En büyük mutlak edge farkı              1.42
Rejim değişen gün                       0
Yön işareti değişen gün                 14
Edge=70 uygunluğu değişen gün           0
```

Yorum:

- `SP500` eksikliği edge puanında küçük kaymalar yaratıyor.
- Rejim sınıflandırmasını değiştirmedi.
- 14 günde signed-edge yön işareti değişti; ancak bu günlerin hiçbiri yayımlanmış `edge=70` uygunluk sınırını değiştirmedi.
- Dolayısıyla SP500 kaynak boşluğu mevcut evidence içinde yeni bir edge=70 sinyal üretmiyor veya mevcut bir edge=70 sinyali ortadan kaldırmıyor.

## Karşılaştırma 2 — 1420 günlük ham tarihsel fark

Bu karşılaştırmada yalnız ALFRED geçmişi bulunan seriler tutulur. Bir tarafta bugünkü FRED geçmiş değerleri, diğer tarafta geçmiş tarihte yayımlanmış ALFRED değerleri kullanılır.

İlk koşunun ham sonucu:

```text
Karşılaştırılan gün                     1420
Ortalama mutlak edge farkı              0.5398
En büyük mutlak edge farkı              14.41
Rejim değişen gün                       21
Yön işareti değişen gün                 5
Edge=70 uygunluğu değişen gün           0
```

Bu sayıların tamamını henüz "revision etkisi" saymıyoruz. Çünkü ilk 23 günde ALFRED'de bulunan yedi seriden en az biri eksik. O günlerdeki farklar iki nedeni birlikte taşıyabilir:

1. gerçek tarihsel revision/yayın-zamanı farkı,
2. eksik tarihsel seri nedeniyle kalite/puan farkı.

Bu nedenle verification kodu güncellendi. Yeni çıktı yalnız 7 serinin de mevcut olduğu 1397 günü ayrıca `vintage_comparison_complete_coverage` altında karşılaştıracaktır.

## Karşılaştırma 3 — Toplam etki

Bugünkü sekiz-seri FRED geçmişi doğrudan strict tarihsel replay ile karşılaştırıldığında:

```text
Karşılaştırılan gün                     1420
Ortalama mutlak edge farkı              0.9443
En büyük mutlak edge farkı              14.89
Rejim değişen gün                       21
Yön işareti değişen gün                 13
Edge=70 uygunluğu değişen gün           0
```

Bu toplam fark hem `SP500` kaynak boşluğunu hem ALFRED-available serilerin tarihsel farklarını hem de ilk 23 gündeki eksik tarihsel kapsama etkisini içerir.

## P1 açısından şu anda neyi kanıtladık?

1. Mevcut `macro.observations` tablosu strict geçmiş doğrulama için tek başına yeterli değildir.
2. ALFRED'de bulunan serilerle verification-only strict historical replay gerçek ortamda çalışmaktadır.
3. `SP500` ALFRED tarihsel geçmişi olmadığı için açık bir kaynak boşluğudur; bugünkü değer geçmişe uydurulmamıştır.
4. FRED/ALFRED kullanımı geçmiş model değerlendirmesinde fark yaratmaktadır; ancak bu farkın saf revision bileşeni temiz kapsama günleriyle ayrıca ayrıştırılmalıdır.
5. İlk 1420 günlük karşılaştırmada `edge=70` uygunluk durumu hiçbir günde değişmemiştir.
6. Bu nedenle şu ana kadarki kanıt, edge=70 sinyal kıtlığını yalnız FRED tarihsel revision sorunuyla açıklamıyor.

## Temiz karşılaştırma neden gerekli?

P1'in amacı yalnız fark bulmak değil, farkın nedenini doğru sınıflandırmaktır.

İlk 23 günde tarihsel veri eksik olduğu halde bu günleri revision etkisine katarsak:

- eksik veri nedeniyle düşen kaliteyi,
- gerçekten farklı yayımlanmış bir FRED değerinin etkisiyle

karıştırmış oluruz.

Bu yüzden yeni doğrulama çıktısı iki ayrı alan üretecek:

```text
vintage_comparison
    1420 günlük ham fark

vintage_comparison_complete_coverage
    yalnız 7 ALFRED serisinin de mevcut olduğu temiz günlerdeki fark
```

P1 FRED alt aşamasının revision etkisiyle ilgili nihai yorumu ikinci alan üzerinden yapılacaktır.

## Henüz neyi kanıtlamadık?

Bu çalışma production ACTION backtest değildir.

Hâlâ açık olanlar:

- İlk 23 gündeki eksik ALFRED serisinin/serilerinin belirlenmesi.
- Tam kapsamalı 1397 günlük temiz FRED tarihsel karşılaştırmanın yeniden çalıştırılması.
- Current/comparable/strict walk-forward özetlerinin birbirleriyle son kez karşılaştırılması.
- Production persistent K1/K2 state davranışının replay ile birebir eşitliği.
- Historical derivatives/event PIT geçmişi.
- URA full PIT.

Bu nedenle P1 genel aşaması devam etmektedir.

## Karar etkisi

Bu kanıt şunları **değiştirmez**:

- Model Version `1.2.0`
- Mode `SHADOW`
- Realtime Execution `OFF`
- edge threshold `70`
- confidence/data-quality threshold'ları
- factor ağırlıkları
- K1/K2
- reversal/reset
- sizing
- SHADOW -> LIVE durumu

`LIVE` hâlâ **NO-GO** durumundadır.
