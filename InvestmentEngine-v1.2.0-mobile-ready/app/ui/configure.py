from __future__ import annotations

import sys
from PyQt5 import QtWidgets

from app.security.settings_store import SettingsStore, SettingsStoreError
from app.ui.settings_dialog import SettingsDialog, UnlockDialog


def configure_settings(force_unlock: bool = False) -> bool:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    store = SettingsStore()

    # Never decrypt existing settings before the administrator proves knowledge
    # of the settings password.
    if store.is_configured and force_unlock:
        unlock = UnlockDialog()
        if unlock.exec_() != QtWidgets.QDialog.Accepted:
            return False
        if not store.verify_settings_password(unlock.password):
            QtWidgets.QMessageBox.warning(None, "Ayar Kilidi", "Ayar şifresi yanlış.")
            return False

    try:
        current = store.load() if store.is_configured else None
    except SettingsStoreError as exc:
        QtWidgets.QMessageBox.critical(None, "Ayar Hatası", str(exc))
        return False

    dialog = SettingsDialog(store, current=current)
    return dialog.exec_() == QtWidgets.QDialog.Accepted
