"""Exercise the installer in isolated XDG directories with a fake user service."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STOCK = Path(os.environ["REDOCK_STOCK_UI"]).resolve()


class RedockTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.home = Path(scratch.name)
        self.config = self.home / "config % $ space"
        self.state = self.home / "state"
        self.settings = self.config / "dms/settings.json"
        self.session = self.state / "dms/session.json"
        self.installation = self.config / "dms/redock"
        self.dropin = self.config / "systemd/user/dms.service.d/70-redock.conf"
        self.settings.parent.mkdir(parents=True)
        self.session.parent.mkdir(parents=True)
        self.env = {
            **os.environ,
            "XDG_CONFIG_HOME": str(self.config),
            "XDG_STATE_HOME": str(self.state),
            "FAKE_SERVICE_HOME": str(self.home),
            "PATH": f"{self.home}:{os.environ['PATH']}",
        }
        self.original = {"dockConfigs": [{"id": "dock", "enabled": False}], "userSetting": "keep"}
        self.settings.write_text(json.dumps(self.original))
        self.session.write_text('{"dockPins":{"dock":["sample-app"]},"userState":true}')
        self.write_executable("dms", """#!/bin/sh
if [ "$1" = version ]; then echo 'dms v2.1.0'; else printf '%s\n' "$@"; fi
""")
        self.write_executable("systemctl", """#!/bin/sh
set -eu
[ "$1" = --user ]
case "$2" in
  show)
    if [ "$4" = -p ] && [ "$5" = ExecStart ]; then
      printf '{ path=%s/dms ; argv[]=%s/dms run --session ; status=0/0 }\n' \
        "$FAKE_SERVICE_HOME" "$FAKE_SERVICE_HOME"
    fi ;;
  is-active)
    [ ! -f "$FAKE_SERVICE_HOME/inactive" ] || exit 3 ;;
  stop|daemon-reload) ;;
  start)
    if [ -f "$FAKE_SERVICE_HOME/fail-next-start" ]; then
      rm "$FAKE_SERVICE_HOME/fail-next-start"
      exit 1
    fi ;;
  *) exit 2 ;;
esac
""")

    def write_executable(self, name, content):
        path = self.home / name
        path.write_text(content)
        path.chmod(0o700)

    def redock(self, *args, ok=True):
        result = subprocess.run(
            [ROOT / "redock", *args], env=self.env, capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def install(self, *, ok=True):
        return self.redock("install", "--shell-dir", STOCK, ok=ok)

    def test_build_in_git_worktree(self):
        subprocess.run(["git", "init", "-q", self.home], check=True)
        destination = self.home / "built ui"
        self.redock("build", STOCK, destination)
        self.assertTrue((destination / "Modules/Dock/GlassDockFinish.qml").is_file())
        self.assertGreater((destination / "Shaders/qsb/redock.frag.qsb").stat().st_size, 0)
        self.assertFalse((STOCK / "Modules/Dock/GlassDockFinish.qml").exists())

    def test_install_uninstall_preserves_unrelated_state(self):
        self.install()
        self.assertTrue(self.dropin.is_file())
        self.assertIn("config %% $ space", self.dropin.read_text())
        current = json.loads(self.settings.read_text())
        self.assertEqual(current["dockConfigs"][0], self.original["dockConfigs"][0])
        self.assertEqual(current["dockConfigs"][1]["id"], "redock")
        self.assertEqual(current["userSetting"], "keep")
        state = json.loads(self.session.read_text())
        state["dockPins"]["redock"] = ["another-app"]
        self.session.write_text(json.dumps(state))
        self.redock("uninstall")
        self.assertFalse(self.dropin.exists())
        self.assertFalse(self.installation.exists())
        self.assertEqual(json.loads(self.settings.read_text()), self.original)
        self.assertEqual(json.loads(self.session.read_text()), {
            "dockPins": {"dock": ["sample-app"]}, "userState": True,
        })

    def test_uninstall_restores_implicit_default(self):
        self.settings.write_text('{"userSetting":"keep"}')
        self.install()
        self.redock("uninstall")
        self.assertEqual(json.loads(self.settings.read_text()), {"userSetting": "keep"})

    def test_refuses_bottom_bar(self):
        self.original["barConfigs"] = [{"id": "bottom", "position": 1}]
        self.settings.write_text(json.dumps(self.original))
        self.assertIn("bottom bar", self.install(ok=False).stderr)
        self.assertFalse(self.dropin.exists())
        self.assertFalse(self.installation.exists())
        self.assertEqual(json.loads(self.settings.read_text()), self.original)

    def test_refuses_inactive_service(self):
        (self.home / "inactive").touch()
        self.assertIn("Start the stock dms.service", self.install(ok=False).stderr)
        self.assertFalse(self.installation.exists())
        self.assertEqual(json.loads(self.settings.read_text()), self.original)

    def test_failed_start_restores_stock_service_and_settings(self):
        before = self.settings.read_bytes()
        (self.home / "fail-next-start").touch()
        self.install(ok=False)
        self.assertFalse(self.dropin.exists())
        self.assertFalse(self.installation.exists())
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertFalse((self.home / "fail-next-start").exists())

    def test_launcher_falls_back_after_binary_change(self):
        self.install()
        launcher = self.installation / "launch.sh"
        dms = self.home / "dms"
        command = [launcher, dms, "run", "--session"]
        output = subprocess.check_output(command, text=True)
        self.assertEqual(output.splitlines(), [
            "--config", str(self.installation / "ui"), "run", "--session",
        ])
        with dms.open("a") as script:
            script.write("# Rebuilt package\n")
        output = subprocess.check_output(command, text=True)
        self.assertEqual(output.splitlines(), ["run", "--session"])
