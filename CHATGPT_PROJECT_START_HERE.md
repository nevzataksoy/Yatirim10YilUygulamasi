# BTC_ETH_URA_10YIL — Yeni Sohbet Buradan Başlasın

Bu dosya ChatGPT projesinde veya repo üzerinde açılan yeni bir sohbetin zorunlu başlangıç noktasıdır.

## 1. Zorunlu okuma sırası

### Python / Engine reposu

1. `CHATGPT_PROJECT_START_HERE.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
5. Python/Shadow işi varsa:
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `InvestmentEngine-v1.2.0-mobile-ready/docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek konuya göre gerçek kod, migration ve teknik belge.

### Quasar reposu

1. `CHATGPT_PROJECT_START_HERE.md`
2. `docs/PROJECT_MEMORY_BANK.md`
3. `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
4. `docs/SESSION_HANDOFF.md`
5. Python/Shadow bağlamı gerekiyorsa:
   - `docs/INVESTMENT_ENGINE_SHADOW_GOREV_TAKVIMI_2026-07-31.md`
   - `docs/SHADOW_CHECKPOINT_LOG.md`
6. Değiştirilecek page/component/store/service ve ilgili teknik belge.

Memory bank, signal contract, handoff, görev takvimi ve checkpoint logunun iki repodaki kopyaları senkron tutulur.

## 2. Yeni sohbete yazılacak başlangıç mesajı

```text
BTC_ETH_URA_10YIL projesinde bağlamı devral.
Önce CHATGPT_PROJECT_START_HERE.md, PROJECT_MEMORY_BANK.md,
SIGNAL_ENGINE_DECISION_CONTRACT.md ve SESSION_HANDOFF.md dosyalarını tamamen oku.
Python/Shadow işi ise görev takvimi ile SHADOW_CHECKPOINT_LOG.md dosyasını da oku.
RELEASED/APPROVED/PROPOSED/OPEN ayrımını koru.
Sonra iki repoda aktif branch ve güncel remote HEAD'i doğrula.
Önceki oturumun kaldığı yerden aynı amaç ve güvenlik sınırlarıyla devam et.
Aksiyon almadan önce kullanıcının son push'ını yeniden oku.
Proje durumu değişirse bitmeden önce handoff ve ilgili kalıcı bağlam dosyasını güncelle.
```

## 3. Değişmez proje sınırları

1. Python global ve portföyden bağımsızdır; seçili hesap bakiyesi okumaz.
2. Quasar gerçek işlemleri seçili portföy hesabında tutar.
3. Otomatik emir yoktur.
4. `READY`, LIVE değildir; LIVE manuel production review ister.
5. Validation sonucu threshold/weight/mode değerini otomatik değiştirmez.
6. `PROPOSED` veya `OPEN` madde kullanıcı onayı olmadan kodlanmaz.
7. API key, parola, bot token, Chat ID, DB password ve service-role secret belgelenmez.
8. Kullanıcıya ait beklenmeyen local/remote değişikliğin üzerine yazılmaz.

## 4. Remote-first pull/push çalışma kuralı

Kullanıcının istediği dönüşümlü çalışma modeli:

1. Asistan her aksiyondan önce remote branch'in son HEAD ve dosyalarını yeniden okur.
2. Asistan değişiklikleri feature/agent branch'e push eder.
3. Kullanıcı `git pull` yapar, testleri tamamlar ve gerekirse kendi değişikliğini push eder.
4. Asistan sonraki aksiyondan önce kullanıcının push'ını yeniden okur.
5. Aynı branch üzerinde eşzamanlı yazma yapılmaz.
6. Git hata çözümünde kullanıcıya bir seferde yalnız bir komut verilir; çıktı görülmeden sonraki komut verilmez.
7. Draft PR test ve doğrulamalar tamamlanmadan merge edilmez.

## 5. Güncel kısa durum

```text
Python model: v1.2.0
Mode: SHADOW
Realtime Execution: OFF
Görev 1: PASS
Görev 2: PASS
Sıradaki: Görev 3 — 01.08.2026 09:30 TRT
Quasar: tek kullanıcı + çoklu portföy, AppPopupSelect standardı,
append-only transaction revision ve account-scoped ledger.
Quasar manuel 100.000 TRY regression senaryosu henüz tamamlanmış sayılmıyor.
```

## 6. Değişiklik öncesi kontrol

Yerel repo kullanılıyorsa:

```text
git status
git branch --show-current
git log -1 --oneline
git fetch origin
```

Connector kullanılıyorsa aktif branch'in güncel HEAD'i ve değiştirilecek dosyanın son SHA'sı yeniden okunur.

## 7. Oturum kapanış protokolü

Oturum proje durumunu değiştirdiyse şu soruların yanıtı `SESSION_HANDOFF.md` içinde bulunmalıdır:

- Ne tamamlandı?
- Ne gerçekten doğrulandı?
- Hangi karar kesinleşti?
- Hangi öneri hâlâ onay bekliyor?
- Hangi branch/commit'e push edildi?
- Sıradaki Quasar testi veya Shadow checkpoint hangisi?

Kalıcı karar değiştiyse memory bank veya signal contract da aynı turda güncellenir. Ortak dosyalar iki repoda senkron tutulur.

## 8. ChatGPT Project Sources notu

Repo dosyasının varlığı normal sohbetin onu otomatik okuyacağını garanti etmez. Bu dosyalar Project Sources'a statik yüklendiyse repo güncellendiğinde yeniden yüklenmelidir. GitHub connected source kullanılıyorsa yeni sohbet yine dosya yollarını açıkça okuyup branch/HEAD doğrulaması yapmalıdır.
