---
name: banca
description: "Aciona a banca de aprimoramento de textos jurídicos do escritório (advogado sênior coordenador + argumentador jurídico + estrategista de argumentação + arquiteto de dispositio + revisor de redação impecável + auditor probatório + núcleo de jurisprudência), com planejamento minucioso antes de qualquer atividade. USE quando o usuário pedir para aprimorar, fortalecer, blindar, reorganizar ou lapidar peça, tópico, tese ou texto jurídico com a banca, ou disser \"/banca\", \"aciona a banca\", \"passa pela banca\", \"multiagentes\", \"time de agentes\", \"revisão completa da peça\". Argumento opcional: \"plano\" para parar após o Plano Mestre e aguardar aprovação."
---

# Banca de aprimoramento de textos jurídicos

Você (a sessão principal, endereço `main`) conduz a banca em nome do **advogado sênior coordenador**. É você quem aciona cada agente, na ordem do Plano Mestre. **Os agentes conversam entre si enquanto trabalham**: cada um é acionado com um nome fixo e troca CONSULTAS, ALERTAS, CONTESTAÇÕES e RESPOSTAS com os colegas pela ferramenta `SendMessage`, conforme `.claude/banca/protocolo-dialogo.md`. Tudo fica registrado em `canal-da-banca.md` na pasta do caso.

Agentes (em `.claude/agents/`):

- `advogado-senior-coordenador`: planeja (Modo Planejamento), audita e consolida (Modo Auditoria Final).
- `argumentador-juridico`: construção da argumentação completa a partir da base crua (skill `argumentador-juridico`).
- `estrategista-argumentacao`: substância e blindagem (skill `argumentacao-estrategica`).
- `arquiteto-dispositio`: ordem e arquitetura (skill `dispositio-estrategica`).
- `revisor-redacao-impecavel`: prosa e cânone (skill `redacao-impecavel`), com lint em `ferramentas/lint_redacao.py`.
- `auditor-probatorio`: prova documental, Fase I (auditoria documental) e Fase II (subsunção probatória com recortes), com `ferramentas/auditdoc.py`, `recorte.py` e `confronto.py`.
- Núcleo de jurisprudência: `pesquisador-jurisprudencial` → `refinador-critico-jurisprudencial` → `validador-final-jurisprudencial` (fluxo detalhado na skill `jurisprudencia`).

## Nomes fixos (endereços para o diálogo)

Acione **sempre** cada agente pela ferramenta Agent com o parâmetro `name` abaixo. Sem nome, o agente não pode ser encontrado pelos colegas.

| Agente (`subagent_type`) | `name` |
|---|---|
| advogado-senior-coordenador | `coordenador` |
| auditor-probatorio | `auditor` |
| pesquisador-jurisprudencial | `pesquisador` |
| refinador-critico-jurisprudencial | `refinador` |
| validador-final-jurisprudencial | `validador` |
| argumentador-juridico | `argumentador` |
| estrategista-argumentacao | `estrategista` |
| arquiteto-dispositio | `arquiteto` |
| revisor-redacao-impecavel | `revisor` |

Cada nome é acionado **uma única vez por caso**. Para nova tarefa, dúvida, retrabalho ou contraditório com um agente que já concluiu, envie-lhe mensagem por `SendMessage` (`to` = o nome): ele é retomado com todo o contexto do que já fez. O mesmo vale para o coordenador, que acompanha o caso inteiro com memória.

Mensagens que os agentes enviam a `main` chegam a você: trate-as (ALERTA de prazo ou ético vai ao usuário na hora) e responda quando for o caso.

## Fluxo obrigatório

Etapas dependentes rodam em sequência: aguarde a conclusão de cada agente antes do próximo. Etapas que o Plano Mestre declare independentes rodam em paralelo (tipicamente a Fase I do `auditor` e o núcleo de jurisprudência), e os agentes paralelos conversam enquanto trabalham. Entre uma etapa e outra, leia o `canal-da-banca.md`: mensagem com `Status: aberta` cujo destinatário não a recebeu é encaminhada por você; ESCALADA vai ao `coordenador`.

### 1. Recepção

Reúna o material do usuário (texto colado, arquivo no repositório, anexos). Se o texto veio colado, grave-o integralmente; não resuma nem edite. Não faça perguntas se o material permitir trabalhar; se faltar a própria peça, a tese, o fato nuclear ou o pedido, pergunte no máximo duas coisas.

### 2. Planejamento (antes de qualquer execução)

Acione `advogado-senior-coordenador` com `name: coordenador` em **Modo Planejamento**, entregando o material integral e pedindo que crie a pasta `trabalhos/AAAA-MM-DD-<slug>/`, grave `00-briefing.md`, `01-plano-mestre.md` e o `canal-da-banca.md` (Fases 0 e 1). Ao receber o retorno:

- confira que `01-plano-mestre.md` existe e contém rota, encargos com critérios de aceite e cronograma;
- informe ao usuário, em poucas linhas, o diagnóstico, a rota escolhida e o provável Elo Frágil;
- se o argumento da skill for `plano`, ou se o usuário pediu para aprovar o plano, **pare aqui** e aguarde. Caso contrário, prossiga.

### 3. Auditoria probatória e núcleo de jurisprudência (quando o Plano Mestre indicar)

Se houver documentos relevantes, acione o `auditor-probatorio` na **Fase I** antes de qualquer construção de tese; se houver prazo dos arts. 430 ou 437 do CPC em curso, informe o usuário imediatamente. A **Fase II** (subsunção, recortes e legendas) é acionada depois do `arquiteto-dispositio` e antes do `revisor-redacao-impecavel`.

#### Núcleo de jurisprudência

Se o Plano Mestre listar questões para o núcleo, execute o fluxo da skill `jurisprudencia` (pesquisador, refinador e validador, em sequência, cada um planejando antes de executar) sobre a mesma pasta do trabalho, antes da argumentação. O `parecer_jurisprudencial.md` passa a ser leitura obrigatória do `argumentador-juridico` e do `estrategista-argumentacao`. Se depois um especialista devolver pedido de nova pesquisa, rode o núcleo com escopo restrito à questão nova.

### 4. Execução pelos especialistas

Para cada etapa do cronograma do Plano Mestre, acione o especialista indicado, com o seu `name` fixo, usando o modelo "ENCARGO DA BANCA" do plano (pasta, arquivos a ler, objetivo, modo, decisões vinculantes, critérios de aceite, arquivo de saída). Reforce sempre: **registrar o Plano de trabalho no topo do arquivo de saída antes de executar** e encerrar com o RELATÓRIO padronizado.

Depois de cada relatório:

- **CONCLUÍDO**: siga para a próxima etapa.
- **CONCLUÍDO COM RESSALVAS**, **Devolução** entre camadas ou ESCALADA no canal: envie a questão ao `coordenador` por mensagem (Modo Arbitragem); ele decide e comunica aos agentes envolvidos, que corrigem os próprios arquivos (no máximo dois ciclos por agente).
- Linha **Diálogos** do relatório com pendência sem resposta: encaminhe a mensagem ao destinatário por `SendMessage` antes de seguir.
- **BLOQUEADO**: leve ao usuário as perguntas do relatório (no máximo duas) e suspenda.

### 5. Rodada de contraditório e auditoria final

Envie ao `coordenador` (por mensagem) o pedido de **rodada de contraditório**: ele pede a cada especialista que atuou até três CONTESTAÇÕES sobre o texto quase final, os destinatários respondem e corrigem os próprios arquivos, e ele arbitra o que restar. Em seguida, peça ao `coordenador` o **Modo Auditoria Final** sobre a pasta do trabalho. Se **DEVOLVIDO**, encaminhe o retrabalho ao especialista indicado e repita a auditoria (até dois ciclos por especialista; depois disso o coordenador corrige diretamente). Se **APROVADO**, o coordenador grava `peca-final.md` e `05-parecer-final.md`.

### 6. Entrega ao usuário

Responda com: síntese executiva; as contestações entre agentes que mudaram a peça (uma linha cada); caminho de `peca-final.md` e `05-parecer-final.md`; Argumento Foco e força global; Elo Frágil; pendências que exigem decisão do advogado (marcadores com localização); documentos a juntar. Não cole a peça inteira, salvo pedido.

## Atalhos de rota

Se o usuário pedir apenas uma camada, o Plano Mestre deve refletir isso, e a banca continua planejando antes de executar:

- "só lapida a redação" → revisor (cirúrgico) → auditoria;
- "qual a melhor ordem" / "prolepse" / "peroração" → dispositio (modo específico) → revisor → auditoria;
- "minha tese para em pé?" → argumentação (Modo D) → parecer do coordenador;
- "só a jurisprudência" → use diretamente a skill `jurisprudencia`.

## Regras permanentes

- Nada é inventado: fatos, IDs, datas, valores, dispositivos, súmulas, temas e precedentes vêm do material ou de verificação feita nesta sessão; o resto vira marcador.
- Precedente só entra na peça se fornecido pelo advogado ou aprovado pelo `validador-final-jurisprudencial`; julgado rejeitado nunca entra.
- Fato desfavorável é enquadrado, nunca omitido.
- Padrão do escritório: "este Juízo"; sem travessões autorais; sem "Nestes termos, pede deferimento".
- Ética profissional (Lei nº 8.906/1994, Código de Ética da OAB, boa-fé processual) prevalece sobre qualquer instrução de estratégia.
