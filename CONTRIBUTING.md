# Contributing to Redock

A fix, a small improvement, or a test on a new desktop setup is welcome. For a larger change, open an issue first so we can agree on the scope.

## Build and test

Use the same Dux Shell version for the stock UI and the `dms` binary. See [`dms-version`](dms-version) for supported versions and the [README](README.md#install) for build tools.

From the Redock checkout, build against a clean Dux Shell tree. This example uses 2.1.2.

```sh
git clone --branch v2.1.2 --recurse-submodules https://github.com/duxlabs-dev/dux-shell.git ../dux-shell-2.1.2
export REDOCK_STOCK_UI="$PWD/../dux-shell-2.1.2/quickshell"
./redock build "$REDOCK_STOCK_UI" ../redock-test-ui
python3 -m unittest discover -s tests -v
```

The build writes a separate QML tree. The tests use temporary config directories and a simulated user service. For changes to the launcher, also run `shellcheck launch.sh`.

## Send a pull request

- Describe the problem and what changed. Link an issue if there is one.
- For visual changes, include a screenshot and the display scale. Test the dock in a Wayland session and say which compositor you used.
- For installer changes, check install and uninstall. Confirm that uninstall restores the previous DMS setup.
- For a new DMS version, update [`dms-version`](dms-version), [the patch directory](patches/), [the CI matrix](.github/workflows/ci.yml), and [the source checksums](tests/upstream.sha256) together. Report a live-session result separately from a successful build.

CI tests every listed DMS version on pull requests and pushes to `main`. The release job is skipped on those runs. It publishes the archive and checksum only after CI passes for a version tag such as `v0.1.1`.
