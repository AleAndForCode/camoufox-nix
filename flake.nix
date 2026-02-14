{
  description = "Camoufox binary and launcher flakes for Nix systems";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = import nixpkgs { inherit system; };

        camoufoxVersion = "135.0.1";
        camoufoxRelease = "beta.24";
        camoufoxHash = "sha256-k5t12L5q0RG8Zun0SAjGthYQXUcf+xVHvk9Mknr97QY=";
        camoufoxPythonHash = "sha256-ixxXzRjkMkC2uu6G68db1B2/66ghvDJkM7NKqK0Tk1I=";

        camoufox-bin = pkgs.callPackage ./pkgs/camoufox-bin.nix {
          inherit camoufoxVersion camoufoxRelease;
          camoufoxHash = camoufoxHash;
        };

        camoufox-launcher = pkgs.callPackage ./pkgs/camoufox-launcher.nix {
          inherit camoufox-bin camoufoxVersion camoufoxRelease;
          inherit camoufoxPythonHash;
        };
      in {
        packages = {
          inherit camoufox-bin camoufox-launcher;
          default = camoufox-bin;
        };

        apps = {
          default = {
            type = "app";
            program = "${camoufox-bin}/bin/camoufox-bin";
          };

          camoufox-launcher = {
            type = "app";
            program = "${camoufox-launcher}/bin/camoufox-launcher";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            camoufox-bin
            camoufox-launcher
          ];

          shellHook = ''
            export CAMOUFOX_EXECUTABLE_PATH="${camoufox-bin}/bin/camoufox-bin"
            export CAMOUFOX_PY_EXECUTABLE_PATH="${camoufox-bin}/share/camoufox-bin/camoufox"
            export CAMOUFOX_LAUNCHER_PATH="${camoufox-launcher}/bin/camoufox-launcher"
            export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
            export PS1='\[\e[38;5;208m\][camoufox-shell]\$\[\e[0m\] '

            echo "Dev shell ready."
            echo "camoufox-bin: $CAMOUFOX_EXECUTABLE_PATH"
            echo "camoufox-py-executable: $CAMOUFOX_PY_EXECUTABLE_PATH"
            echo "camoufox-launcher: $CAMOUFOX_LAUNCHER_PATH"
          '';
        };
      }
    );
}
