#!/usr/bin/env python3
"""Gera .github/workflows/cardsid-build.yml a partir do flutter-build.yml oficial.

Plataformas: Windows x64 (.exe e .msi), macOS Intel e Apple Silicon (.dmg) e
Linux x86_64/aarch64 (.deb, .rpm, .rpm SUSE e AppImage). A marca e aplicada logo
apos o checkout e tudo vai para uma unica Release com nomes CardsID-Suporte-*.
Rodar de novo apos sincronizar com uma versao nova do RustDesk:  python cardsid/gen_workflow.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / ".github/workflows/flutter-build.yml").read_text(encoding="utf-8")
APP = "CardsID-Suporte"
KEEP = ["generate-bridge", "build-RustDeskTempTopMostWindow", "build-for-windows-flutter",
        "build-for-macOS", "build-rustdesk-linux", "build-appimage"]


def must(cond, msg):
    if not cond:
        sys.exit(f"[gen_workflow] {msg}")


def replace1(text, old, new, what):
    must(text.count(old) == 1, f"{what}: esperava 1 ocorrencia, achei {text.count(old)}")
    return text.replace(old, new)


def apply_step(platform):
    return f"""      - name: Aplicar marca CardsID Suporte
        shell: bash
        run: python3 cardsid/apply.py {platform}
"""


def after_checkout(block, platform, what):
    chk = "          submodules: recursive\n"
    return replace1(block, chk, chk + apply_step(platform), f"{what}: checkout com submodulos")


# ---------- cabecalho
i_env = src.index("\nenv:\n")
i_jobs = src.index("\njobs:\n")
header = """name: CardsID Suporte - build

on:
  workflow_dispatch:
  push:
    branches: [cardsid]
    paths-ignore: ["**.md", "cardsid/gen_workflow.py"]

permissions:
  contents: write

concurrency:
  group: cardsid-build
  cancel-in-progress: true
"""
env = src[i_env:i_jobs]
env = env.replace('TAG_NAME: "${{ inputs.upload-tag }}"', 'TAG_NAME: "cardsid-v${{ github.run_number }}"')
env = env.replace('UPLOAD_ARTIFACT: "${{ inputs.upload-artifact }}"', 'UPLOAD_ARTIFACT: "true"')

# ---------- separa os jobs (indentacao de 2 espacos)
jobs_text = src[i_jobs + len("\njobs:\n"):]
parts = re.split(r"(?m)^(?=  [A-Za-z0-9_-]+:\s*$)", jobs_text)
blocks = {}
for p in parts:
    m = re.match(r"  ([A-Za-z0-9_-]+):", p)
    if m:
        blocks[m.group(1)] = p.rstrip("\n") + "\n\n"
for k in KEEP:
    must(k in blocks, f"job {k} nao encontrado no flutter-build.yml")
J = {k: blocks[k].replace("${{ inputs.upload-artifact }}", "true") for k in KEEP}

# ---------- Windows
J["build-RustDeskTempTopMostWindow"], n = re.subn(r"\n\s*- \{[^{}]*windows-11-arm[^{}]*\}", "", J["build-RustDeskTempTopMostWindow"])
must(n == 1, "ARM64 do TopMostWindow")
w = J["build-for-windows-flutter"]
w, n = re.subn(r"\n\s*- \{[^{}]*windows-11-arm[^{}]*\}", "", w)
must(n == 1, "ARM64 do Windows")
w = after_checkout(w, "windows", "windows")
mv = "          mv ./flutter/build/windows/${{ matrix.job.flutter-arch }}/runner/Release ./rustdesk\n"
w = replace1(w, mv, mv + f"          mv ./rustdesk/rustdesk.exe ./rustdesk/{APP}.exe\n", "windows: build")
w = replace1(w, "python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/rustdesk.exe",
             f"python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/{APP}.exe", "windows: generate.py")
w = replace1(w, "./SignOutput/rustdesk-${{ env.VERSION }}-${{ matrix.job.arch }}.exe",
             f"./SignOutput/{APP}-${{{{ env.VERSION }}}}.exe", "windows: saida exe")
w = replace1(w, "python preprocess.py --arp -d ../../rustdesk",
             f"python preprocess.py --arp -d ../../rustdesk --app-name {APP} --manufacturer Cardsinova", "windows: msi")
w = replace1(w, "../../SignOutput/rustdesk-${{ env.VERSION }}-${{ matrix.job.arch }}.msi",
             f"../../SignOutput/{APP}-${{{{ env.VERSION }}}}-Instalador.msi", "windows: saida msi")
w = w.replace("sha256sum ../../SignOutput/rustdesk-*.msi", f"sha256sum ../../SignOutput/{APP}-*.msi")
w = replace1(w, "            ./SignOutput/rustdesk-*.msi\n            ./SignOutput/rustdesk-*.exe\n",
             f"            ./SignOutput/{APP}-*.msi\n            ./SignOutput/{APP}-*.exe\n", "windows: release")
J["build-for-windows-flutter"] = w

# ---------- macOS (sem certificado Apple: os passos de assinatura nao podem rodar)
m = J["build-for-macOS"]
m = m.replace("env.MACOS_P12_BASE64 != null", "env.MACOS_P12_BASE64 != ''")
m = after_checkout(m, "macos", "macos")
m = replace1(m, 'mv "$name" "${name%%.dmg}-${{ matrix.job.arch }}.dmg"',
             f'mv "$name" "{APP}-${{{{ env.VERSION }}}}-mac-${{{{ matrix.job.arch }}}}.dmg"', "macos: rename")
m = replace1(m, "            rustdesk*-${{ matrix.job.arch }}.dmg",
             f"            {APP}-*-mac-${{{{ matrix.job.arch }}}}.dmg", "macos: release")
J["build-for-macOS"] = m

# ---------- Linux (.deb/.rpm); o arquivo .deb original segue para o job do AppImage
l = J["build-rustdesk-linux"]
l = after_checkout(l, "linux", "linux")
rename_linux = f"""      - name: Renomear pacotes CardsID
        if: env.UPLOAD_ARTIFACT == 'true'
        shell: bash
        run: |
          mkdir -p cardsid-out
          for f in rustdesk-*.deb rustdesk-*.rpm; do
            [ -e "$f" ] || continue
            sudo cp "$f" "cardsid-out/{APP}-${{f#rustdesk-}}"
          done
          sudo chmod a+r cardsid-out/*; ls -la cardsid-out

"""
pub = "      - name: Publish debian/rpm package\n"
l = replace1(l, pub, rename_linux + pub, "linux: publish")
l, n = re.subn(r"(      - name: Publish debian/rpm package\n(?:.*\n)*?          files: \|\n)((?:            .*\n)+)",
              r"\g<1>            cardsid-out/*\n", l, count=1)
must(n == 1, "linux: arquivos da release")
l, n = re.subn(r"if: matrix\.job\.arch == 'x86_64' && env\.UPLOAD_ARTIFACT == 'true'", "if: false", l)
must(n == 3, f"linux: passos do archlinux (achei {n})")    # pacote Arch fica de fora
J["build-rustdesk-linux"] = l

# ---------- AppImage (reempacota o .deb ja com a marca)
a = J["build-appimage"]
pub = "      - name: Publish appimage package\n"
a = replace1(a, pub, f"""      - name: Renomear AppImage CardsID
        shell: bash
        run: |
          for f in ./appimage/rustdesk-*.AppImage; do sudo mv "$f" "./appimage/{APP}-${{f##*/rustdesk-}}"; done
          ls -la ./appimage/*.AppImage

""" + pub, "appimage: publish")
a = replace1(a, "            ./appimage/rustdesk-${{ env.VERSION }}-*.AppImage",
             f"            ./appimage/{APP}-*.AppImage", "appimage: release")
J["build-appimage"] = a

# ---------- todas as releases: mesma tag, versao final (nao pre-release)
body = "".join(J[k] for k in KEEP)
body = body.replace("          prerelease: true\n", "          prerelease: false\n")

# bridge.yml: o bridge do Flutter 3.44 so serve ao Windows ARM64 (nao compilamos) e ja travou o build
bp = ROOT / ".github/workflows/bridge.yml"
bsrc = bp.read_text(encoding="utf-8")
bnew, n = re.subn(r"\n\s*# Dedicated bridge for the Windows arm64 build[^\n]*\n\s*- \{[^{}]*\}", "", bsrc)
if n:
    bp.write_text(bnew, encoding="utf-8")
    print("[gen_workflow] bridge.yml: removido bridge Flutter 3.44 (ARM64)")

out = ROOT / ".github/workflows/cardsid-build.yml"
text = header + env + "\njobs:\n" + body
out.write_text(text, encoding="utf-8")
print(f"[gen_workflow] gerado {out.relative_to(ROOT)} ({len(text.splitlines())} linhas)")
