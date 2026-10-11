# Instalação da banca no computador local

A banca roda dentro do **Claude Code**. Os agentes (`.claude/agents/`), os comandos `/banca` e `/jurisprudencia` (`.claude/skills/`) e as regras (`CLAUDE.md`) são carregados automaticamente quando o Claude Code é aberto **na pasta deste repositório**. Não há instalação dos agentes um a um: basta ter o repositório no computador e abrir o Claude Code dentro dele.

## 1. Programas necessários

| Programa | Para quê | Windows | macOS |
|---|---|---|---|
| Git | baixar e atualizar o repositório; no Windows, também é exigido pelo Claude Code | git-scm.com/download/win | `xcode-select --install` |
| Claude Code | rodar os agentes | PowerShell: `irm https://claude.ai/install.ps1 \| iex` | Terminal: `curl -fsSL https://claude.ai/install.sh \| bash` |
| Python 3.10 ou superior | ferramentas de lint, auditoria e recorte | python.org (marque "Add python.exe to PATH") | `brew install python` |
| Poppler (opcional) | `pdftotext`, `pdftoppm`, `pdfsig` na auditoria documental | `winget install oschwartz10612.Poppler` | `brew install poppler` |
| Tesseract com português (opcional) | OCR de prints e PDFs escaneados | instalador do UB Mannheim (github.com/UB-Mannheim/tesseract/wiki), marcando o idioma Portuguese | `brew install tesseract tesseract-lang` |

Depois de instalar o Claude Code, rode `claude` uma vez no terminal e entre com a sua conta Claude.

## 2. Baixar o repositório

```bash
git clone https://github.com/manoeldiasnetoadv-debug/dias.git
cd dias
```

O repositório é privado: na primeira vez, o Git pedirá login no GitHub (no Windows abre uma janela do navegador).

## 3. Dependências Python

Na pasta `dias`:

```bash
python -m pip install -r ferramentas/requirements.txt
```

(no macOS, use `python3 -m pip ...`). Teste:

```bash
python ferramentas/auditdoc.py data 15/11/2025
python ferramentas/lint_redacao.py CLAUDE.md
```

**Windows**: as instruções dos agentes chamam `python3`. Se o comando `python3` não existir no seu terminal, diga ao Claude no início da sessão "neste computador use `python` em vez de `python3`", ou crie o atalho no Git Bash: `echo "alias python3=python" >> ~/.bashrc`.

## 4. Usar

```bash
cd dias
claude
```

Na primeira abertura, o Claude Code pergunta se você confia na pasta: confirme (sem isso, os agentes do projeto não carregam). Depois:

- `/agents` mostra os nove agentes da banca;
- `/banca` seguido do texto ou do caminho do arquivo roda o ciclo completo; `/banca plano` para aprovar o Plano Mestre antes da execução;
- `/jurisprudencia` seguido da questão jurídica roda só o núcleo de jurisprudência;
- `claude --agent advogado-senior-coordenador` abre a sessão já com o coordenador no comando.

Coloque os documentos do caso dentro da pasta `dias` (por exemplo, `dias/entrada/`) e indique o caminho ao Claude.

**Aplicativo Claude para desktop**: a aba Code do aplicativo também roda o Claude Code; escolha a pasta `dias` como pasta de trabalho.

## 5. Atualizar

```bash
cd dias
git pull
```

## 6. Observações

- **Sigilo**: o conteúdo de `trabalhos/` (casos reais) está no `.gitignore` e não é enviado ao GitHub. Faça cópia de segurança dessa pasta por outro meio.
- **Skills da conta**: os agentes tentam carregar as skills do escritório (`argumentacao-estrategica`, `dispositio-estrategica`, `redacao-impecavel`, `argumentador-juridico`, `auditoria-documental`, `subsuncao-probatoria`). Se elas não estiverem disponíveis no Claude Code local, cada agente segue o método que já traz escrito no próprio arquivo.
- **Pesquisa de jurisprudência**: no computador local, o acesso aos sites dos tribunais depende só da sua internet; a limitação de rede do ambiente na nuvem não se aplica.
- **Uso em qualquer pasta (opcional)**: para ter os agentes disponíveis fora do repositório, copie `.claude/agents/*.md` para `~/.claude/agents/` (Windows: `C:\Users\<usuário>\.claude\agents\`). As ferramentas de `ferramentas/` e os comandos `/banca` e `/jurisprudencia` continuam dependendo da pasta do repositório, por isso o uso recomendado é dentro dela.
