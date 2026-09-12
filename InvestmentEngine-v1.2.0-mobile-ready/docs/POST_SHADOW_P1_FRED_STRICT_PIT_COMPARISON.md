# Post-Shadow P1 — FRED Gerçek Tarihsel Veri Karşılaştırması

**Kanıt tarihi:** 2026-09-07 (Europe/Istanbul)  
**Model:** 1.2.0  
**Mode:** SHADOW  
**Realtime execution:** OFF  
**Kapsam:** ETH/BTC geçmiş yön çekirdeğinde FRED'in bugün görünen geçmişi ile geçmiş tarihte gerçekten yayımlanmış ALFRED sürümlerinin karşılaştırılması. Üretim motoru davranışı değiştirilmemiştir.

## 1. Bu çalışmada çözmeye çalıştığımız sorun

Geçmiş performansı ölçerken motorun geçmişte henüz bilmediği, sonradan düzeltilmiş bir makro değeri kullanması sonuçları olduğundan iyi veya farklı gösterebilir.

Bu nedenle P1 içinde şu soruyu doğruluyoruz:

> Motor 2023 veya 2025 tarihini yeniden hesaplarken bugünkü düzeltilmiş FRED değerini mi görüyor, yoksa o tarihte gerçekten yayımlanmış değeri mi görüyor?

Bu çalışma model ayarlarını değiştirmek için değil, mevcut v1.2.0 geçmiş doğrulamasının ne kadar güvenilir olduğunu ölçmek için yapılmaktadır.

## 2. Gerçek ortam doğrulama durumu

Son kullanıcı koşusunda:

```text
FRED PIT odaklı testler                 10 passed
Tüm Python testleri                     64 passed
Release check                           OK
Doğrulama stderr                        BOŞ
Sonuç durumu                            VERIFICATION_COMPLETE_WITH_SOURCE_GAP
DB'ye doğrulama kaydı yazıldı mı?       HAYIR
Otomatik parametre değişikliği          HAYIR
```

Gerçek FRED/ALFRED karşılaştırma komutu başarıyla tamamlanmıştır.

## 3. Veri kaynağı durumu

Yapılandırılmış sekiz FRED serisinden yedisi ALFRED üzerinden tarihsel sürümleriyle doğrulanabilmektedir.

`SP500` için FRED API serinin ALFRED'de bulunmadığını açıkça bildirmektedir. Bu nedenle strict geçmiş doğrulamada bugünkü SP500 değeri geçmişe uydurulmamış, tarihsel olarak kanıtlanamayan kaynak kabul edilmiştir.

Bu yüzden tüm sekiz serinin aynı anda strict tarihsel kapsaması doğal olarak sıfırdır. Asıl tarihsel karşılaştırma, ALFRED geçmişi bulunan yedi seri üzerinde ayrıca yapılır.

## 4. İlk 23 gün neden eksik?

ALFRED geçmişi bulunan yedi seri için toplam replay günü `1420`dir.

```text
Tam tarihsel veri bulunan gün          1397
Tam kapsama oranı                      %98.3803
İlk tam gün                            2022-11-10
Son tam gün                            2026-09-06
Eksik gün                              23
```

Eksik 23 günün tamamı:

```text
2022-10-18 ... 2022-11-09
missing_series = STLFSI4
```

Resmî ALFRED kaydı `STLFSI4` serisinin ilk yayımlanma tarihini `2022-11-10` olarak göstermektedir. Bu nedenle bu 23 günlük eksiklik veri çekme hatası değildir; o tarihlerde bugün kullandığımız `STLFSI4` serisi henüz yayımlanmamıştı.

Önceki `STLFSI3` serisini sessizce yerine koymak doğru değildir. Böyle bir ikame, veri kaynağı/model tanımını değiştirir ve ayrı model kararı gerektirir. Mevcut v1.2.0 doğrulamasında bu 23 gün tam-kapsama kanıtından çıkarılır.

## 5. SP500 tarihsel kaynak boşluğunun etkisi

Bugünkü FRED geçmişi korunup yalnız ALFRED geçmişi olmayan `SP500` eksik kabul edildiğinde:

```text
Karşılaştırılan gün                     1420
Ortalama mutlak edge farkı              0.5475
En büyük mutlak edge farkı              1.42
Rejim değişen gün                       0
Yön işareti değişen gün                 14
Edge=70 uygunluğu değişen gün           0
```

Yorum:

- SP500 kaynak boşluğu edge puanında küçük kaymalar yaratıyor.
- Rejim sınıflandırmasını değiştirmiyor.
- Bazı çok zayıf/dengeye yakın günlerde yön işareti değişebiliyor.
- Buna rağmen hiçbir gün yayımlanmış `edge=70` uygunluk sınırını geçip çıkmıyor veya altına düşmüyor.

Dolayısıyla SP500 kaynak boşluğu, mevcut edge=70 sinyal kıtlığını açıklamıyor.

## 6. Temiz FRED tarihsel sürüm karşılaştırması — 1397 gün

Gerçek revision/yayın-zamanı etkisini ölçerken ilk 23 eksik gün çıkarılmıştır. Karşılaştırma yalnız ALFRED geçmişi bulunan yedi serinin de o tarihte mevcut olduğu `1397` gün üzerinde yapılmıştır.

```text
Karşılaştırılan gün                     1397
İlk gün                                 2022-11-10
Son gün                                 2026-09-06
Ortalama mutlak edge farkı              0.5222834646
En büyük mutlak edge farkı              14.27
Rejim değişen gün                       19
Yön işareti değişen gün                 5
Edge=70 uygunluğu değişen gün           0
```

Bu sonuç iki şeyi aynı anda gösterir:

1. FRED tarihsel sürüm farkı gerçektir; bazı günlerde motorun iç puanını ve rejim yorumunu değiştirmektedir.
2. Buna rağmen yayımlanmış `edge=70` uygunluk sonucu tam kapsamalı 1397 günün hiçbirinde değişmemektedir.

En büyük farkların önemli örnekleri:

```text
2025-04-04   edge 30.75 -> 16.48   RISK_OFF -> NEUTRAL
2025-04-05   edge 30.96 -> 16.82   RISK_OFF -> NEUTRAL
2025-04-06   edge 34.07 -> 20.28   RISK_OFF -> NEUTRAL
2025-04-07   edge 36.06 -> 22.69   RISK_OFF -> NEUTRAL
2025-04-08   edge 38.22 -> 25.94   RISK_OFF -> NEUTRAL
2025-04-21   edge 20.12 -> 31.83   NEUTRAL  -> RISK_OFF
2023-03-22   edge 38.38 -> 45.58   NEUTRAL  -> RISK_ON_TREND
```

Bu örneklerin tamamı edge=70 sınırının belirgin biçimde altındadır. Büyük görünen `14.27` puanlık fark bile bir ACTION uygunluğu üretmemektedir.

## 7. 1420 günlük ham karşılaştırma neden ayrı tutuluyor?

İlk koşuda ALFRED geçmişi bulunan seriler için tüm 1420 gün karşılaştırılmıştı:

```text
Ortalama mutlak edge farkı              0.5398
En büyük mutlak edge farkı              14.41
Rejim değişen gün                       21
Yön işareti değişen gün                 5
Edge=70 uygunluğu değişen gün           0
```

Ancak ilk 23 günde `STLFSI4` henüz yayımlanmadığı için bu sayıların tamamını "saf revision etkisi" diye adlandırmak doğru değildir. Bu yüzden karar kanıtı olarak 1397 günlük tam-kapsama karşılaştırması kullanılır; 1420 günlük sonuç yalnız tanısal bilgi olarak korunur.

## 8. Walk-forward sonucu nasıl yorumlanmalı?

Son gerçek ortam koşusunda ortak kanıt sınıflandırması başarıyla çalışmıştır.

```text
current_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  selection_status         LIMITED_SIGNAL_COUNT
  observations             1420
  folds                    12
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

comparable_current_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  selection_status         LIMITED_SIGNAL_COUNT
  observations             1420
  folds                    12
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

strict_walk_forward
  evidence_status          LIMITED_OOS_SIGNAL_COUNT
  selection_status         OK
  observations             1420
  folds                    12
  edge70_signals           0
  selected_candidate_folds 7
  selected_oos_signals     1

comparable_complete_coverage_walk_forward
  evidence_status          LIMITED_TRAIN_SIGNAL_COUNT
  selection_status         LIMITED_SIGNAL_COUNT
  observations             1397
  folds                    12
  edge70_signals           0
  selected_candidate_folds 0
  selected_oos_signals     0

strict_complete_coverage_walk_forward
  evidence_status          LIMITED_OOS_SIGNAL_COUNT
  selection_status         LIMITED_SIGNAL_COUNT
  observations             1397
  folds                    12
  edge70_signals           0
  selected_candidate_folds 7
  selected_oos_signals     0
```

Burada karar için esas alınan satır `strict_complete_coverage_walk_forward` sonucudur; çünkü bu satır yalnız yedi ALFRED serisinin de tarihsel olarak mevcut olduğu 1397 günü kullanır.

Önemli yorumlar:

- `edge70_signals = 0`: yayımlanmış v1.2.0 edge=70 ayarı tarihsel sürümler doğru kullanıldığında da bağımsız test sinyali üretmemektedir.
- `selected_candidate_folds = 7`: daha düşük keşif eşikleri bazı eğitim pencerelerinde aday seçmeye yetecek kadar örnek üretmiştir.
- `selected_oos_signals = 0`: bu adaylar tam-kapsamalı bağımsız test dönemlerinde sinyal üretmemiştir.
- `evidence_status = LIMITED_OOS_SIGNAL_COUNT`: model ayarı değiştirmeye yetecek bağımsız kanıt yoktur.
- 1420 günlük strict koşudaki tek OOS sinyal, tam-kapsama dışındaki 23 günlük dönemin dahil olduğu ham karşılaştırmadadır; karar kanıtı olarak kullanılmaz.

Dolayısıyla `selection_status=OK` veya `selected_candidate_folds>0`, tek başına “model doğrulandı” anlamına gelmez.

## 9. P1 açısından neyi kanıtladık?

1. Mevcut `macro.observations` tablosu strict tarihsel FRED doğrulaması için tek başına yeterli değildir.
2. FRED tarihsel revision'ları gerçekten vardır.
3. Revision'lar bazı günlerde edge puanı ve rejim yorumunu değiştirir.
4. `SP500` ALFRED geçmişi olmayan açık bir tarihsel kaynak boşluğudur.
5. `STLFSI4` için 2022-10-18..2022-11-09 eksikliği collector hatası değil, serinin henüz yayımlanmamış olmasıdır.
6. Tam kapsamalı 1397 günde FRED tarihsel sürüm farkı `edge=70` uygunluğunu hiçbir gün değiştirmemiştir.
7. Tam kapsamalı strict walk-forward'da yayımlanmış `edge=70` için OOS sinyal sayısı `0`dır.
8. Daha düşük keşif eşiklerinde bile tam-kapsamalı bağımsız test sinyali `0`dır.
9. Dolayısıyla mevcut edge=70 sinyal kıtlığı FRED revision etkisiyle açıklanamamaktadır.
10. Bu kanıt threshold düşürmeyi veya LIVE'a geçmeyi desteklememektedir.

## 10. FRED strict-PIT alt aşaması kararı

```text
Verification implementation     VERIFIED
Real ALFRED fetch               VERIFIED
Source-gap handling             VERIFIED
Complete-coverage separation    VERIFIED
Evidence classification         VERIFIED IN REAL ENVIRONMENT
FRED strict-PIT sub-stage       CLOSED
Model change                    NONE
Threshold change                NONE
LIVE impact                     NONE / NO-GO unchanged
```

Bu alt aşama, FRED tarihsel sürüm etkisinin P1 kapsamında ölçülmesi açısından kapatılmıştır.

Bu kapanış, üretim `macro.observations` yaşam döngüsü veya retention/dedup tasarımını otomatik kapatmaz. O başlık P2 veri yaşam döngüsü çalışması olarak ayrıca ele alınır.

## 11. Sonraki P1 sorunu

FRED tarafı kapandıktan sonra P1'in sıradaki ana sorusu şudur:

> Geçmiş replay ile üretimde çalışan gerçek karar zinciri aynı girdiyi gördüğünde aynı factor, state ve ACTION davranışını üretiyor mu?

Bu nedenle sıradaki çalışma production-vs-replay parity'dir. Özellikle:

- üretim factor/quality/confidence kapıları ile replay arasındaki fark,
- aynı piyasa `as_of` tarihindeki tekrar scheduler koşularının nasıl ele alınacağı,
- persistent K1/K2 state,
- reversal/reset davranışı,
- `ACTION` ile `action_event` ayrımı,
- derivatives/event geçmişi eksik olduğunda karşılaştırma sınırları

ölçülecektir.

## 12. Karar etkisi

Bu çalışma şunları **değiştirmez**:

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
