# İşlem Düzenleme ve Revizyon Akışı

Portföy işlemleri finansal geçmişin bir parçasıdır. Bu nedenle bir işlem düzenlendiğinde eski kayıt fiziksel olarak değiştirilmez veya otomatik olarak silinmez.

## Temel İlke

Düzenleme işlemi yeni bir kayıt üretir.

Örnek:

```text
BUY #A   (ilk kayıt)
   ↓ düzenleme
BUY #B   (revizyon 2, #A kaydını supersede eder)
   ↓ tekrar düzenleme
BUY #C   (revizyon 3, #B kaydını supersede eder)
```

`#A` ve `#B` audit geçmişinde kalır. Ledger, Dashboard, Portföy ve Raporlar yalnız `#C` kaydını aktif işlem olarak kullanır.

## Metadata

Yeni revizyonda aşağıdaki alanlar `metadata` içinde tutulur:

- `revision_root_id`: revizyon zincirinin ilk işlem kimliği.
- `revision_number`: 1, 2, 3 ... revizyon numarası.
- `supersedes_transaction_id`: yeni kaydın yerine geçtiği bir önceki kayıt.
- `revised_at`: düzeltmenin oluşturulduğu zaman.
- `revision_reason`: kullanıcının girdiği düzeltme nedeni.

Bu yaklaşım mevcut `portfolio_transactions` şemasındaki `metadata` alanını kullanır; yeni transaction type gerektirmez.

## Hesaplama Kuralı

Aktif kayıtlar belirlenirken başka bir kayıt tarafından `supersedes_transaction_id` ile işaretlenmiş kayıtlar hesaplamadan çıkarılır.

```text
Tüm kayıtlar
  ↓
Supersede edilmiş revizyonları ayır
  ↓
Yalnız güncel revizyonlar
  ↓
Ledger / maliyet / K-Z / raporlar
```

Böylece bir alım Revizyon 1 ve Revizyon 2 olarak iki satır saklansa bile yatırım hesabına iki kez uygulanmaz.

## Düzenleme Öncesi Bakiye

Düzenleme ekranındaki `Önce / İşlem / Sonra` hesabı mevcut işlemi geçici olarak ledger'dan çıkarır. Yeni revizyon, işlem hiç yapılmamış durumdaki bakiye üzerine uygulanır.

Bu özellikle şu durumda gereklidir:

```text
100.000 TRY
- 24.000 TRY eski BUY
= 76.000 TRY mevcut bakiye
```

Eski BUY 20.000 TRY olarak düzeltilirken kullanılabilir bakiye `76.000` kabul edilmez. Eski kayıt önce çıkarılır:

```text
76.000 + 24.000 = 100.000 TRY revizyon baz bakiyesi
100.000 - 20.000 = 80.000 TRY yeni sonuç
```

## İşlem Geçmişi

Varsayılan görünüm yalnız aktif işlemleri gösterir.

`Revizyon Geçmişi` açıldığında eski kayıtlar da görülebilir. Eski revizyonlar `Eski Revizyon` olarak işaretlenir ve tekrar düzenlenemez; yalnız güncel revizyon düzenlenebilir.

## Silme

Supersede edilmiş eski revizyonlar audit kaydı olduğundan silinmez.

Güncel bir revizyon manuel olarak silinirse bir önceki revizyon yeniden aktif hale gelir. Bu davranış kullanıcıya silme onayında açıkça gösterilir.
