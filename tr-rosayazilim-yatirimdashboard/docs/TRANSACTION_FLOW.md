# Portföy İşlem Akışı

Bu belge uygulamadaki finansal hareketlerin hangi işlem tipiyle kaydedileceğini ve kullanıcıdan hangi gerçek işlem verilerinin alınacağını tanımlar.

## Temel İlke

Portföye dışarıdan para girişi ile portföy içindeki varlık değişimleri birbirinden ayrılır.

- `CASH_IN`: Dışarıdan yatırım hesabına yeni sermaye girer.
- `BUY`: Mevcut TRY/USD nakit bakiyesi kullanılarak BTC/ETH/URA alınır.
- `CONVERSION`: Portföyde zaten bulunan bir varlık başka bir portföy varlığına dönüşür.
- `SELL`: BTC/ETH/URA satılır ve karşılığı portföy içinde TRY/USD nakit olarak kalır.
- `CASH_OUT`: Portföy nakdi yatırım hesabından dışarı çekilir.
- `OPENING`: Takibe başlanırken zaten mevcut olan varlıkların başlangıç bakiyesi ve maliyet bazıdır.

Bu ayrım sayesinde aylık yatırım bütçesi yalnız `CASH_IN` kayıtlarından, sermaye çıkışları ise `CASH_OUT` kayıtlarından raporlanabilir. Alım, satış ve dönüşüm yeni sermaye sayılmaz.

Her kullanıcı işlemi form açıldığında üretilen sabit bir transaction UUID'si taşır.
Ağ yanıtı belirsiz kalıp aynı form tekrar gönderilirse aynı UUID ikinci finansal kayıt
üretmez. Aynı UUID'nin farklı içerikle yeniden kullanılması sessizce kabul edilmez.
Store, insert öncesinde seçili hesabın effective işlem zincirini kronolojik replay
ederek negatif bakiye oluşmasını engeller. Dönüşüm tek satırda kaynak ve hedef bacağını
birlikte taşır; başlangıç portföyündeki birden fazla OPENING kaydı tek atomik bulk
insert olarak yazılır.

## Alım Girişi

Borsadaki eski bir alış işlemine baktığında genellikle şu bilgiler bulunur:

- alınan varlık,
- alınan miktar,
- ortalama/birim fiyat,
- işlem para birimi,
- tarih/saat,
- komisyon,
- platform.

Uygulamada kullanıcı:

1. Kaynak para birimini `TRY` veya `USD` seçer.
2. Alınan varlığı `BTC`, `ETH` veya `URA` seçer.
3. Alım miktarını girer.
4. Birim fiyatı kaynak para birimi cinsinden girer.
5. USD/TRY kurunu girer.

Toplam alım tutarı arka planda hesaplanır:

`toplam kaynak maliyeti = alım miktarı × birim fiyat`

USD karşılığı ve USD bazlı birim maliyet de otomatik üretilir. İstenirse güncel piyasa fiyatı forma otomatik doldurulabilir; geçmiş işlem girerken gerçek borsa işlem fiyatı esas alınır.

## Dönüşüm Girişi

Dönüşümde kullanıcı kaynak varlıktan ne kadar dönüştürdüğünü ve işlem paritesini girer.

Örnek: BTC → ETH

- kaynak miktar: `0.01 BTC`
- BTC/ETH paritesi: `1 BTC = 31.25 ETH`
- hesaplanan hedef: `0.3125 ETH`

Hedef miktar otomatik hesaplanır:

`hedef miktar = kaynak miktar × parite`

Borsa işlem detayında gerçekleşen miktar farklıysa kullanıcı hedef miktarı manuel düzeltebilir. `%25`, `%50`, `%75`, `%100` butonları mevcut kaynak bakiyeden hızlı miktar seçimi sağlar.

ETH → BTC işleminde aynı mantık ters yönde uygulanır:

- ETH/BTC paritesi girilir,
- kaynak ETH miktarı girilir,
- hedef BTC miktarı otomatik hesaplanır.

USD/TRY kuru her dönüşüm kaydında saklanır. TRY/USD bacağı olmayan kripto-kripto dönüşümlerde USD raporlama karşılığı piyasa snapshot'ından üretilir; maliyet bazının taşınması ise gerçek kaynak ve hedef miktarlara dayanır.

## Satış Girişi

Satış ekranı borsa işlem detayına göre çalışır:

1. Satılan varlık seçilir.
2. Satılan miktar girilir veya yüzde butonlarıyla seçilir.
3. Satış karşılığı `TRY` veya `USD` seçilir.
4. Birim/ortalama satış fiyatı girilir.
5. Satış tutarı otomatik hesaplanır.
6. Borsadaki gerçekleşen toplam farklıysa kullanıcı gerçekleşen satış tutarını manuel düzeltebilir.
7. USD/TRY, tarih/saat, platform ve komisyon kaydedilir.

Satış sonrası para portföy içinde TRY/USD nakit olarak kalır. Bankaya para çekilmedikçe `CASH_OUT` oluşmaz.

## Sermaye Giriş / Çıkış

`CASH_IN` ve `CASH_OUT` yalnız dış dünya ile yatırım portföyü arasındaki para hareketleridir.

Kullanıcı tutar, para birimi, USD/TRY kuru, tarih/saat, banka/borsa hesabı ve masrafı girer. Kayıttan önce özet ekranı gösterilir.

## Örnek 1: 10.000 TRY Havale Edip Doğrudan BTC Almak

1. Bankadan borsa hesabına 10.000 TRY havale edilir.
   - `CASH_IN`
   - target_asset: `TRY`
   - target_quantity: `10000`
   - USD/TRY: işlem anındaki kur
2. Borsada BTC alınır.
   - `BUY`
   - source_asset: `TRY`
   - target_asset: `BTC`
   - target_quantity: alınan BTC
   - entered_unit_price: borsadaki TRY/BTC birim fiyatı
   - source_quantity: arka planda `target_quantity × unit_price`

Sonuç: Yatırım bütçesi yalnız 10.000 TRY karşılığı kadar artar; TRY nakit azalır, BTC artar. BUY ikinci kez sermaye artırmaz.

## Örnek 2: 10.000 TRY Havale, USD Dönüşümü, Sonra BTC Alımı

1. `CASH_IN`: 10.000 TRY
2. `CONVERSION`: TRY → USD
3. `BUY`: USD → BTC

Bu akışta yalnız ilk adım yeni yatırım bütçesidir. Diğer iki hareket portföy içidir.

## Örnek 3: BTC'nin %50'sini ETH'ye Çevirmek

- `CONVERSION`
- source_asset: `BTC`
- source_quantity: `%50` butonu ile seçilebilir
- target_asset: `ETH`
- pair_rate: BTC/ETH işlem paritesi
- target_quantity: pariteden otomatik hesaplanır, gerçek işlem miktarıyla düzeltilebilir
- USD/TRY: işlem anındaki kur

Maliyet bazı kaynak varlıktan hedef varlığa taşınır. Yeni sermaye oluşmaz.

## Örnek 4: BTC Satıp Parayı Borsada Bırakmak

1. `SELL`: BTC → TRY veya BTC → USD
2. Portföyün BTC bakiyesi azalır, TRY/USD nakdi artar.

Bankaya para çekilmediyse `CASH_OUT` oluşturulmaz.

## Örnek 5: Borsadan Bankaya Para Çekmek

- Önce gerekiyorsa `SELL` ile varlık TRY/USD nakde çevrilir.
- Ardından `CASH_OUT` ile yatırım hesabından çıkan nakit kaydedilir.

## USD Normalizasyonu

Ledger maliyet bazını USD olarak normalize eder. Her işlemde `usd_try` saklanır. Kullanıcı arayüzündeki görüntüleme birimi (`USD`, `TRY`, `BTC`, `ETH`) yalnız sunum katmanıdır; muhasebe verisini değiştirmez.

Görüntüleme birimi SecureLS ile yerel olarak saklanır ve uygulama yenilendiğinde korunur.

## USDT

İlk sürümde USDT ayrı varlık olarak modellenmez. TRY ve USD nakit akışı yeterlidir. Böylece şema, RLS, ledger ve raporlama gereksiz stablecoin karmaşıklığından korunur.
