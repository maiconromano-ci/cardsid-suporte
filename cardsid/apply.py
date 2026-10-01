#!/usr/bin/env python3
"""Aplica a marca CardsID Suporte (Cardsinova) sobre o codigo do RustDesk.

Roda no CI logo apos o checkout (com submodulos). Cada substituicao e verificada:
se o codigo do RustDesk mudar e um padrao deixar de existir, o build falha aqui
em vez de gerar um cliente meio-RustDesk.
"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "cardsid" / "assets"

APP_NAME = "CardsID-Suporte"          # so letras, numeros e hifen (exigencia do RustDesk)
DISPLAY = "CardsID Suporte"
COMPANY = "Cardsinova"
HOST = "rd.cardsinova.com.br"
KEY = "Fbog8tnDnZUYMoLsiy7SuGQOsFodARtLzeGYDuP2Dnc="   # chave PUBLICA do hbbs
COPYRIGHT = "Cardsinova - baseado no RustDesk (AGPL-3.0)"

PURPLE = "58167D"
GOLD = "E29901"


def sub(rel, pattern, repl, count=1):
    p = ROOT / rel
    with open(p, encoding="utf-8", newline="") as f:   # preserva LF/CRLF originais
        text = f.read()
    new, n = re.subn(pattern, repl, text, count=0 if count == 0 else count)
    if n == 0:
        sys.exit(f"[cardsid] padrao nao encontrado em {rel}: {pattern}")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print(f"[cardsid] {rel}: {n} alteracao(oes)")


def copy(src, *dests):
    for d in dests:
        dst = ROOT / d
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ASSETS / src, dst)
        print(f"[cardsid] {src} -> {d}")


# 1) Nome do app, servidor proprio e chave publica (hbb_common)
cfg = "libs/hbb_common/src/config.rs"
sub(cfg, r'(APP_NAME: RwLock<String> = RwLock::new\(")RustDesk(")', rf"\g<1>{APP_NAME}\g<2>")
sub(cfg, r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
    f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{HOST}"];')
sub(cfg, r'pub const RS_PUB_KEY: &str = "[^"]*";', f'pub const RS_PUB_KEY: &str = "{KEY}";')

# 2) Metadados do executavel (Propriedades > Detalhes no Windows)
for toml in ("Cargo.toml", "libs/portable/Cargo.toml"):
    # sem ancora "$": no runner Windows o checkout vem com CRLF
    sub(toml, r'(?m)^LegalCopyright = "[^"]*"', f'LegalCopyright = "{COPYRIGHT}"')
    sub(toml, r'(?m)^ProductName = "[^"]*"', f'ProductName = "{DISPLAY}"')
    sub(toml, r'(?m)^FileDescription = "[^"]*"', f'FileDescription = "{DISPLAY} - Acesso remoto Cardsinova"')
rc = "flutter/windows/runner/Runner.rc"
sub(rc, r'VALUE "CompanyName", ".*?"', f'VALUE "CompanyName", "{COMPANY}"')
sub(rc, r'VALUE "FileDescription", ".*?"', f'VALUE "FileDescription", "{DISPLAY} - Acesso remoto Cardsinova"')
sub(rc, r'VALUE "LegalCopyright", ".*?"', f'VALUE "LegalCopyright", "{COPYRIGHT}"')
sub(rc, r'VALUE "ProductName", ".*?"', f'VALUE "ProductName", "{DISPLAY}"')

# 3) Cores da marca no tema Flutter
dart = "flutter/lib/common.dart"
sub(dart, r"0xFF0071FF", f"0xFF{PURPLE}", count=0)
sub(dart, r"0x770071FF", f"0x77{PURPLE}", count=0)
sub(dart, r"0xAA0071FF", f"0xAA{PURPLE}", count=0)
sub(dart, r"0xFF2C8CFF", f"0xFF{PURPLE}", count=0)
sub(dart, r"(static const Color idColor = Color\()0xFF00B6F0", rf"\g<1>0xFF{GOLD}")

# 4) Icones e logos
copy("icon.ico", "res/icon.ico", "flutter/windows/runner/resources/app_icon.ico", "flutter/assets/icon.ico")
copy("tray-icon.ico", "res/tray-icon.ico")
copy("icon.png", "res/icon.png", "flutter/assets/icon.png")
copy("icon.svg", "flutter/assets/icon.svg")
for s in ("32x32.png", "64x64.png", "128x128.png", "128x128@2x.png"):
    copy(s, f"res/{s}")
for s in ("logo.png", "logo_light.png", "logo_dark.png"):
    copy(s, f"flutter/assets/{s}")       # exibido na tela inicial (max 300x60)

# 5) Telas do instalador MSI
copy("WixUIBannerBmp.bmp", "res/msi/Package/Resources/WixUIBannerBmp.bmp")
copy("WixUIDialogBmp.bmp", "res/msi/Package/Resources/WixUIDialogBmp.bmp")

print("[cardsid] marca aplicada")
