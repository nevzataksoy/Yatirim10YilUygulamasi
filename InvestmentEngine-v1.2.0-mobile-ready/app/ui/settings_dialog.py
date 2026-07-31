from __future__ import annotations

import subprocess
import sys
import time

from PyQt5 import QtCore, QtWidgets

from app.collectors.alpha_vantage import AlphaVantageCollector
from app.collectors.fred import FredCollector
from app.collectors.globalx_ura import GlobalXUraHoldingsCollector
from app.collectors.sec import SecCollector
from app.database.db import DatabaseError, DatabaseService
from app.models import AppSettings, SettingsValidationError
from app.notifications.telegram import TelegramNotifier
from app.paths import APP_DIR
from app.security.settings_store import SettingsStore, SettingsStoreError


class UnlockDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Investment Engine — Ayar Kilidi")
        self.setModal(True)
        self.setMinimumWidth(380)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Ayar şifresini girin:"))
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Ayar Şifresi")
        self.password_input.returnPressed.connect(self.accept)
        layout.addWidget(self.password_input)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def password(self) -> str:
        return self.password_input.text()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        store: SettingsStore,
        current: AppSettings | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.current = current or AppSettings()
        self.saved_settings: AppSettings | None = None
        self.setWindowTitle("Rosa Investment Engine — İlk Kurulum / Ayarlar")
        self.setModal(True)
        self.resize(780, 720)

        root = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Supabase ve API sırları Windows DPAPI (LocalMachine) ile şifrelenir. "
            "settings ve rosalock dosyaları InvestmentEngine.exe ile aynı klasörde oluşturulur. "
            "Ayar şifresinin kendisi saklanmaz; rosalock yalnız PBKDF2 doğrulama kaydı içerir."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        path_label = QtWidgets.QLabel(f"Yerel ayar klasörü: {APP_DIR}")
        path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        root.addWidget(path_label)

        tabs = QtWidgets.QTabWidget()
        root.addWidget(tabs)
        tabs.addTab(self._build_database_tab(), "Supabase PostgreSQL")
        tabs.addTab(self._build_api_tab(), "API & Telegram")
        tabs.addTab(self._build_engine_tab(), "Motor")
        tabs.addTab(self._build_security_tab(), "Güvenlik")

        test_row = QtWidgets.QHBoxLayout()
        for text, slot in [
            ("Supabase Test", self._test_db),
            ("Alpha Vantage Test", self._test_alpha),
            ("FRED Test", self._test_fred),
            ("Global X Test", self._test_globalx),
            ("SEC Test", self._test_sec),
            ("Telegram Test", self._test_telegram),
        ]:
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(slot)
            test_row.addWidget(btn)
        root.addLayout(test_row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("Kaydet")
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText("İptal")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _line(self, value: str = "", password: bool = False) -> QtWidgets.QLineEdit:
        w = QtWidgets.QLineEdit(value)
        if password:
            w.setEchoMode(QtWidgets.QLineEdit.Password)
        return w

    def _build_database_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        c = self.current
        self.db_host = self._line(c.supabase_host)
        self.db_host.setPlaceholderText("aws-0-...pooler.supabase.com")
        self.db_port = QtWidgets.QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(c.supabase_port)
        self.db_name = self._line(c.supabase_database)
        self.db_user = self._line(c.supabase_user)
        self.db_password = self._line(c.supabase_password, True)
        self.db_sslmode = QtWidgets.QComboBox()
        self.db_sslmode.addItems(["require", "verify-full", "prefer"])
        self.db_sslmode.setCurrentText(c.supabase_sslmode)
        f.addRow("Host / Session Pooler:", self.db_host)
        f.addRow("Port:", self.db_port)
        f.addRow("Database:", self.db_name)
        f.addRow("Kullanıcı:", self.db_user)
        f.addRow("DB Parolası:", self.db_password)
        f.addRow("SSL Mode:", self.db_sslmode)
        note = QtWidgets.QLabel(
            "Mobil uygulama Supabase Project URL + public/publishable key bilgisini kendi ilk kurulumunda alacaktır. "
            "Windows Engine yalnız PostgreSQL bağlantısına ihtiyaç duyar."
        )
        note.setWordWrap(True)
        f.addRow(note)
        return w

    def _build_api_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        c = self.current
        self.alpha_key = self._line(c.alpha_vantage_api_key, True)
        self.fred_key = self._line(c.fred_api_key, True)
        self.telegram_token = self._line(c.telegram_bot_token, True)
        self.telegram_chat_id = self._line(c.telegram_chat_id)
        self.sec_user_agent = self._line(c.sec_user_agent)
        self.ura_holdings_url = self._line(c.ura_holdings_csv_url)
        self.ura_holdings_url.setPlaceholderText("Boş bırakılırsa resmi Global X sayfasından güncel CSV otomatik bulunur")
        f.addRow("Alpha Vantage API Key:", self.alpha_key)
        f.addRow("FRED API Key:", self.fred_key)
        f.addRow("Telegram Bot Token:", self.telegram_token)
        f.addRow("Telegram Chat ID:", self.telegram_chat_id)
        f.addRow("SEC User-Agent (ad/e-posta):", self.sec_user_agent)
        f.addRow("URA Holdings CSV URL (ops. override):", self.ura_holdings_url)
        return w

    def _build_engine_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        c = self.current
        self.engine_mode = QtWidgets.QComboBox()
        self.engine_mode.addItems(["shadow", "live", "maintenance"])
        self.engine_mode.setCurrentText(c.engine_mode)
        self.derivatives_provider = QtWidgets.QComboBox()
        self.derivatives_provider.addItem("Otomatik (Deribit → OKX)", "auto")
        self.derivatives_provider.addItem("Yalnız Deribit", "deribit")
        self.derivatives_provider.addItem("Yalnız OKX", "okx")
        provider_index = self.derivatives_provider.findData(c.derivatives_provider)
        self.derivatives_provider.setCurrentIndex(max(0, provider_index))
        self.realtime = QtWidgets.QCheckBox(
            "Aksiyon adayı oluştuğunda execution worker çalışsın"
        )
        self.realtime.setChecked(c.realtime_execution_enabled)
        self.realtime_minutes = QtWidgets.QSpinBox()
        self.realtime_minutes.setRange(5, 120)
        self.realtime_minutes.setValue(c.realtime_execution_minutes)
        self.realtime_minutes.setSuffix(" dk")
        self.min_quality = QtWidgets.QDoubleSpinBox()
        self.min_quality.setRange(0, 100)
        self.min_quality.setValue(c.min_data_quality)
        self.min_edge = QtWidgets.QDoubleSpinBox()
        self.min_edge.setRange(0, 100)
        self.min_edge.setValue(c.min_action_edge)
        self.min_conf = QtWidgets.QDoubleSpinBox()
        self.min_conf.setRange(0, 100)
        self.min_conf.setValue(c.min_action_confidence)
        self.strong_edge = QtWidgets.QDoubleSpinBox()
        self.strong_edge.setRange(0, 100)
        self.strong_edge.setValue(c.strong_action_edge)
        self.strong_conf = QtWidgets.QDoubleSpinBox()
        self.strong_conf.setRange(0, 100)
        self.strong_conf.setValue(c.strong_action_confidence)
        self.reset_edge = QtWidgets.QDoubleSpinBox()
        self.reset_edge.setRange(0, 100)
        self.reset_edge.setValue(c.regime_reset_edge)
        self.reset_days = QtWidgets.QSpinBox()
        self.reset_days.setRange(1, 30)
        self.reset_days.setValue(c.regime_reset_days)
        f.addRow("Çalışma modu:", self.engine_mode)
        f.addRow("Derivatives provider:", self.derivatives_provider)
        f.addRow("Realtime execution:", self.realtime)
        f.addRow("Execution penceresi:", self.realtime_minutes)
        f.addRow("Min. Data Quality:", self.min_quality)
        f.addRow("Min. Edge:", self.min_edge)
        f.addRow("Min. Confidence:", self.min_conf)
        f.addRow("Güçlü Edge:", self.strong_edge)
        f.addRow("Güçlü Confidence:", self.strong_conf)
        f.addRow("Rejim Reset Edge:", self.reset_edge)
        f.addRow("Rejim Reset Gün:", self.reset_days)
        return w

    def _build_security_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)
        self.settings_password = self._line("", True)
        self.settings_password_confirm = self._line("", True)
        f.addRow("Yeni Ayar Şifresi:", self.settings_password)
        f.addRow("Şifre Tekrar:", self.settings_password_confirm)
        note = QtWidgets.QLabel(
            "Şifre en az 10 karakter olmalıdır. Şifrenin kendisi hiçbir dosyaya yazılmaz. "
            "Servis yeniden başlarken parola sormaz; settings DPAPI LocalMachine ile korunur."
        )
        note.setWordWrap(True)
        f.addRow(note)
        return w

    def _build_settings(self, validate: bool = True) -> AppSettings:
        s = AppSettings(
            supabase_host=self.db_host.text().strip(),
            supabase_port=self.db_port.value(),
            supabase_database=self.db_name.text().strip(),
            supabase_user=self.db_user.text().strip(),
            supabase_password=self.db_password.text(),
            supabase_sslmode=self.db_sslmode.currentText(),
            alpha_vantage_api_key=self.alpha_key.text().strip(),
            fred_api_key=self.fred_key.text().strip(),
            telegram_bot_token=self.telegram_token.text().strip(),
            telegram_chat_id=self.telegram_chat_id.text().strip(),
            sec_user_agent=self.sec_user_agent.text().strip(),
            engine_mode=self.engine_mode.currentText(),
            derivatives_provider=self.derivatives_provider.currentData(),
            realtime_execution_enabled=self.realtime.isChecked(),
            realtime_execution_minutes=self.realtime_minutes.value(),
            min_data_quality=self.min_quality.value(),
            min_action_edge=self.min_edge.value(),
            min_action_confidence=self.min_conf.value(),
            strong_action_edge=self.strong_edge.value(),
            strong_action_confidence=self.strong_conf.value(),
            regime_reset_edge=self.reset_edge.value(),
            regime_reset_days=self.reset_days.value(),
            ura_holdings_csv_url=self.ura_holdings_url.text().strip(),
        )
        if validate:
            s.validate()
        return s

    def _run_test(self, title: str, fn) -> None:
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            fn()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, title, str(exc))
        else:
            QtWidgets.QMessageBox.information(self, title, "Bağlantı başarılı.")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _test_db(self) -> None:
        self._run_test(
            "Supabase Test",
            lambda: DatabaseService(self._build_settings(False)).test_connection(),
        )

    def _test_alpha(self) -> None:
        self._run_test(
            "Alpha Vantage Test",
            lambda: AlphaVantageCollector(self.alpha_key.text().strip()).fetch_daily("URA"),
        )

    def _test_fred(self) -> None:
        self._run_test(
            "FRED Test",
            lambda: FredCollector(self.fred_key.text().strip()).fetch_series("DGS10", limit=3),
        )

    def _test_globalx(self) -> None:
        self._run_test(
            "Global X URA Test",
            lambda: GlobalXUraHoldingsCollector().fetch(self.ura_holdings_url.text().strip()),
        )

    def _test_sec(self) -> None:
        self._run_test(
            "SEC Test",
            lambda: SecCollector(self.sec_user_agent.text().strip()).fetch_ticker_map(),
        )

    def _test_telegram(self) -> None:
        self._run_test(
            "Telegram Test",
            lambda: TelegramNotifier(
                self.telegram_token.text().strip(), self.telegram_chat_id.text().strip()
            ).send("✅ Rosa Investment Engine Telegram testi başarılı."),
        )

    @staticmethod
    def _restart_running_service() -> str:
        """Restart the installed service only when it was already RUNNING.

        First-install configuration happens before Inno registers the service, so
        this is a no-op there. A deliberately stopped service also remains stopped.
        """
        if sys.platform != "win32":
            return ""

        def query() -> str:
            cp=subprocess.run(["sc.exe","query","RosaInvestmentEngine"],capture_output=True,text=True,encoding="utf-8",errors="replace",check=False)
            if cp.returncode != 0:
                return "MISSING"
            text=(cp.stdout+"\n"+cp.stderr).upper()
            for state in ("RUNNING","STOPPED","START_PENDING","STOP_PENDING"):
                if state in text:
                    return state
            return "UNKNOWN"

        if query() != "RUNNING":
            return ""
        subprocess.run(["sc.exe","stop","RosaInvestmentEngine"],capture_output=True,check=False)
        deadline=time.monotonic()+30
        while time.monotonic()<deadline and query()!="STOPPED":
            time.sleep(0.5)
        cp=subprocess.run(["sc.exe","start","RosaInvestmentEngine"],capture_output=True,text=True,encoding="utf-8",errors="replace",check=False)
        if cp.returncode != 0:
            return "\n\nUYARI: Ayarlar kaydedildi fakat çalışan servis yeniden başlatılamadı. Servisi Windows Hizmetleri'nden yeniden başlatın."
        return "\n\nÇalışan RosaInvestmentEngine servisi yeni ayarlarla yeniden başlatıldı."

    def _save(self) -> None:
        password = self.settings_password.text()
        if password != self.settings_password_confirm.text():
            QtWidgets.QMessageBox.warning(self, "Şifre", "Ayar şifreleri eşleşmiyor.")
            return
        try:
            settings = self._build_settings(True)
            DatabaseService(settings).test_connection()
            self.store.save(settings, password)
        except (SettingsValidationError, DatabaseError, SettingsStoreError) as exc:
            QtWidgets.QMessageBox.warning(self, "Kaydetme Hatası", str(exc))
            return
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Kaydetme Hatası", str(exc))
            return
        self.saved_settings = settings
        service_note=self._restart_running_service()
        QtWidgets.QMessageBox.information(
            self,
            "Ayarlar",
            f"Ayarlar güvenli şekilde kaydedildi.\n\n{self.store.settings_path}\n{self.store.lock_path}{service_note}",
        )
        self.accept()
