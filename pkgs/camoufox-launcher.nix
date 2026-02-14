{ lib
, python3Packages
, fetchFromGitHub
, makeWrapper
, camoufox-bin
, camoufoxVersion ? "135.0.1"
, camoufoxRelease ? "beta.24"
, camoufoxPythonHash ? "sha256-ixxXzRjkMkC2uu6G68db1B2/66ghvDJkM7NKqK0Tk1I="
}:

let
  camoufoxTag = "v${camoufoxVersion}-${camoufoxRelease}";

  camoufoxPythonSrc = fetchFromGitHub {
    owner = "daijro";
    repo = "camoufox";
    rev = camoufoxTag;
    hash = camoufoxPythonHash;
  };
in
python3Packages.buildPythonApplication {
  pname = "camoufox-launcher";
  version = "${camoufoxVersion}-${camoufoxRelease}";
  pyproject = true;
  src = ../camoufox-launcher;

  build-system = [
    python3Packages.setuptools
  ];

  propagatedBuildInputs = [
    python3Packages.browserforge
    python3Packages.click
    python3Packages.geoip2
    python3Packages."language-tags"
    python3Packages.lxml
    python3Packages.numpy
    python3Packages.orjson
    python3Packages.platformdirs
    python3Packages.playwright
    python3Packages.pysocks
    python3Packages.pyyaml
    python3Packages.requests
    python3Packages.screeninfo
    python3Packages.tqdm
    python3Packages."typing-extensions"
    python3Packages."ua-parser"
  ];

  nativeBuildInputs = [
    makeWrapper
  ];

  doCheck = false;

  postFixup = ''
    wrapProgram "$out/bin/camoufox-launcher" \
      --set-default CAMOUFOX_EXECUTABLE_PATH "${camoufox-bin}/bin/camoufox-bin" \
      --set-default CAMOUFOX_PY_EXECUTABLE_PATH "${camoufox-bin}/share/camoufox-bin/camoufox" \
      --set-default CAMOUFOX_BUNDLE_PATH "${camoufox-bin}/share/camoufox-bin" \
      --set-default CAMOUFOX_VERSION "${camoufoxVersion}" \
      --set-default CAMOUFOX_RELEASE "${camoufoxRelease}" \
      --set-default CAMOUFOX_PYTHONLIB_PATH "${camoufoxPythonSrc}/pythonlib"
  '';

  meta = with lib; {
    description = "CLI launcher for Camoufox Playwright server with Python-client fingerprint and geoip features";
    homepage = "https://github.com/daijro/camoufox";
    license = licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "camoufox-launcher";
  };
}
