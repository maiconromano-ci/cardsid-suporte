#!/usr/bin/env python3
"""Gera .github/workflows/cardsid-build.yml a partir do flutter-build.yml oficial.

Mantem so o necessario para Windows x64 (bridge, TopMostWindow, build flutter),
aplica a marca apos o checkout e publica CardsID-Suporte-<versao>.exe/.msi como Release.
Rodar de novo apos sincronizar com uma versao nova do RustDesk:  python cardsid/gen_workflow.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / ".github/workflows/flutter-build.yml").read_text(encoding="utf-8")
APP = "CardsID-Suporte"


def must(cond, msg):
    if not cond:
        sys.exit(f"[gen_workflow] {msg}")


# Cabecalho: gatilhos proprios
i_env = src.index("\nenv:\n")
header = """name: CardsID Suporte - build Windows

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
body = src[i_env:]

# Somente os jobs do Windows flutter
i_cut = body.index("\n  build-for-windows-sciter:")
body = body[:i_cut] + "\n"

body = body.replace('TAG_NAME: "${{ inputs.upload-tag }}"', 'TAG_NAME: "cardsid-v${{ github.run_number }}"')
body = body.replace('UPLOAD_ARTIFACT: "${{ inputs.upload-artifact }}"', 'UPLOAD_ARTIFACT: "true"')
body = body.replace("${{ inputs.upload-artifact }}", "true")

# Sem ARM64
body, n = re.subn(r"\n\s*- \{[^{}]*windows-11-arm[^{}]*\}", "", body)
must(n == 2, f"esperava remover 2 entradas ARM64, removi {n}")

# Aplicar a marca logo apos o checkout
chk = "          submodules: recursive\n"
must(body.count(chk) == 1, "checkout com submodulos nao encontrado")
body = body.replace(chk, chk + """      - name: Aplicar marca CardsID Suporte
        shell: bash
        run: python3 cardsid/apply.py
""")

# Executavel com o nome do app (o instalador e o packer esperam <app>.exe)
mv = "          mv ./flutter/build/windows/${{ matrix.job.flutter-arch }}/runner/Release ./rustdesk\n"
must(mv in body, "passo de build nao encontrado")
body = body.replace(mv, mv + f"          mv ./rustdesk/rustdesk.exe ./rustdesk/{APP}.exe\n")

old = "python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/rustdesk.exe"
must(old in body, "generate.py nao encontrado")
body = body.replace(old, f"python3 ./generate.py -f ../../rustdesk/ -o . -e ../../rustdesk/{APP}.exe")
body, n = re.subn(r"\./SignOutput/rustdesk-\$\{\{ env\.VERSION \}\}-\$\{\{ matrix\.job\.arch \}\}\.exe",
                  f"./SignOutput/{APP}-${{{{ env.VERSION }}}}.exe", body)
must(n == 1, "saida .exe nao encontrada")

old = "python preprocess.py --arp -d ../../rustdesk"
must(old in body, "preprocess msi nao encontrado")
body = body.replace(old, f'python preprocess.py --arp -d ../../rustdesk --app-name {APP} --manufacturer Cardsinova')
body, n = re.subn(r"\.\./\.\./SignOutput/rustdesk-\$\{\{ env\.VERSION \}\}-\$\{\{ matrix\.job\.arch \}\}\.msi",
                  f"../../SignOutput/{APP}-${{{{ env.VERSION }}}}-Instalador.msi", body)
must(n == 1, "saida .msi nao encontrada")
body = body.replace("sha256sum ../../SignOutput/rustdesk-*.msi", f"sha256sum ../../SignOutput/{APP}-*.msi")

# Release no proprio repositorio
body, n = re.subn(r"            \./SignOutput/rustdesk-\*\.msi\n            \./SignOutput/rustdesk-\*\.exe\n",
                  f"            ./SignOutput/{APP}-*.msi\n            ./SignOutput/{APP}-*.exe\n", body)
must(n == 1, "arquivos da release nao encontrados")
body = body.replace("          prerelease: true\n          tag_name: ${{ env.TAG_NAME }}",
                    "          prerelease: false\n          name: CardsID Suporte ${{ env.VERSION }} (build ${{ github.run_number }})\n"
                    "          tag_name: ${{ env.TAG_NAME }}")

# bridge.yml: o bridge do Flutter 3.44 so serve ao Windows ARM64 (nao compilamos) e ja travou o build
bp = ROOT / ".github/workflows/bridge.yml"
bsrc = bp.read_text(encoding="utf-8")
bnew, n = re.subn(r"\n\s*# Dedicated bridge for the Windows arm64 build[^\n]*\n\s*- \{[^{}]*\}", "", bsrc)
if n:
    bp.write_text(bnew, encoding="utf-8")
    print("[gen_workflow] bridge.yml: removido bridge Flutter 3.44 (ARM64)")

out = ROOT / ".github/workflows/cardsid-build.yml"
out.write_text(header + body, encoding="utf-8")
print(f"[gen_workflow] gerado {out.relative_to(ROOT)} ({len((header + body).splitlines())} linhas)")
