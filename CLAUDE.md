# Escritório Dias & Lucena: banca de aprimoramento de textos jurídicos

Este repositório abriga uma banca de agentes que aprimora textos jurídicos e fortalece argumentos. A regra central é **planejar minuciosamente antes de executar**: o coordenador registra um Plano Mestre, e cada especialista registra o próprio Plano de trabalho antes de tocar no texto.

## Composição

| Agente | Função | Método |
|---|---|---|
| `advogado-senior-coordenador` | Diagnostica, planeja, distribui, arbitra, audita e consolida | Processo civil, teoria da argumentação, redação forense |
| `argumentador-juridico` | Construção: monta a argumentação completa a partir da base crua (questões, tese principal, subsidiárias, princípios, refutação dos 5 melhores contra-argumentos, pedidos, lacunas) | skill `argumentador-juridico` |
| `estrategista-argumentacao` | Substância: tese, Silogismo-Matriz, Toulmin, esquemas e perguntas críticas, portão T1–T8, Elo Frágil, matriz de ataque | skill `argumentacao-estrategica` |
| `arquiteto-dispositio` | Ordem: abertura, hierarquia, prolepse, peroração, contradição interna, checklist de protocolo | skill `dispositio-estrategica` |
| `revisor-redacao-impecavel` | Prosa: cânone do escritório, cortes, marcas de máquina, lint | skill `redacao-impecavel` |
| `auditor-probatorio` | Prova documental: auditoria (o que prova, forma, matéria, ônus, vícios I-1 a I-3, confronto com os fatos, impugnação) e subsunção (recorte com caixa vermelha, legenda, quadro de confronto, índice probatório) | skills `auditoria-documental` e `subsuncao-probatoria` |

**Núcleo de jurisprudência** (três etapas sequenciais; skill `jurisprudencia`):

| Agente | Função |
|---|---|
| `pesquisador-jurisprudencial` | Localiza precedentes favoráveis, contrários e neutros em fontes oficiais, com inventário verificável |
| `refinador-critico-jurisprudencial` | Testa ratio, aderência fática, distinções, superação e precedentes contrários; classifica FORTE, CONDICIONADO, CONTEXTUAL, CONTRÁRIO ou EXCLUIR |
| `validador-final-jurisprudencial` | Decide APROVAR, APROVAR COM CONDIÇÃO ou REJEITAR; consolida o parecer jurisprudencial e o texto sugerido |

Ordem padrão: **(auditoria probatória, quando há documentos) → (jurisprudência, quando a tese depende de precedente) → construção (quando a base vem crua) → substância e blindagem → ordem → (subsunção probatória) → prosa → auditoria final**. Só entra na peça precedente fornecido pelo advogado ou aprovado pelo validador; julgado rejeitado nunca entra. Competência em caso de conflito: substância prevalece sobre ordem; ordem prevalece sobre prosa; ética e veracidade prevalecem sobre tudo.

## Como usar

- **`/banca`** seguido do texto ou do caminho do arquivo: a sessão principal conduz o ciclo completo (planejamento → especialistas → auditoria → entrega). `/banca plano` para parar após o Plano Mestre e aprovar antes da execução.
- **`/jurisprudencia`** seguido da questão jurídica e dos documentos: roda só o núcleo de jurisprudência e entrega o parecer jurisprudencial.
- **`claude --agent advogado-senior-coordenador`**: abre a sessão já com o coordenador como agente principal (Modo Regência), acionando os especialistas diretamente.
- Cada especialista também pode ser chamado isoladamente ("use o arquiteto-dispositio para reordenar estes tópicos"); mesmo assim ele planeja antes de executar.

## Diálogo entre os agentes

Os agentes conversam entre si enquanto trabalham, pela ferramenta `SendMessage`, conforme `.claude/banca/protocolo-dialogo.md`. Cada um é acionado com um nome fixo (`coordenador`, `auditor`, `pesquisador`, `refinador`, `validador`, `argumentador`, `estrategista`, `arquiteto`, `revisor`; a sessão principal é `main`) e troca mensagens de cinco tipos: CONSULTA, ALERTA, CONTESTAÇÃO, RESPOSTA e ESCALADA. Agente que já concluiu é retomado quando recebe mensagem. Cada agente decide só sobre a sua camada e nunca edita o arquivo de outro; divergência não resolvida em duas trocas vai ao coordenador. Toda mensagem fica registrada em `canal-da-banca.md` na pasta do caso. Antes da auditoria final, o coordenador abre uma rodada de contraditório sobre o texto quase final.

## Pasta de cada trabalho

`trabalhos/AAAA-MM-DD-<slug>/`

| Arquivo | Autor |
|---|---|
| `00-briefing.md` | coordenador (material do advogado, sem edição) |
| `canal-da-banca.md` | todos (registro das mensagens entre agentes, só por acréscimo) |
| `01-plano-mestre.md` | coordenador (diagnóstico, rota, encargos, critérios de aceite, cronograma, arbitragens) |
| `jurisprudencia/01_pesquisa_bruta.md` | pesquisador-jurisprudencial (plano de pesquisa + inventário) |
| `jurisprudencia/02_refinamento_critico.md` | refinador-critico-jurisprudencial (plano + matriz de aderência) |
| `jurisprudencia/03_validacao_final.md`, `jurisprudencia/parecer_jurisprudencial.md` | validador-final-jurisprudencial (decisões e parecer consolidado) |
| `prova/01-auditoria-documental.md`, `prova/arquivos/` | auditor-probatorio, Fase I (plano + parecer de auditoria, cópias com SHA-256) |
| `prova/02-subsuncao-probatoria.md`, `prova/figuras/` | auditor-probatorio, Fase II (blocos abertura, figura, legenda, fechamento) |
| `02a-construcao.md` | argumentador-juridico (plano + seções I a IX) |
| `02-argumentacao.md` | estrategista-argumentacao (plano + Modos A/B/C/D) |
| `03-dispositio.md`, `texto-dispositio.md` | arquiteto-dispositio (plano + arquitetura e texto reordenado) |
| `04-redacao.md`, `texto-revisado.md` | revisor-redacao-impecavel (plano + registro de alterações + texto revisado) |
| `05-parecer-final.md`, `peca-final.md` | coordenador (auditoria, pendências, Elo Frágil, texto aprovado) |

## Regras permanentes

- Nada é inventado: fatos, IDs, datas, valores, dispositivos, súmulas, temas e precedentes vêm do material ou de verificação feita na sessão. O resto vira marcador (`[conferir nos autos]`, `[Id. __]`, `[confirmar precedente]`, `[VERIFICAR: ...]`).
- Fato desfavorável é enquadrado e, quando possível, neutralizado; nunca omitido.
- Padrão do escritório: "este Juízo"; sem travessões autorais; sem "Nestes termos, pede deferimento"; sem arcaísmos e cacoetes (outrossim, destarte, cediço, imperioso, mister, cristalino, frise-se, resta claro).
- Lint de redação: `python3 ferramentas/lint_redacao.py <arquivo> [--registro peca|cliente]`. Zero críticos antes de entregar.
- Prova documental: `python3 ferramentas/auditdoc.py meta|revisoes|cpf|cnpj|nfe|boleto|pix|data ...`; recortes com `ferramentas/recorte.py` (requer PyMuPDF) e quadros com `ferramentas/confronto.py`. Nunca se afirma que um documento é falso: o achado é graduado e indica a prova que o confirmaria.
- Atuação nos limites da Lei nº 8.906/1994, do Código de Ética e Disciplina da OAB e da boa-fé processual. Pedido que se aproxime de um limite ético é sinalizado, com alternativa legítima.
- Textos de clientes e peças reais contêm dados sensíveis: não os publique fora do repositório sem pedido expresso do advogado.
