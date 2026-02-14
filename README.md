# camoufox-nix

[Camoufox](https://github.com/daijro/camoufox) nix packages

## Motivation

[Camoufox](https://github.com/daijro/camoufox) is currently easiest to consume on Nix as a repackaged upstream binary release.
This repository exists as an intermediate step in the Camoufox nixification process:
- provide reusable flake packages now;
- keep packaging logic separated and ready to migrate into nixpkgs layout later;
- provide a launcher utility that reuses Camoufox Python-client fingerprint and GeoIP logic.

## What This Is

`camoufox-nix` is a flake with two packages:
- `camoufox-bin`: precompiled Camoufox release assets from GitHub;
- `camoufox-launcher`: tiny CLI that starts Camoufox Playwright server with Python-client features.

This is **not** a pure source build yet. The browser package applies Nix-side runtime patching/wrapping for Linux execution.

Current packaged browser version in this repository:
- `135.0.1-beta.24` (Linux `x86_64` asset)

## Usage

### Add flake input

```nix
{
  inputs.camoufox-nix.url = "github:AleAndForCode/camoufox-nix";

  outputs = { self, nixpkgs, camoufox-nix, ... }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    packages.${system}.default = camoufox-nix.packages.${system}.camoufox-bin;
  };
}
```

### Install packages from this flake

```bash
nix profile install github:AleAndForCode/camoufox-nix#camoufox-bin
nix profile install github:AleAndForCode/camoufox-nix#camoufox-launcher
```

### Run browser directly

```bash
nix run github:AleAndForCode/camoufox-nix
```

### Dev shell

Use the flake dev shell for local testing of both packages:

```bash
nix develop
```

Inside the shell, these tools/env vars are available:
- `camoufox-bin`
- `camoufox-launcher`
- `CAMOUFOX_EXECUTABLE_PATH`
- `CAMOUFOX_PY_EXECUTABLE_PATH`
- `CAMOUFOX_LAUNCHER_PATH`

## Use a different Camoufox version (override)

The browser package is parameterized by:
- `camoufoxVersion`
- `camoufoxRelease`
- `camoufoxHash` (required for fixed-output fetch)

The launcher package is also parameterized by:
- `camoufoxVersion`
- `camoufoxRelease`
- `camoufoxPythonHash` (source hash for Camoufox Python code)

Example override from another flake:

```nix
{
  inputs.camoufox-nix.url = "github:AleAndForCode/camoufox-nix";

  outputs = { self, nixpkgs, camoufox-nix, ... }:
  let
    system = "x86_64-linux";
    custom = camoufox-nix.packages.${system}.camoufox-bin.override {
      camoufoxVersion = "146.0.0";
      camoufoxRelease = "beta.1";
      camoufoxHash = "sha256-REPLACE_WITH_REAL_HASH";
    };
  in {
    packages.${system}.default = custom;
  };
}
```

Tip: use a fake hash first (for example `sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`), run a build, then replace with the hash Nix reports.

## Additional Features

### camoufox-launcher

`camoufox-launcher` starts Camoufox as a Playwright websocket server and exposes common runtime options:
- ws endpoint options (`--port`, `--ws-path`);
- fingerprint/runtime options from Camoufox Python client (`--os`, `--locale`, `--humanize`, `--set ...`);
- geoip and proxy options (`--geoip`, `--geoip-auto`, `--proxy-server`, ...);
- config-file based launch (`--config-file`) with CLI overrides.

It also includes:
- cache seeding for Camoufox runtime layout in `~/.cache/camoufox` (or `$XDG_CACHE_HOME/camoufox`);
- graceful shutdown on `SIGINT`/`SIGTERM` with fallback force-kill;
- Nix-compatible Playwright server launch.

Quick start:

```bash
camoufox-launcher --port 1234 --ws-path hello --headless true
```

Then connect from any Playwright client to:
- `ws://127.0.0.1:1234/hello`

Launcher config modes:

1. Direct flags

```bash
camoufox-launcher \
  --port 1234 \
  --ws-path hello \
  --os windows \
  --os macos \
  --locale en-US \
  --humanize-max-time 1.2 \
  --set firefox_user_prefs."network.http.max-connections"=180
```

2. YAML/JSON config + overrides

```bash
camoufox-launcher --config-file ./camoufox-server.yml --set geoip=true --set proxy.server='"socks5://127.0.0.1:9050"'
```

3. Validate config without launching

```bash
camoufox-launcher --config-file ./camoufox-server.yml --print-effective-config --check-only
```

Notes:
- Playwright client/server versions must match for websocket connect.
- Playwright server mode requires Node.js runtime (provided through Playwright Python package in Nix).

## Project Goals

1. Submit `camoufox-bin` and `camoufox-launcher` to nixpkgs with proper nixpkgs layout and review quality.
2. Build a fully pure Nix package from Camoufox sources (no precompiled upstream binaries).

Until then, this repository serves as the intermediate project for Camoufox nixification.
