# Telegram Bildirim Kurulumu

Investment Engine e-posta göndermez. Aksiyon bildirimleri Telegram Bot API üzerinden gider.

## 1. Bot oluştur

Telegram'da resmi `@BotFather` hesabını açın ve:

```text
/newbot
```

komutunu çalıştırın.

Bot adı ve `bot` ile biten kullanıcı adını belirleyin. BotFather'ın verdiği tokenı güvenli saklayın.

## 2. Sohbeti başlat

Oluşturduğunuz botu açıp:

```text
/start
```

veya herhangi bir mesaj gönderin.

## 3. Chat ID öğren

Tarayıcıda:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

adresini açın. Dönen JSON içinde:

```json
"chat": { "id": 123456789 }
```

alanındaki sayı Chat ID'dir.

## 4. Engine ayar ekranı

`InvestmentEngine.exe` dosyasını yönetici olarak açın.

**API & Telegram** sekmesine:

- Telegram Bot Token
- Telegram Chat ID

bilgilerini yazın ve `Telegram Test` düğmesine basın.

Başarılı durumda bot şu mesajı yollar:

```text
✅ Rosa Investment Engine Telegram testi başarılı.
```

## 5. Bildirim davranışı

- `shadow`: karar DB'ye yazılır, aksiyon Telegram bildirimi gönderilmez.
- `live`: yeni ACTION kararı Telegram'a gönderilir.
- `maintenance`: karar job'ları durdurulur, bakım/veri işleri kullanılabilir.

Aynı sistem/yön/tarih ACTION kararı tekrarlanırsa yeniden bildirim göndermemek için dedupe uygulanır.

## Güvenlik

Bot token:

- Supabase public tablolarına,
- mobil uygulamaya,
- Git repository'ye,
- log mesajlarına

konulmamalıdır. Yalnız DPAPI şifreli `settings` dosyasında tutulur.
