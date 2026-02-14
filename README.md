# camoufox-nix

[Camoufox](https://github.com/daijro/camoufox) nix packages

## Motivation

[Camoufox](https://github.com/daijro/camoufox) is currently easiest to consume on Nix as a repackaged upstream binary release.
This repository exists as an intermediate step in the Camoufox nixification process:
- provide a reusable flake package now;
- keep packaging logic separated and ready to migrate into nixpkgs layout later.

## What This Is

`camoufox-nix` is a flake that packages precompiled Camoufox release assets from GitHub as `camoufox-bin`.

It is **not** a pure source build at this stage. The package applies Nix-side runtime patching/wrapping for Linux execution.

Current packaged version in this repository:
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

### Run directly

```bash
nix run github:AleAndForCode/camoufox-nix
```

### Install package from this flake

```bash
nix profile install github:AleAndForCode/camoufox-nix#camoufox-bin
```

### Use a different Camoufox version (override)

The package is parameterized by:
- `camoufoxVersion`
- `camoufoxRelease`
- `camoufoxHash` (required for fixed-output fetch)

Example override from another flake:

```nix
{
  inputs.camoufox-nix.url = "github:AleAndForCode/camoufox-nix";

  outputs = { self, nixpkgs, camoufox-nix, ... }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    camoufoxCustom = camoufox-nix.packages.${system}.camoufox-bin.override {
      camoufoxVersion = "146.0.0";
      camoufoxRelease = "beta.1";
      camoufoxHash = "sha256-REPLACE_WITH_REAL_HASH";
    };
  in {
    packages.${system}.default = camoufoxCustom;
  };
}
```

Tip: use a fake hash first (for example `sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=`), run a build, then replace with the hash Nix reports.

## Project Goals

1. Submit `camoufox-bin` to nixpkgs with proper nixpkgs layout and review quality.
2. Build a fully pure Nix package from Camoufox sources (no precompiled upstream binaries).

Until then, this repository serves as the intermediate project for Camoufox nixification.
