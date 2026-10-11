---
name: banca
description: "Aciona a banca de aprimoramento de textos jurídicos do escritório (advogado sênior coordenador + argumentador jurídico + estrategista de argumentação + arquiteto de dispositio + revisor de redação impecável + auditor probatório + núcleo de jurisprudência), com planejamento minucioso antes de qualquer atividade. USE quando o usuário pedir para aprimorar, fortalecer, blindar, reorganizar ou lapidar peça, tópico, tese ou texto jurídico com a banca, ou disser \"/banca\", \"aciona a banca\", \"passa pela banca\", \"multiagentes\", \"time de agentes\", \"revisão completa da peça\". Argumento opcional: \"plano\" para parar após o Plano Mestre e aguardar aprovação."
---

# Banca de aprimoramento de textos jurídicos

Você (a sessão principal) conduz a banca em nome do **advogado sênior coordenador**. Os subagentes não acionam uns aos outros: é você quem os chama, um de cada vez, na ordem do Plano Mestre, e quem leva cada relatório ao coordenador quando há dúvida ou devolução.

Agentes (em `.claude/agents/`):

- `advogado-senior-coordenador`: planeja (Modo Planejamento), audita e consolida (Modo Auditoria Final).
- `argumentador-juridico`: construção da argumentação completa a partir da base crua (skill `argumentador-juridico`).
- `estrategista-argumentacao`: substância e blindagem (skill `argumentacao-estrategica`).
- `arquiteto-dispositio`: ordem e arquitetura (skill `dispositio-estrategica`).
- `revisor-redacao-impecavel`: prosa e cânone (skill `redacao-impecavel`), com lint em `ferramentas/lint_redacao.py`.
- `auditor-probatorio`: prova documental, Fase I (auditoria documental) e Fase II (subsunção probatória com recortes), com `ferramentas/auditdoc.py`, `recorte.py` e `confronto.py`.
- Núcleo de jurisprudência: `pesquisador-jurisprudencial` → `refinador-critico-jurisprudencial` → `validador-final-jurisprudencial` (fluxo detalhado na skill `jurisprudencia`).

## Fluxo obrigatório

Cada passo depende do anterior: aguarde a conclusão de cada subagente antes do próximo (não os deixe correndo em paralelo, salvo etapas que o Plano Mestre declare independentes).

### 1. Recepção

Reúna o material do usuário (texto colado, arquivo no repositório, anexos). Se o texto veio colado, grave-o integralmente; não resuma nem edite. Não faça perguntas se o material permitir trabalhar; se faltar a própria peça, a tese, o fato nuclear ou o pedido, pergunte no máximo duas coisas.

### 2. Planejamento (antes de qualquer execução)

Acione `advogado-senior-coordenador` em **Modo Planejamento**, entregando o material integral e pedindo que crie a pasta `trabalhos/AAAA-MM-DD-<slug>/`, grave `00-briefing.md` e `01-plano-mestre.md` (Fases 0 e 1). Ao receber o retorno:

- confira que `01-plano-mestre.md` existe e contém rota, encargos com critérios de aceite e cronograma;
- informe ao usuário, em poucas linhas, o diagnóstico, a rota escolhida e o provável Elo Frágil;
- se o argumento da skill for `plano`, ou se o usuário pediu para aprovar o plano, **pare aqui** e aguarde. Caso contrário, prossiga.

### 3. Auditoria probatória e núcleo de jurisprudência (quando o Plano Mestre indicar)

Se houver documentos relevantes, acione o `auditor-probatorio` na **Fase I** antes de qualquer construção de tese; se houver prazo dos arts. 430 ou 437 do CPC em curso, informe o usuário imediatamente. A **Fase II** (subsunção, recortes e legendas) é acionada depois do `arquiteto-dispositio` e antes do `revisor-redacao-impecavel`.

#### Núcleo de jurisprudência

Se o Plano Mestre listar questões para o núcleo, execute o fluxo da skill `jurisprudencia` (pesquisador, refinador e validador, em sequência, cada um planejando antes de executar) sobre a mesma pasta do trabalho, antes da argumentação. O `parecer_jurisprudencial.md` passa a ser leitura obrigatória do `argumentador-juridico` e do `estrategista-argumentacao`. Se depois um especialista devolver pedido de nova pesquisa, rode o núcleo com escopo restrito à questão nova.

### 4. Execução pelos especialistas

Para cada etapa do cronograma do Plano Mestre, acione o especialista indicado usando o modelo "ENCARGO DA BANCA" do plano (pasta, arquivos a ler, objetivo, modo, decisões vinculantes, critérios de aceite, arquivo de saída). Reforce sempre: **registrar o Plano de trabalho no topo do arquivo de saída antes de executar** e encerrar com o RELATÓRIO padronizado.

Depois de cada relatório:

- **CONCLUÍDO**: siga para a próxima etapa.
- **CONCLUÍDO COM RESSALVAS** ou **Devolução** entre camadas: acione o coordenador (Modo Auditoria Final, escopo restrito à questão) para arbitrar; aplique a decisão (retrabalho do especialista indicado, no máximo dois ciclos).
- **BLOQUEADO**: leve ao usuário as perguntas do relatório (no máximo duas) e suspenda.

### 5. Auditoria final

Acione `advogado-senior-coordenador` em **Modo Auditoria Final** sobre a pasta do trabalho. Se **DEVOLVIDO**, encaminhe o retrabalho ao especialista indicado e repita a auditoria (até dois ciclos por especialista; depois disso o coordenador corrige diretamente). Se **APROVADO**, o coordenador grava `peca-final.md` e `05-parecer-final.md`.

### 6. Entrega ao usuário

Responda com: síntese executiva; caminho de `peca-final.md` e `05-parecer-final.md`; Argumento Foco e força global; Elo Frágil; pendências que exigem decisão do advogado (marcadores com localização); documentos a juntar. Não cole a peça inteira, salvo pedido.

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
