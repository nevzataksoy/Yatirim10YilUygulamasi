# Release Validation — v1.2.0

Kaynak ağacı üzerinde doğrulanan kontroller:

```text
python -m compileall -q app run.py service.py   PASS
pytest -q                                      34 passed
python scripts/release_check.py                PASS
```

Ek statik kontroller:

- `VERSION = 1.2.0`
- Inno Setup version = `1.2.0`
- PyInstaller version resource numeric tuple = `1.2.0.0`
- `InvestmentEngineCLI.cmd` / `.ps1` içinde literal `\\n` yok
- CLI argüman forwarding mevcut
- Migration `0007_v1_2_model_validation.sql` iki migration klasöründe mevcut
- Validation parametreleri model ayarlarını otomatik değiştirmiyor
- Release ağacında `settings`, `rosalock`, Google Sheets veya Apps Script artifact yok

Windows `InvestmentEngine.exe` / Inno Setup binary derlemesi bu Linux doğrulamasında yapılmadı; `build.bat` Windows development bilgisayarında çalıştırılmalıdır.
