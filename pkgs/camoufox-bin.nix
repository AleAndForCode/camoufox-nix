{ lib
, stdenv
, fetchzip
, patchelf
, makeWrapper
, zlib
, gtk3
, nspr
, nss
, alsa-lib
, libpulseaudio
, libglvnd
, libva
, libgbm
, libnotify
, libX11
, libxcb
, libxscrnsaver
, cups
, pciutils
, vulkan-loader
, udev
, libcanberra-gtk3
, speechd-minimal
, ffmpeg
, pipewire
, mesa
, camoufoxVersion ? "135.0.1"
, camoufoxRelease ? "beta.24"
, camoufoxHash ? "sha256-k5t12L5q0RG8Zun0SAjGthYQXUcf+xVHvk9Mknr97QY="
}:

let
  camoufoxTag = "v${camoufoxVersion}-${camoufoxRelease}";

  src = fetchzip {
    url = "https://github.com/daijro/camoufox/releases/download/${camoufoxTag}/camoufox-${camoufoxVersion}-${camoufoxRelease}-lin.x86_64.zip";
    hash = camoufoxHash;
    stripRoot = false;
  };

  runtimeLibs = [
    stdenv.cc.cc
    zlib
    gtk3
    nspr
    nss
    alsa-lib
    libpulseaudio
    libglvnd
    libva
    libgbm
    libnotify
    libX11
    libxcb
    libxscrnsaver
    cups
    pciutils
    vulkan-loader
    udev
    libcanberra-gtk3
    speechd-minimal
    ffmpeg
    pipewire
    mesa
  ];
in
stdenv.mkDerivation rec {
  pname = "camoufox-bin";
  version = "${camoufoxVersion}-${camoufoxRelease}";

  inherit src;

  nativeBuildInputs = [
    patchelf
    makeWrapper
  ];

  buildInputs = runtimeLibs;

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/share/${pname}" "$out/bin"
    cp -r . "$out/share/${pname}/"

    if [ -f "$out/share/${pname}/camoufox" ]; then
      chmod +x "$out/share/${pname}/camoufox"
      # Patch ELF interpreter only; preserve upstream RPATH/$ORIGIN logic.
      if head -c 4 "$out/share/${pname}/camoufox" | grep -q $'\x7fELF'; then
        patchelf --set-interpreter "${stdenv.cc.bintools.dynamicLinker}" \
          "$out/share/${pname}/camoufox"
      fi
    fi

    if [ -f "$out/share/${pname}/camoufox-bin" ]; then
      chmod +x "$out/share/${pname}/camoufox-bin"
      if head -c 4 "$out/share/${pname}/camoufox-bin" | grep -q $'\x7fELF'; then
        patchelf --set-interpreter "${stdenv.cc.bintools.dynamicLinker}" \
          "$out/share/${pname}/camoufox-bin"
      fi
    fi

    runHook postInstall
  '';

  postFixup = let
    libPath = lib.makeLibraryPath runtimeLibs;
  in ''
    if [ -x "$out/share/${pname}/camoufox" ]; then
      wrapProgram "$out/share/${pname}/camoufox" \
        --prefix LD_LIBRARY_PATH : "${libPath}" \
        --set-default MOZ_ENABLE_WAYLAND 1 \
        --set-default MOZ_GLX_TEST_DISABLE 1
      ln -s "$out/share/${pname}/camoufox" "$out/bin/camoufox-bin"
    fi

    if [ -x "$out/share/${pname}/camoufox-bin" ]; then
      ln -s "$out/share/${pname}/camoufox-bin" "$out/bin/camoufox-bin-upstream"
    fi
  '';

  meta = with lib; {
    description = "Prebuilt Camoufox binary package for NixOS/Linux";
    homepage = "https://github.com/daijro/camoufox";
    license = licenses.mpl20;
    platforms = [ "x86_64-linux" ];
    mainProgram = "camoufox-bin";
  };
}
