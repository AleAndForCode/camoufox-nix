{
  description = "Camoufox binary package flake for Nix systems";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = import nixpkgs { inherit system; };
        camoufox-bin = pkgs.callPackage ./pkgs/camoufox-bin.nix { };
      in {
        packages = {
          inherit camoufox-bin;
          default = camoufox-bin;
        };

        apps.default = {
          type = "app";
          program = "${camoufox-bin}/bin/camoufox-bin";
        };
      }
    );
}
