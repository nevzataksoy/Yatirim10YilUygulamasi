begin;
insert into system.data_sources(code,category,source_url,expected_interval_seconds,stale_after_seconds,required,notes) values
('COINBASE_DAILY','price','https://api.exchange.coinbase.com/products/{product_id}/candles',86400,172800,true,'BTC-USD ve ETH-USD birincil günlük kaynak'),
('BITSTAMP_DAILY','price','https://www.bitstamp.net/api/v2/ohlc/{market_symbol}/',86400,172800,true,'Coinbase hata durumunda aynı anda iki crypto için failover'),
('ALPHA_URA','price','https://www.alphavantage.co/query',86400,259200,true,'URA günlük/haftalık/aylık'),
('DERIBIT','derivatives','https://www.deribit.com/api/v2',3600,10800,false,'AUTO modunda birincil derivatives provider; erişilemezse OKX fallback'),
('OKX','derivatives','https://www.okx.com/api/v5',3600,10800,false,'Deribit erişilemezse BTC/ETH aynı venue olacak şekilde public OI/funding/mark/index fallback'),
('FRED','macro','https://api.stlouisfed.org/fred/series/observations',21600,172800,true,'Makro zaman serileri'),
('SEC','events','https://data.sec.gov/submissions/',3600,10800,false,'Yapılandırılmış resmi filing olayları'),
('TCMB','fx','https://www.tcmb.gov.tr/kurlar/',86400,259200,false,'USD/TRY referans')
on conflict(code) do update set source_url=excluded.source_url,notes=excluded.notes;

insert into model.parameters(system,parameter_key,value_numeric,description) values
('ALL','min_data_quality',80,'Yeni aksiyon için minimum veri kalitesi'),
('ALL','min_action_edge',70,'Yeni aksiyon için minimum edge'),
('ALL','min_action_confidence',70,'Yeni aksiyon için minimum confidence'),
('ALL','strong_action_edge',80,'Kademe 2 için güçlü edge'),
('ALL','strong_action_confidence',80,'Kademe 2 için güçlü confidence'),
('ALL','regime_reset_edge',45,'Aktif rejimin zayıf kabul edildiği edge'),
('ALL','regime_reset_days',5,'Rejim reset için ardışık zayıf gün'),
('ALL','base_tranche_pct',0.25,'Normal volatilitede baz kademe'),
('ALL','max_regime_pct',0.50,'Aynı rejimde toplam maksimum dönüşüm'),
('ALL','late_entry_max_age_days',5,'Yeni trend dönüşü maksimum yaşı')
on conflict(system,parameter_key) do nothing;
commit;
