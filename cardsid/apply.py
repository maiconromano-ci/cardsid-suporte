#!/usr/bin/env python3
"""Aplica a marca CardsID Suporte (Cardsinova) sobre o codigo do RustDesk.

Uso (no CI, logo apos o checkout com submodulos):
    python3 cardsid/apply.py windows   # marca completa: nome do app, instalador MSI, metadados
    python3 cardsid/apply.py macos     # marca leve (ver abaixo)
    python3 cardsid/apply.py linux     # marca leve (ver abaixo)

Marca leve (macOS/Linux): no Mac e no Linux o nome do app vira nome de servico systemd,
de pastas (/etc/rustdesk, /tmp/rustdesk-*), do pacote .app e dos plists do launchd.
Trocar exigiria reescrever todo o empacotamento. Por isso o nome interno continua
"RustDesk", mas servidor/chave, icones, logos, cores e o nome no menu sao da Cardsinova,
e a checagem de atualizacao do RustDesk oficial fica desligada.

Cada substituicao e verificada: se o codigo do RustDesk mudar e um padrao deixar de
existir, o build falha aqui em vez de gerar um cliente meio-RustDesk.
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

PLATFORM = sys.argv[1] if len(sys.argv) > 1 else ""
if PLATFORM not in ("windows", "macos", "linux"):
    sys.exit("uso: apply.py windows|macos|linux")


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


print(f"[cardsid] plataforma: {PLATFORM}")

# 1) Servidor proprio e chave publica (todas as plataformas)
cfg = "libs/hbb_common/src/config.rs"
sub(cfg, r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
    f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{HOST}"];')
sub(cfg, r'pub const RS_PUB_KEY: &str = "[^"]*";', f'pub const RS_PUB_KEY: &str = "{KEY}";')

if PLATFORM == "windows":
    # Nome do app: o RustDesk entao troca "RustDesk" por ele em toda a interface
    # e desliga sozinho a checagem de atualizacao oficial
    sub(cfg, r'(APP_NAME: RwLock<String> = RwLock::new\(")RustDesk(")', rf"\g<1>{APP_NAME}\g<2>")
else:
    # Nome interno continua RustDesk -> desligar a checagem de atualizacao na mao
    sub("src/common.rs", r"(pub fn check_software_update\(\) \{\s*)if is_custom_client\(\) \{",
        r"\g<1>if true {")

# 2) Cores da marca no tema Flutter (todas)
dart = "flutter/lib/common.dart"
sub(dart, r"0xFF0071FF", f"0xFF{PURPLE}", count=0)
sub(dart, r"0x770071FF", f"0x77{PURPLE}", count=0)
sub(dart, r"0xAA0071FF", f"0xAA{PURPLE}", count=0)
sub(dart, r"0xFF2C8CFF", f"0xFF{PURPLE}", count=0)
sub(dart, r"(static const Color idColor = Color\()0xFF00B6F0", rf"\g<1>0xFF{GOLD}")

# 3) Icones e logos dentro do app (todas)
copy("icon.png", "res/icon.png", "flutter/assets/icon.png")
copy("icon.svg", "flutter/assets/icon.svg")
for s in ("logo.png", "logo_light.png", "logo_dark.png"):
    copy(s, f"flutter/assets/{s}")       # exibido na tela inicial (max 300x60)
for s in ("32x32.png", "64x64.png", "128x128.png", "128x128@2x.png"):
    copy(s, f"res/{s}")

if PLATFORM == "windows":
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
    copy("icon.ico", "res/icon.ico", "flutter/windows/runner/resources/app_icon.ico", "flutter/assets/icon.ico")
    copy("tray-icon.ico", "res/tray-icon.ico")
    # Telas do instalador MSI
    copy("WixUIBannerBmp.bmp", "res/msi/Package/Resources/WixUIBannerBmp.bmp")
    copy("WixUIDialogBmp.bmp", "res/msi/Package/Resources/WixUIDialogBmp.bmp")

elif PLATFORM == "macos":
    copy("AppIcon.icns", "flutter/macos/Runner/AppIcon.icns")
    copy("mac-icon.png", "res/mac-icon.png")
    copy("mac-tray-dark-x2.png", "res/mac-tray-dark-x2.png")
    copy("mac-tray-light-x2.png", "res/mac-tray-light-x2.png")
    sub("flutter/macos/Runner/Configs/AppInfo.xcconfig", r"PRODUCT_COPYRIGHT = .*",
        f"PRODUCT_COPYRIGHT = {COPYRIGHT}")

elif PLATFORM == "linux":
    copy("tray-icon.ico", "res/tray-icon.ico")
    copy("icon.svg", "res/scalable.svg")
    # Nome que aparece no menu de aplicativos
    sub("res/rustdesk.desktop", r"(?m)^Name=RustDesk", f"Name={DISPLAY}")
    sub("res/rustdesk.desktop", r"(?m)^GenericName=.*", "GenericName=Acesso remoto Cardsinova")

print("[cardsid] marca aplicada")
