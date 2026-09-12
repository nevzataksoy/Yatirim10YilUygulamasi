# POST_SHADOW Build Warning RCA Closure

Tarih: 2026-09-11

Branch: `agent/portfolio-audit-reset`

Bu belge Oturum16 sırasında incelenen iki non-blocking warning (engelleyici olmayan uyarı) için RCA (root cause analysis / kök neden analizi) kapanış kanıtını kaydeder.

## 1. Kapsam

İncelenen warning ailesi:

```text
pytest cache/temp cleanup      WinError 183 / WinError 5
PyInstaller hidden import      "sip" not found
```

Amaç warning'leri rastgele patch ile susturmak değil, gerçek kök nedeni kanıtlamak ve runtime/build riski olup olmadığını sınıflandırmaktı.

Model semantiği, scheduler cadence, threshold, factor weight, K1/K2, reset/reversal/sizing ve SHADOW/LIVE durumu değiştirilmedi.

## 2. Pytest WinError 183 / WinError 5 RCA

### 2.1 Yeniden üretim

Normal kullanıcı PowerShell altında proje `.venv` Python'u ile tam test çalıştırıldı:

```text
PYTHON_EXE=D:\wamp64\www\Yatirim10YilUygulamasi\InvestmentEngine-v1.2.0-mobile-ready\.venv\Scripts\python.exe
PYTEST=8.4.2
TEMPFILE_ROOT=C:\Users\ROOT\AppData\Local\Temp

94 passed, 1 warning
PYTEST_EXIT=0
```

Warning kanıtı:

```text
PytestCacheWarning: could not create cache path
...\.pytest_cache\v\cache\nodeids
[WinError 183] Halen varolan bir dosya oluşturulamaz
```

Ayrıca pytest exit cleanup sırasında:

```text
PermissionError: [WinError 5] Erişim engellendi:
C:\Users\ROOT\AppData\Local\Temp\pytest-of-ROOT\pytest-current
```

### 2.2 Sahiplik ve ACL kanıtı

Normal kullanıcı ile okunamayan eski pytest nesneleri Administrator PowerShell ile incelendi.

Kanıt:

```text
.pytest_cache                         OWNER=BUILTIN\Administrators
.pytest_cache\v                       OWNER=BUILTIN\Administrators
.pytest_cache\v\cache                 OWNER=BUILTIN\Administrators

pytest-116                            OWNER=BUILTIN\Administrators
pytest-117                            OWNER=BUILTIN\Administrators
pytest-118                            OWNER=BUILTIN\Administrators
pytest-current                        OWNER=BUILTIN\Administrators
```

`pytest-current` ayrıca bir symbolic link (sembolik bağlantı) idi:

```text
ATTRIBUTES=Directory, ReparsePoint
LINK_TYPE=SymbolicLink
TARGET=C:\Users\ROOT\AppData\Local\Temp\pytest-of-ROOT\pytest-118
OWNER=BUILTIN\Administrators
```

Aynı ortamda normal kullanıcıyla oluşturulan yeni temp dizinleri ise:

```text
pytest-119 OWNER=DESKTOP-C7U2FG0\ROOT
pytest-120 OWNER=DESKTOP-C7U2FG0\ROOT
```

Bu karşılaştırma kök nedeni doğrudan doğruladı: eski pytest/cache/temp nesneleri geçmiş elevated (yükseltilmiş / Administrator) çalıştırmalardan kalmıştı. Güncel normal-user pytest bu nesneleri güncelleyemiyor veya silemiyordu.

### 2.3 Güvenli cleanup ve doğrulama

Yalnız pytest tarafından üretilen eski `.pytest_cache` ve `%TEMP%\pytest-of-ROOT` kalıntıları Administrator PowerShell ile temizlendi.

Cleanup sonrası:

```text
PROJECT_CACHE_EXISTS=False
PYTEST_ROOT_EXISTS=False
```

Ardından normal kullanıcı PowerShell ile tekrar tam test çalıştırıldı:

```text
94 passed in 2.93s
PYTEST_EXIT=0
CACHE_OWNER=DESKTOP-C7U2FG0\ROOT
pytest-0 | DESKTOP-C7U2FG0\ROOT | Directory
```

Warning summary oluşmadı; `WinError 183` ve `WinError 5` tekrar etmedi.

Git status temiz kaldı.

### 2.4 Pytest final sınıflandırması

```text
Root cause                 historical elevated pytest/cache/temp ownership
Current normal-user flow   healthy
Code defect                NO
pytest.ini defect           NO
Test failure               NO
Patch required             NO
Status                     CLOSED / VERIFIED
```

## 3. PyInstaller `"sip" not found` RCA

### 3.1 Ortam kanıtı

Normal kullanıcı `.venv` ortamında:

```text
PYTHON=3.14.0
PYINSTALLER=6.21.0
PYQT5=5.15.11
PYQT5_SIP_DIST=NOT_INSTALLED
TOPLEVEL_SIP_DIST=NOT_INSTALLED
HOOKS_CONTRIB=2026.6
SPEC_sip=None
```

Buna karşılık gerçek kullanılan private PyQt5 SIP modülü mevcut ve yüklenebilir:

```text
SPEC_PyQt5.sip=ModuleSpec(...)
origin=...\.venv\Lib\site-packages\PyQt5\sip.cp314-win_amd64.pyd

PYQT5_SIP_FILES=sip.cp314-win_amd64.pyd,sip.pyi
```

Dolayısıyla `PYQT5_SIP_DIST=NOT_INSTALLED` ayrı bir distribution paketinin kurulu olmadığını gösterir; runtime SIP modülünün eksik olduğunu göstermez. `PyQt5.sip` doğrudan PyQt5 paketinin içinde mevcuttur.

### 3.2 PyInstaller hook kanıtı

Kurulu PyInstaller 6.21.0 `hook-PyQt5.py` dosyası şu iki hidden import adayını birlikte tanımlar:

```text
# PyQt5.10 and earlier uses sip in an separate package;
'sip',
# PyQt5.11 and later provides SIP in a private package. Support both.
'PyQt5.sip',
```

Bu davranış eski ve yeni PyQt5 sürümlerini aynı hook ile desteklemek içindir.

Mevcut PyQt5 5.15.11 ortamında:

```text
top-level sip    yok
PyQt5.sip        var
```

Bu nedenle PyInstaller'ın `"sip" not found` uyarısı eski PyQt5 uyumluluk adayı için oluşur; kullanılan `PyQt5.sip` bileşeni eksik değildir.

### 3.3 Build/runtime bağlamı

Önceki kapanış kanıtında aynı release hattı için:

```text
PyInstaller 6.21.0 OneDir build   PASS
Inno Setup compile                PASS
installed EXE hash match          PASS
Windows Service                   Running / Automatic
service runtime continuity        VERIFIED
```

Dolayısıyla warning build veya runtime'ı düşüren bir eksiklik olarak gözlenmedi.

### 3.4 PyInstaller final sınıflandırması

```text
Root cause                 PyInstaller PyQt5 backward-compatibility hook
Missing required runtime   NO
PyQt5.sip                   PRESENT / IMPORTABLE
Top-level sip               NOT PRESENT / NOT REQUIRED for PyQt5 5.15.11
requirements patch          NO
--hidden-import sip patch   NO
Random warning suppression  NO
Status                     CLOSED / VERIFIED / NON-BLOCKING
```

## 4. Değişiklik kararı

Bu RCA sonucunda kaynak kodda veya build dependency sözleşmesinde değişiklik yapılmadı.

Özellikle yapılmayanlar:

```text
pytest.ini değişikliği                  YOK
pytest temp/cache redirect              YOK
requirements.txt sip ekleme             YOK
requirements-build.txt sip ekleme       YOK
build.bat --hidden-import sip ekleme     YOK
model/scheduler değişikliği             YOK
```

Gerekçe: iki warning'in de kök nedeni kanıtlandı ve warning'i susturmak için yeni dependency veya build davranışı eklemek gereksiz risk oluşturacaktı.

## 5. Oturum16 sonrası teknik durum

```text
pytest WinError 183 / WinError 5     CLOSED / VERIFIED
PyInstaller "sip" not found         CLOSED / VERIFIED / NON-BLOCKING
Code/config patch                    NONE
Model semantics change              NONE
SHADOW_READINESS                    READY (değişmedi)
LIVE                                NO-GO (değişmedi)
```

Forward observation (ileri yönlü gözlem) olarak kalan önceki başlıklar mevcut kapanışları yeniden açmaz:

1. 1 Ekim 2026 09:00 Europe/Istanbul ilk doğal `monthly_audit_job` lifecycle observation.
2. İkinci farklı post-0014 URA holdings tarihi oluştuğunda immutable raw snapshot current + previous zinciri gözlemi.
3. Historical PostgreSQL connection-pool timeout ailesi için GitHub Issue #2 production observation borcu.
