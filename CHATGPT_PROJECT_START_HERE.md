# BTC_ETH_URA_10YIL — Yeni Sohbet Buradan Başlasın

Bu dosya ChatGPT projesinde veya repo üzerinde açılan yeni bir sohbetin başlangıç noktasıdır.

## Zorunlu okuma sırası

### Python / Engine reposu

1. `InvestmentEngine-v1.2.0-mobile-ready/docs/PROJECT_MEMORY_BANK.md`
2. `InvestmentEngine-v1.2.0-mobile-ready/docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
3. `InvestmentEngine-v1.2.0-mobile-ready/docs/SESSION_HANDOFF.md`
4. Değiştirilecek konuya göre eski teknik belge ve gerçek kod

### Quasar reposu

1. `docs/PROJECT_MEMORY_BANK.md`
2. `docs/SIGNAL_ENGINE_DECISION_CONTRACT.md`
3. `docs/SESSION_HANDOFF.md`
4. Değiştirilecek sayfa/store/service ve ilgili teknik belge

Ortak üç bağlam belgesi iki repoda aynı tutulur.

## Yeni sohbete yazılacak kısa başlangıç mesajı

```text
BTC_ETH_URA_10YIL projesinde bağlamı devral.
Önce CHATGPT_PROJECT_START_HERE.md, PROJECT_MEMORY_BANK.md,
SIGNAL_ENGINE_DECISION_CONTRACT.md ve SESSION_HANDOFF.md dosyalarını tamamen oku.
RELEASED/APPROVED/PROPOSED/OPEN ayrımını koru.
Sonra aktif branch, son commit ve çalışma ağacını doğrula.
Önceki oturumun kaldığı yerden, aynı amaç ve güvenlik sınırlarıyla devam et.
Bu oturum proje durumunu değiştirirse bitmeden önce handoff ve ilgili kalıcı
bağlam belgesini güncelle.
```

## ChatGPT Project Instructions için kalıcı metin

BTC_ETH_URA_10YIL içindeki her yeni sohbet:

1. Önce bu başlangıç dosyası ile üç bağlam belgesini okur.
2. Sinyal önerisini released kod davranışı saymaz; durum etiketlerini korur.
3. Python'un global/portföyden bağımsız, Quasar'ın seçili hesap bazlı olduğunu korur.
4. Otomatik emir, otomatik LIVE ve otomatik threshold/weight değişikliği yapmaz.
5. Yeni görev sonucunu kanıtlanmış saymadan önce scheduler/provider/freshness/snapshot/health/job-audit tutarlılığını kontrol eder.
6. Proje durumu değiştiyse oturum sonunda `SESSION_HANDOFF.md` dosyasını; kalıcı karar değiştiyse memory bank veya contract'ı günceller.
7. API key, parola, bot token, Chat ID ve service-role secret'ı belgelere yazmaz.

## Süreklilik gerçeği

- Aynı ChatGPT projesindeki sohbetler proje Sources ve Project Instructions bağlamını paylaşabilir.
- Bir GitHub/repo dosyasının varlığı, normal ChatGPT sohbetinin onu kendiliğinden mutlaka okuyacağı anlamına gelmez; bu başlangıç dosyası ve üç bağlam belgesi Project Sources/connected source içinde erişilebilir olmalıdır.
- Codex repo oturumlarında kök `AGENTS.md` otomatik başlangıç talimatıdır.
- Chat memory yardımcıdır; bağlayıcı proje kararlarının tek kaynağı değildir.
- Her sohbetin tüm metnini kopyalamak yerine doğrulanmış karar ve ilerleme handoff belgelerine işlenir.

## Kaynak yenileme kuralı

Eğer ChatGPT Project Sources'a dosyalar statik yüklenmişse repo güncellendiğinde eski yükleme otomatik güncellenmiş kabul edilmez; güncel dosya yeniden yüklenir. GitHub/bağlı kaynak kullanılıyorsa yeni sohbet yine bu dosya yollarını açıkça okuyarak branch ve commit'i doğrular.

## Değişiklik öncesi kontrol

```text
git status
git branch --show-current
git log -1 --oneline
```

Kullanıcıya ait beklenmeyen değişiklik varsa üzerine yazılmaz.

## Oturum bitmeden

- Ne tamamlandı?
- Ne doğrulandı?
- Hangi karar kesinleşti?
- Hangi öneri hâlâ onay bekliyor?
- Branch/commit nedir?
- Bir sonraki iş veya Shadow checkpoint hangisidir?

Bu altı sorunun yanıtı `SESSION_HANDOFF.md` içinde güncel olmalıdır.
