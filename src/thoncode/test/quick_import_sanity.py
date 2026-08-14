"""Quick syntax + import sanity check for upgraded plugin modules.

This script is a lightweight alternative to running the full unittest
suite when PowerShell ExecutionPolicy blocks the test runner. It verifies
that the modified modules compile and can be imported (it does not spin
up a Tk window so it works in headless environments).

Run with:
    python quick_import_sanity.py
"""

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)  # src/thoncode/
sys.path.insert(0, PROJECT)
sys.path.insert(0, os.path.join(PROJECT, "libs"))

# Don't launch Tk during sanity checks
os.environ.setdefault("THONCODE_HEADLESS", "1")

MODULES = [
    "libs.plugins.plugin_base",
    "libs.plugins.plugin_manager",
    "libs.plugins.plugin_api",
    "libs.plugins.plugin_marketplace",
]


def main() -> int:
    print("=" * 60)
    print("Quick import sanity check")
    print("=" * 60)
    failed = 0
    for mod in MODULES:
        try:
            __import__(mod)
            print("OK   ", mod)
        except Exception:
            failed += 1
            print("FAIL ", mod)
            traceback.print_exc()
    # Version constraint smoke test (no Tk required)
    try:
        from libs.plugins.plugin_manager import (
            _check_version_constraint,
            resolve_plugin_dirs,
        )
        assert _check_version_constraint("1.5.0", ">=1.0,<2.0")
        assert not _check_version_constraint("2.0.0", ">=1.0,<2.0")
        print("OK    plugin_manager version constraints")
    except Exception:
        failed += 1
        print("FAIL  plugin_manager version constraints")
        traceback.print_exc()
    # Marketplace helper smoke test
    try:
        from libs.plugins.plugin_marketplace import PluginMarketplace
        tmp_dir = os.path.join(os.path.dirname(HERE), "test", "_market_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        d = PluginMarketplace.user_writable_plugin_dir(tmp_dir)
        assert os.path.isdir(d)
        # Install -> uninstall cycle for single-file & package
        single = os.path.join(d, "x.py")
        with open(single, "w", encoding="utf-8") as f:
            f.write("#\n")
        assert PluginMarketplace.uninstall_plugin("x", d)
        assert not os.path.exists(single)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("OK    plugin_marketplace install/uninstall helpers")
    except Exception:
        failed += 1
        print("FAIL  plugin_marketplace install/uninstall helpers")
        traceback.print_exc()
    print("=" * 60)
    print(f"Result: {'PASS' if failed == 0 else 'FAIL'}  failures={failed}")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
