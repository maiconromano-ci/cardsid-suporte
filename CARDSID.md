# CardsID Suporte

Cliente de acesso remoto da **Cardsinova**, baseado no [RustDesk](https://github.com/rustdesk/rustdesk)
(AGPL-3.0). Este repositório é um fork público, conforme exige a licença AGPL.

**Download para clientes:** https://sup-desk.cardsinova.com.br

## O que muda em relação ao RustDesk
Todas as alterações são aplicadas na hora do build por [`cardsid/apply.py`](cardsid/apply.py):
- nome do app `CardsID-Suporte` (o RustDesk então desativa a checagem de atualização oficial);
- servidor próprio `rd.cardsinova.com.br` e sua chave **pública**;
- ícones, logos e cores da Cardsinova; telas do instalador MSI (`cardsid/assets`);
- metadados do executável.

Nenhum segredo fica neste repositório.

## Build
GitHub Actions → **CardsID Suporte - build** (`.github/workflows/cardsid-build.yml`),
disparado a cada push na branch `cardsid` ou manualmente. Gera uma Release com:
- Windows x64: `CardsID-Suporte-<versão>.exe` (executa direto, com opção de instalar) e `-Instalador.msi`;
- macOS: `-mac-x86_64.dmg` (Intel) e `-mac-aarch64.dmg` (Apple Silicon) — sem assinatura Apple;
- Linux x86_64/aarch64: `.deb`, `.rpm`, `-suse.rpm` e `.AppImage`.

No Windows a marca é completa (nome do app inclusive). No macOS/Linux o nome interno
continua "RustDesk" (ele define serviço, pastas e pacote), mas servidor, chave, ícones,
logo, cores e o nome no menu são da Cardsinova.

## Atualizar para uma versão nova do RustDesk
```
git fetch upstream --tags
git rebase <nova-tag>            # a branch cardsid só adiciona arquivos em cardsid/ e o workflow
python cardsid/gen_workflow.py   # regera o workflow a partir do flutter-build.yml novo
git push --force-with-lease
```
Se `apply.py` falhar com "padrão não encontrado", algo mudou no código do RustDesk e o padrão precisa ser ajustado.
