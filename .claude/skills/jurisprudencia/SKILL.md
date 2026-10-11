---
name: jurisprudencia
description: "Aciona o NÚCLEO DE JURISPRUDÊNCIA da banca (pesquisador-jurisprudencial → refinador-critico-jurisprudencial → validador-final-jurisprudencial) para pesquisar, criticar e validar precedentes sobre uma questão jurídica, com planejamento antes de cada etapa. USE quando o usuário pedir pesquisa de jurisprudência ou de precedentes, disser \"/jurisprudencia\", \"pesquisa jurisprudencial\", \"ache precedentes\", \"tem julgado do STJ sobre\", \"precedente contrário\", \"valide esta jurisprudência\", \"confira este precedente\", ou entregar questão jurídica e documentos pedindo o parecer jurisprudencial."
---

# Núcleo de jurisprudência

Você (a sessão principal) conduz o núcleo em nome do `advogado-senior-coordenador`. As três etapas são sequenciais: cada uma lê a saída da anterior, então aguarde a conclusão de cada subagente antes de acionar o próximo.

Acione cada um com o nome fixo (`name`: `pesquisador`, `refinador`, `validador`) para que conversem entre si por `SendMessage`, conforme `.claude/banca/protocolo-dialogo.md`: o refinador consulta o pesquisador sobre a trilha de fonte, o validador resolve divergências consultando os dois. Crie `canal-da-banca.md` na pasta do caso, se não existir. Dúvida posterior com um agente que já concluiu vai por mensagem, sem novo acionamento.

## Fluxo

### 1. Recepção e pasta

Reúna a questão jurídica, a peça e os documentos. Use a pasta do trabalho da banca, se existir (`trabalhos/<caso>/`); caso contrário, crie `trabalhos/AAAA-MM-DD-<slug>/` e grave em `00-briefing.md` o material recebido, sem editar. As saídas do núcleo ficam em `trabalhos/<caso>/jurisprudencia/`.

Se faltar a própria questão jurídica, pergunte (no máximo duas perguntas). Fatos ausentes não travam a pesquisa: viram limitação declarada.

### 2. Pesquisa

Acione `pesquisador-jurisprudencial` com: pasta do trabalho, questão(ões) jurídica(s), fase processual, via e tribunal de destino, fatos comprovados com ID, tese do cliente e tese contrária conhecida. Exija o Plano de pesquisa antes das buscas e a entrega em `jurisprudencia/01_pesquisa_bruta.md`.

### 3. Refinamento crítico

Acione `refinador-critico-jurisprudencial` sobre a pasta. Exija o Plano de refinamento e a entrega em `jurisprudencia/02_refinamento_critico.md`.

### 4. Validação final

Acione `validador-final-jurisprudencial` sobre a pasta. Exija o Plano de validação e as entregas `jurisprudencia/03_validacao_final.md` e `jurisprudencia/parecer_jurisprudencial.md`.

Se o validador apontar pendência que uma nova busca resolveria, acione de novo o pesquisador com escopo restrito a essa pendência e repita refinamento e validação só para os itens novos (no máximo um ciclo adicional).

### 5. Entrega ao usuário

Apresente o parecer de forma curta, separando **dado conferido**, **inferência** e **pendência**:

- precedentes aprovados (e aprovados com condição, com a condição);
- melhor precedente contrário e o tratamento recomendado;
- orientação atual do tribunal de destino, se identificada;
- cobertura da pesquisa e limitações (fontes inacessíveis);
- caminho de `parecer_jurisprudencial.md`.

Julgado rejeitado não aparece como fundamento sugerido.

## Integração com a banca

Quando o núcleo roda dentro do `/banca`, o parecer jurisprudencial é insumo do `estrategista-argumentacao`, que só usa precedentes aprovados (ou fornecidos pelo advogado) e trata o melhor precedente contrário na matriz de ataque.

## Regras permanentes

- Nada é inventado: julgado, número, relator, data, tese, trecho, URL ou conteúdo dos autos.
- Fontes oficiais confirmam; fontes secundárias só ajudam a descobrir.
- A pesquisa inclui precedentes contrários; os fatos comprovados do caso são o limite da comparação.
- Sem acesso à internet, o núcleo declara a limitação e lista as consultas a fazer, em vez de responder de memória.
