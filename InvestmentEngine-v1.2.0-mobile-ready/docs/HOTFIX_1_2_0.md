# v1.2.0 — Model Validation Milestone

- Kullanıcının düzelttiği CLI wrapper dosyaları gerçek satır sonlarıyla release'e alındı.
- `--validate-model` eklendi.
- ETH/BTC leakage-resistant directional core replay eklendi.
- Train/holdout exploratory edge-threshold calibration raporu eklendi; otomatik apply yok.
- Shadow -> LIVE readiness gate eklendi.
- Validation audit ve public snapshot tabloları eklendi.
- Kararlara `model_version` provenance eklendi.
- Monthly audit artık realized performance yanında validation çalıştırıyor.
- URA full PIT backtest, yeterli point-in-time holdings/breadth/event history birikene kadar bilinçli `NOT_READY`.
