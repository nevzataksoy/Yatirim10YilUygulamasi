from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_onedir_build_and_installer_files_exist() -> None:
    build_path = ROOT / "build.bat"
    setup_path = ROOT / "investmentengine_setup.iss"
    ps1_path = ROOT / "scripts" / "build_exe.ps1"

    assert build_path.is_file()
    assert setup_path.is_file()
    assert ps1_path.is_file()

    build = build_path.read_text(encoding="utf-8")
    assert "--onedir" in build
    assert '--contents-directory "_internal"' in build
    assert "--noupx" in build
    assert "--onefile" not in build
    assert "dist\\InvestmentEngine\\InvestmentEngine.exe" in build
    assert "dist\\InvestmentEngine\\_internal" in build

    ps1 = ps1_path.read_text(encoding="utf-8")
    assert "--onedir" in ps1
    assert '--contents-directory "_internal"' in ps1
    assert "--noupx" in ps1
    assert "--onefile" not in ps1

    setup = setup_path.read_text(encoding="utf-8")
    assert 'Source: "dist\\InvestmentEngine\\{#MyAppExeName}"' in setup
    assert 'Source: "dist\\InvestmentEngine\\_internal\\*"' in setup
    assert 'DestDir: "{app}\\_internal"' in setup


def test_service_executable_path_remains_stable() -> None:
    setup = (ROOT / "investmentengine_setup.iss").read_text(encoding="utf-8")
    service = (ROOT / "app" / "windows_service.py").read_text(encoding="utf-8")

    assert '#define MyAppExeName "InvestmentEngine.exe"' in setup
    assert 'bin_path = f\'"{exe}" --service\'' in service
    assert "SERVICE_NAME = \"RosaInvestmentEngine\"" in service


def test_runtime_files_remain_outside_bundled_internal_tree() -> None:
    paths = (ROOT / "app" / "paths.py").read_text(encoding="utf-8")

    assert "CONFIG_DIR = APP_DIR" in paths
    assert 'SETTINGS_PATH = APP_DIR / "settings"' in paths
    assert 'LOCK_PATH = APP_DIR / "rosalock"' in paths
    assert 'LOG_DIR = APP_DIR / "logs"' in paths
    assert 'RUNTIME_DIR = APP_DIR / "runtime"' in paths
