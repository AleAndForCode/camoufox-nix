#!/usr/bin/env python3
import argparse
import base64
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _cache_dir() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "camoufox"
    return Path.home() / ".cache" / "camoufox"


def _seed_runtime_cache() -> None:
    bundle_root = os.environ.get("CAMOUFOX_BUNDLE_PATH")
    if not bundle_root:
        return

    bundle_dir = Path(bundle_root)
    if not bundle_dir.is_dir():
        return

    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Keep store as source of truth and avoid copying large bundles.
    for entry in bundle_dir.iterdir():
        dst = cache_dir / entry.name
        if dst.exists() or dst.is_symlink():
            continue
        dst.symlink_to(entry, target_is_directory=entry.is_dir())

    version = os.environ.get("CAMOUFOX_VERSION")
    release = os.environ.get("CAMOUFOX_RELEASE")
    version_json = cache_dir / "version.json"
    if version and release:
        version_json.write_text(
            json.dumps({"version": version, "release": release}),
            encoding="utf-8",
        )


def _add_nested_key(target: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = target
    for part in parts[:-1]:
        current = cursor.get(part)
        if not isinstance(current, dict):
            current = {}
            cursor[part] = current
        cursor = current
    cursor[parts[-1]] = value


def _parse_scalar(raw: str) -> Any:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_set_arg(entry: str) -> tuple[str, Any]:
    if "=" not in entry:
        raise ValueError(f"Invalid --set value '{entry}'. Expected KEY=VALUE.")
    key, raw_value = entry.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Invalid --set value '{entry}'. Empty key.")
    return key, _parse_scalar(raw_value)


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".json"}:
        data = json.loads(text)
    else:
        import yaml

        data = yaml.safe_load(text)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Top-level config must be a mapping/object.")
    return data


def _resolve_geoip(value: str | None, auto: bool) -> Any:
    if auto:
        return True
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "auto":
        return True
    return value


def _resolve_headless(value: str | None) -> Any:
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "virtual":
        return "virtual"
    raise ValueError(f"Invalid --headless value: {value}")


def _import_camoufox() -> tuple[Any, Any]:
    pythonlib_path = os.environ.get("CAMOUFOX_PYTHONLIB_PATH")
    if pythonlib_path:
        sys.path.insert(0, pythonlib_path)

    try:
        import camoufox.locale as camoufox_locale
        from camoufox.server import LAUNCH_SCRIPT, to_camel_case_dict
        from camoufox.utils import launch_options
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Failed to import Camoufox Python client. "
            "Ensure CAMOUFOX_PYTHONLIB_PATH and Python dependencies are available."
        ) from exc

    # Camoufox upstream stores GeoIP DB near module files; redirect to writable cache.
    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    mmdb_name = Path(camoufox_locale.MMDB_FILE).name
    camoufox_locale.MMDB_FILE = cache_dir / mmdb_name

    return launch_options, LAUNCH_SCRIPT, to_camel_case_dict


def _launch_server_compat(
    launch_options_fn: Any,
    launch_script: Any,
    to_camel_case_dict_fn: Any,
    **kwargs: Any,
) -> int:
    import orjson
    from playwright._impl._driver import compute_driver_executable

    config = launch_options_fn(**kwargs)
    # Playwright launchServer rejects null for some fields (e.g. proxy).
    config = {k: v for k, v in config.items() if v is not None}
    data = orjson.dumps(to_camel_case_dict_fn(config))

    nodejs, driver_cli = compute_driver_executable()
    driver_root = str(Path(driver_cli).parent)

    process = subprocess.Popen(  # nosec
        [nodejs, str(launch_script)],
        cwd=driver_root,
        stdin=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    if process.stdin:
        process.stdin.write(base64.b64encode(data).decode())
        process.stdin.close()

    received_signal: int | None = None

    def _forward_signal(signum: int, _frame: Any) -> None:
        nonlocal received_signal
        received_signal = signum
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass

    prev_int = signal.getsignal(signal.SIGINT)
    prev_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _forward_signal)
    signal.signal(signal.SIGTERM, _forward_signal)

    try:
        while True:
            rc = process.poll()
            if rc is not None:
                return rc
            time.sleep(0.2)
    except KeyboardInterrupt:
        _forward_signal(signal.SIGINT, None)
    finally:
        signal.signal(signal.SIGINT, prev_int)
        signal.signal(signal.SIGTERM, prev_term)

    # Graceful shutdown timeout, then force kill as fallback.
    deadline = time.time() + 8.0
    while time.time() < deadline:
        rc = process.poll()
        if rc is not None:
            return rc
        time.sleep(0.2)

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)

    if received_signal is not None:
        return 128 + received_signal
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="camoufox-launcher",
        description="Launch Camoufox Playwright websocket server with fingerprint/geoip features",
    )

    parser.add_argument("--config-file", type=Path, help="JSON/YAML file with launch_server kwargs")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="Override/add option using dotted path; VALUE parsed as JSON when possible")

    parser.add_argument("--port", type=int, help="Playwright WS server port")
    parser.add_argument("--ws-path", help="Playwright WS path")
    parser.add_argument("--headless", choices=["true", "false", "virtual"], help="Headless mode")
    parser.add_argument("--executable-path", help="Path to camoufox executable")

    parser.add_argument("--geoip", help="GeoIP option: true/false/auto/or explicit IP")
    parser.add_argument("--geoip-auto", action="store_true", help="Shortcut for --geoip auto")
    parser.add_argument("--proxy-server", help="Proxy server URL, e.g. socks5://127.0.0.1:9050")
    parser.add_argument("--proxy-username", help="Proxy username")
    parser.add_argument("--proxy-password", help="Proxy password")

    parser.add_argument("--os", dest="target_os", action="append", choices=["windows", "macos", "linux"], help="Target OS distribution for fingerprint generation (repeatable)")
    parser.add_argument("--locale", action="append", help="Locale value (repeatable)")
    parser.add_argument("--humanize", action="store_true", help="Enable human-like mouse movement")
    parser.add_argument("--humanize-max-time", type=float, help="Humanize max duration in seconds")

    parser.add_argument("--print-effective-config", action="store_true", help="Print launch_options output before launching")
    parser.add_argument("--check-only", action="store_true", help="Validate config and exit without running server")

    return parser.parse_args()


def build_options(args: argparse.Namespace) -> dict[str, Any]:
    cfg: dict[str, Any] = {}

    if args.config_file:
        cfg.update(_load_config_file(args.config_file))

    if args.port is not None:
        cfg["port"] = args.port
    if args.ws_path:
        cfg["ws_path"] = args.ws_path

    headless = _resolve_headless(args.headless)
    if headless is not None:
        cfg["headless"] = headless

    geoip = _resolve_geoip(args.geoip, args.geoip_auto)
    if geoip is not None:
        cfg["geoip"] = geoip

    proxy: dict[str, str] = {}
    if args.proxy_server:
        proxy["server"] = args.proxy_server
    if args.proxy_username:
        proxy["username"] = args.proxy_username
    if args.proxy_password:
        proxy["password"] = args.proxy_password
    if proxy:
        cfg["proxy"] = proxy

    if args.target_os:
        cfg["os"] = args.target_os if len(args.target_os) > 1 else args.target_os[0]

    if args.locale:
        cfg["locale"] = args.locale if len(args.locale) > 1 else args.locale[0]

    if args.humanize_max_time is not None:
        cfg["humanize"] = args.humanize_max_time
    elif args.humanize:
        cfg["humanize"] = True

    if args.executable_path:
        cfg["executable_path"] = args.executable_path
    elif "executable_path" not in cfg and os.environ.get("CAMOUFOX_PY_EXECUTABLE_PATH"):
        cfg["executable_path"] = os.environ["CAMOUFOX_PY_EXECUTABLE_PATH"]
    elif "executable_path" not in cfg and os.environ.get("CAMOUFOX_EXECUTABLE_PATH"):
        cfg["executable_path"] = os.environ["CAMOUFOX_EXECUTABLE_PATH"]

    for item in args.set:
        key, value = _parse_set_arg(item)
        _add_nested_key(cfg, key, value)

    return cfg


def main() -> int:
    args = parse_args()
    _seed_runtime_cache()
    launch_options, launch_script, to_camel_case_dict_fn = _import_camoufox()

    options = build_options(args)

    if args.print_effective_config or args.check_only:
        rendered = launch_options(**options)
        print(json.dumps(rendered, indent=2, default=str))

    if args.check_only:
        ws_path = options.get("ws_path", "")
        port = options.get("port")
        if port is not None:
            print(f"Config validated. Expected endpoint like: ws://127.0.0.1:{port}/{ws_path}")
        return 0

    return _launch_server_compat(
        launch_options,
        launch_script,
        to_camel_case_dict_fn,
        **options,
    )


if __name__ == "__main__":
    raise SystemExit(main())
