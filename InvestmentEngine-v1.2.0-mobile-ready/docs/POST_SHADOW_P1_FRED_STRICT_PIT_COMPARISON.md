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

Bu koşu P1'in önemli bir sorusuna gerçek veriyle cevap verdi:

> Bugün FRED'de görünen, sonradan düzeltilmiş geçmiş değerleri kullanmak yerine o tarihte gerçekten yayımlanmış değerleri kullansaydık ETH/BTC motorunun geçmiş değerlendirmesi değişir miydi?

Cevap: **Evet, bazı günlerde iç değerlendirme değişiyor; ancak yayımlanmış edge=70 uygunluk durumu hiçbir günde değişmiyor.**

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
```

İlk 23 replay gününde ALFRED'de mevcut yedi serinin en az biri eksiktir. Hangi serinin ve neden eksik olduğu ayrıca kapatılmadan FRED P1 alt aşaması tamamen kapanmış sayılmayacaktır.

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

## Karşılaştırma 2 — FRED'in sonradan düzeltilmiş değerlerinin etkisi

Bu karşılaştırmada yalnız ALFRED geçmişi bulunan seriler tutulur. Bir tarafta bugünkü FRED geçmiş değerleri, diğer tarafta geçmiş tarihte gerçekten yayımlanmış sürüm kullanılır. Böylece revision/yayın-zamanı etkisi SP500 boşluğundan ayrılır.

```text
Karşılaştırılan gün                     1420
Ortalama mutlak edge farkı              0.5398
En büyük mutlak edge farkı              14.41
Rejim değişen gün                       21
Yön işareti değişen gün                 5
Edge=70 uygunluğu değişen gün           0
```

Yorum:

- Ortalama edge etkisi küçük olsa da bazı tekil günlerde fark büyüktür; en büyük fark `14.41` puandır.
- 21 günde rejim sınıflandırması değişmiştir. Bu, FRED tarihsel sürüm farkının modelin iç yorumuna gerçekten etki ettiğini kanıtlar.
- 5 günde signed-edge yön işareti değişmiştir.
- Buna rağmen `edge=70` uygunluk durumu 1420 günün hiçbirinde değişmemiştir.

Bu nedenle geçmiş bilgi sızıntısı etkisi **mevcuttur**, ancak mevcut kanıt production edge threshold'u düşürmeyi veya LIVE'a geçmeyi desteklememektedir.

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

Bu toplam fark hem SP500 kaynak boşluğunu hem diğer FRED serilerinin geçmiş revision/yayın-zamanı farkını içerir.

## P1 açısından neyi kanıtladık?

1. Mevcut `macro.observations` tablosu strict geçmiş doğrulama için tek başına yeterli değildir.
2. FRED tarihsel revision'ları gerçekten vardır ve modelin geçmiş rejim/yön değerlendirmesini bazı günlerde değiştirmektedir.
3. ALFRED'de bulunan serilerle verification-only strict historical replay gerçek ortamda çalışmaktadır.
4. `SP500` ALFRED tarihsel geçmişi olmadığı için açık bir kaynak boşluğudur; bugünkü değer geçmişe uydurulmamıştır.
5. Mevcut 1420 replay gününde strict tarihsel makro kullanımı `edge=70` uygunluk durumunu hiçbir günde değiştirmemiştir.
6. Bu sonuç, daha önce görülen edge=70 sinyal kıtlığını FRED revision kaynaklı sahte bir sonuç olarak açıklamıyor.

## Henüz neyi kanıtlamadık?

Bu çalışma production ACTION backtest değildir.

Hâlâ açık olanlar:

- İlk 23 gündeki ALFRED-available seri eksikliğinin hangi seri/yayın başlangıcı nedeniyle oluştuğunun açıklanması.
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
