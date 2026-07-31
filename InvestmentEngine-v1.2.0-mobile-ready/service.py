"""Development-only service entry point.

Production uses the single-file InvestmentEngine.exe --service mode. This file
is kept so source checkouts can still host/test the pywin32 service class.
"""
from __future__ import annotations

import win32serviceutil

from app.windows_service import RosaInvestmentEngineService

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(RosaInvestmentEngineService)
