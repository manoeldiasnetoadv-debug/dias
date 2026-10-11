#!/usr/bin/env python3
"""Lint do cânone de redação Dias & Lucena.
Uso: python3 lint_redacao.py ARQUIVO [--registro peca|cliente]
Lê .txt, .md e .docx. Trecho entre aspas ou em linha iniciada por '>' é citação
literal: fica fora das regras de estilo. Sai com código 1 se houver crítico."""
import re, sys, zipfile, html, argparse

def ler(p):
    if p.lower().endswith('.docx'):
        xml = zipfile.ZipFile(p).read('word/document.xml').decode('utf8')
        ps = re.findall(r'<w:p[ >].*?</w:p>', xml, flags=re.S)
        return '\n'.join(html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x))) for x in ps)
    return open(p, encoding='utf-8').read()

def mascara(l):
    if l.lstrip().startswith('>'):
        return ''
    return re.sub(r'“[^”]*”|"[^"\n]*"|«[^»]*»', lambda m: ' ' * len(m.group()), l)

I = re.I
PAL = lambda s: re.compile(r'(?<![\wÀ-ú])(?:' + s + r')(?![\wÀ-ú])', I)
CRIT = [
 ('TRAVESSAO', re.compile(r'[—–]|(?<=\S) - (?=\S)'), 'travessão fora de citação: vírgula, parênteses, dois-pontos ou ponto'),
 ('VOCAB', PAL(r'cumpre (?:destacar|salientar|ressaltar|observar|registrar|consignar)|é imperioso|imperios[oa]s?|faz-se mister|mister|salutar|cristalin[oa]s?'
   r'|frise-se|vale dizer|insta (?:consignar|salientar|destacar|ressaltar)|no que tange|em sede de|a nível de|indubitavelmente|conclui-se,? portanto'
   r'|no presente caso|data m[áa]xima venia|outrossim|destarte|cediç[oa]|com efeito|resta (?:claro|evidente|cristalino|demonstrado|patente)'
   r'|hodiernamente|alhures|sobredit[oa]s?|supramencionad[oa]s?|supracitad[oa]s?|retromencionad[oa]s?|nesse diapasão|nessa toada|nessa esteira'), 'vocabulário vedado pelo cânone'),
 ('TAUTOLOGIA', PAL(r'nul[oa]s? e sem efeito|clar[oa] e evidente|just[oa]s? e contratad[oa]s?|verdadeira realidade|absolut[oa] e total|plenamente clar[oa]'
   r'|teto máximo|elo de ligação|há \w+ anos atrás|surpresa inesperada|certeza absoluta'), 'tautologia/pleonasmo'),
 ('METADISCURSO', PAL(r'passa-se a \w+|passamos a \w+|neste tópico|no presente tópico|a seguir (?:será|serão|se demonstrará)|(?:será|serão) demonstrad[oa]s?'
   r'|(?:como|conforme) se (?:verá|demonstrará)|cumpre agora|antes de adentrar|inicialmente, cabe|é o que se (?:passa a demonstrar|demonstrará)'), 'metadiscurso: trate do assunto diretamente'),
 ('FECHO', PAL(r'(?:nestes|nesses) termos|termos em que|pede (?:e espera )?deferimento'), 'fecho vedado pelo padrão do escritório'),
 ('O-MESMO', re.compile(r'(?<![\wÀ-ú])(?:o|a|os|as|do|da|dos|das|no|na|nos|nas|pelo|pela|pelos|pelas|ao|aos)\s+mesm[oa]s?(?=\s*(?:[,.;:)]|$|\s+(?:é|foi|era|será|está|estava|tem|teve|deve|pode|não|se|já|também|possui|apresentou|alegou|afirmou|requereu|recebeu|foi)\b))', I), '"o mesmo/a mesma" como pronome: use o substantivo ou pronome pessoal'),
 ('MESOCLISE', re.compile(r'\b\w+-(?:se|me|te|lhe|lhes|nos|vos|o|a|os|as|lo|la|los|las)-(?:ei|á|ás|ão|emos|eis|ia|ias|íamos|íeis|iam)\b', I), 'mesóclise: reestruture a frase (não troque por próclise inicial)'),
]
PECA_CRIT = [
 ('PRONOME-INICIAL', re.compile(r'(?:^|[.!?:]\s+)(?:(?:Me|Te|Lhe|Lhes)(?=\s+[a-zà-ú])|Se\s+(?:vê|verifica|nota|percebe|constata|observa|trata|infere|depreende|extrai|evidencia|mostra|revela|impõe)\b|Nos\s+(?:parece|interessa|cabe|resta|compete)\b)'), 'período iniciado por pronome átono (só admitido em e-mail/cliente)'),
 ('EXCLAMACAO', re.compile(r'!'), 'exclamação em peça'),
]
ADJ = r'\w+(?:ivo|iva|ivos|ivas|ado|ada|ados|adas|ido|ida|idos|idas|ente|entes|ante|antes|al|ais|oso|osa|osos|osas|ável|áveis|ível|íveis|ico|ica|icos|icas|ório|ória|ário|ária|ários|árias|ar|ares)'
AVIS = [
 ('IA-PARALELISMO', re.compile(r'\bnão se trata(?:va)? (?:de|apenas|somente|só)\b|\bnão (?:apenas|somente|só)\b[^.;]{0,120}?\b(?:mas|como) também\b|\bmais do que (?:um|uma|mer[oa]|simples)\b'
   r'|\bnão (?:é|foi|era|são|será|está)\b[^.;:!?—–]{1,80}[.;,—–]\s+(?:é|foi|era|são|será|está)\b|,\s+e não\s+\w+|,\s+não\s+(?:um |uma |mer[oa] )?' + ADJ + r'[.;]', I), 'paralelismo negativo: afirme o que é, sem o contraste montado'),
 ('IA-GERUNDIO', re.compile(r',\s+(?:evidenciando|demonstrando|revelando|reforçando|confirmando|comprovando|ressaltando|denotando|sinalizando|corroborando|esvaziando)\b|,\s+o que (?:demonstra|evidencia|revela|reforça|confirma|comprova|denota|corrobora|esvazia)\b', I), 'gerúndio/cláusula conclusiva: frase nova com sujeito e verbo, ou corte'),
 ('IA-TRIADE', re.compile(r'\b' + ADJ + r',\s+' + ADJ + r',?\s+e\s+(?:\w+mente\s+)?' + ADJ + r'\b', I), 'tríade de qualificadores: fique com o que a prova sustenta'),
 ('IA-VOCAB', PAL(r'robust[oa]s?|crucia(?:l|is)|cenário|nuances?|pila(?:r|res)|de (?:forma|modo|maneira) inequívoc[oa]|inequivocamente|salta aos olhos|vale (?:ressaltar|destacar|lembrar|registrar)'
   r'|(?:é )?importante (?:ressaltar|destacar|notar|frisar|registrar)|irrefutáve(?:l|is)|inquestionáve(?:l|is)|incontestáve(?:l|is)|indiscutíve(?:l|is)'
   r'|flagrante(?:mente)?|patente|notadamente|em última análise|no cerne|(?:é|são|mostra-se|revela-se|afigura-se) (?:fundamenta(?:l|is)|essencia(?:l|is)|crucia(?:l|is))'
   r'|ou seja|em outras palavras|dito de outro modo|vejamos|não há (?:que se )?falar|(?:não )?merece prosperar|avença'), 'marca de IA ou juridiquês de muleta'),
 ('INTENSIFICADOR', PAL(r'muito|extremamente|absolutamente|realmente|literalmente|totalmente|completamente|verdadeir[oa]s?(?=\s+[a-zà-ú]{3,})|sobremaneira|deveras|\w+íssim[oa]s?|probleminha|minutinho'), 'intensificador/superlativo: troque por dado ou palavra exata'),
 ('BAJULACAO', PAL(r'dout[oa]s?|ilustres?|egrégi[oa]s?|colend[oa]s?|brilhante(?:mente)?|respeitáve(?:l|is)|eminentes?|preclar[oa]s?|insignes?|digníssim[oa]s?|Excelentíssim[oa]s?|Meritíssim[oa]s?|[rv]\. (?:sentença|decisão|acórdão|despacho)'), 'reverência: só no vocativo/endereçamento protocolar'),
 ('FORMATO', re.compile(r'§\d|(?:art\.?|§)\s*\d+°|\bn°|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b', I), 'formato: "§ 3º" com espaço, "º" (não "°"), "nº", data por extenso ou dd/mm/aaaa'),
]
PECA_AVIS = [('TRATAMENTO', re.compile(r'Vossa Excelência|V\. ?Ex[aª]\.?'), 'padrão do escritório: "este Juízo" (ou "esta Câmara", "esta Turma")')]
FORMULA = re.compile(r'\b(?:A questão é (?:simples|esta)|O ponto (?:controvertido |central |decisivo )?é (?:este|simples)|é (?:claro|expresso|categórico|taxativo|simples)|Explica-se|Explico|Em síntese|Em suma|Confira-se|Veja-se)\s*:', I)
CONECT = re.compile(r'\b(?:Ademais|Nesse sentido|Neste sentido|Dessa forma|Desse modo|Dessa maneira|Por sua vez|Além disso|Assim sendo|Nessa linha|Nessa perspectiva|Sob essa ótica)\b')
PEND = re.compile(r'\[(?:VERIFICAR|PREENCHER|CONFIRMAR|QUEM|DATA|VALOR|Id\.|fl\.|Doc\.)[^\]]*\]|_{3,}', I)
HEAD = re.compile(r'^\s*(?:#{1,6}\s|\*\*[^*]+\*\*\s*$|[IVXLC]+\s*[.\-–)]\s|\d+(?:\.\d+)*\.?\s+[A-ZÁÉÍÓÚ][^.]*$|[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 ,:;()\-–ºª§.]{12,}$)')
ABREV = re.compile(r'\b(?:arts?|fls?|Id|nº|Rel|Min|Des|j|p|pp|ex|Dr|Dra|Sr|Sra|cf|inc|al|Doc|ss|Exa|Ex|Proc|Ag|Resp|REsp|RE|AgInt|EDcl|Rcl)\.|\d\.\d')

def trecho(l, m, r=45):
    a, b = max(0, m.start() - r), min(len(l), m.end() + r)
    return ('…' if a else '') + l[a:b].strip() + ('…' if b < len(l) else '')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('arquivo'); ap.add_argument('--registro', default='peca', choices=['peca', 'cliente'])
    a = ap.parse_args(); peca = a.registro == 'peca'
    linhas = ler(a.arquivo).split('\n'); out = {'CRÍTICO': [], 'AVISO': [], 'PENDÊNCIA': []}
    crit = CRIT + (PECA_CRIT if peca else []); avis = AVIS + (PECA_AVIS if peca else [])
    formulas, conect, negritos, secao = [], {}, 0, 1
    lim_frase = 45 if peca else 35
    for n, bruta in enumerate(linhas, 1):
        l = mascara(bruta)
        for m in PEND.finditer(bruta): out['PENDÊNCIA'].append(f'L{n} {m.group()}: listar em Pontos de atenção')
        if not l.strip(): continue
        st = bruta.strip()
        titulo = (bool(HEAD.match(bruta)) and len(st.split()) <= 25) or (len(st.split()) <= 15 and st[:1].isupper() and not re.search(r'[.:;!?,)\]]$', st) and not st.startswith(('-', '*', '>')))
        if titulo:
            negritos = 0
            ws = [w for w in re.findall(r'[A-Za-zÀ-ú]+', bruta) if len(w) > 3]
            if ws and not bruta.isupper() and sum(w[0].isupper() for w in ws) / len(ws) >= .6 and len(ws) >= 3:
                out['AVISO'].append(f'L{n} [TITLE-CASE] título com iniciais maiúsculas em todas as palavras: só a primeira e nomes próprios')
        for sev, regras in (('CRÍTICO', crit), ('AVISO', avis)):
            for cod, rx, msg in regras:
                if titulo and cod in ('EXCLAMACAO', 'IA-PARALELISMO'): continue
                ms = list(rx.finditer(l))
                if ms:
                    termos = sorted({m.group().strip(' .!?:,').lower() for m in ms})
                    out[sev].append(f'L{n} [{cod}] {msg} ({", ".join(termos)}): "{trecho(bruta, ms[0])}"')
        formulas += [(n, m.group()) for m in FORMULA.finditer(l)]
        for m in CONECT.finditer(l): conect.setdefault(m.group(), []).append(n)
        if not titulo:
            negritos += len(re.findall(r'\*\*[^*]+\*\*', bruta))
            if negritos > 1: out['AVISO'].append(f'L{n} [NEGRITO] mais de um destaque em negrito no tópico'); negritos = -99
            if re.search(r'[a-zà-ú]', l) and re.search(r'(?:\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{4,}\b\s+){2}\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{4,}\b', l):
                out['AVISO'].append(f'L{n} [CAIXA-ALTA] caixa alta no corpo do texto')
            palavras = len(l.split())
            if palavras > 150: out['AVISO'].append(f'L{n} [PARAGRAFO] parágrafo com {palavras} palavras: divida por função')
            for f in re.split(r'[.!?;]\s+', ABREV.sub(lambda m: m.group().replace('.', '§§'), l)):
                if len(f.split()) > lim_frase: out['AVISO'].append(f'L{n} [FRASE] frase com {len(f.split())} palavras: "{f.strip()[:70]}…"')
    if len(formulas) > 1:
        out['AVISO'].append('[FORMULA] fórmulas de dois-pontos acima de 1 por peça: ' + '; '.join(f'L{n} "{t}"' for n, t in formulas))
    for c, ns in conect.items():
        if len(ns) >= 3: out['AVISO'].append(f'[CONECTIVO] "{c}" {len(ns)}x (L{", L".join(map(str, ns))}): costure pela ideia, não pelo conectivo')
    if sum(len(v) for v in conect.values()) >= 6: out['AVISO'].append('[CONECTIVO] conectivos de muleta em excesso no texto inteiro')
    print(f'LINT redação · {a.arquivo} · registro: {a.registro}')
    for sev, itens in out.items():
        if itens: print(f'\n{sev} ({len(itens)})'); [print('  ' + i) for i in itens]
    c = len(out['CRÍTICO'])
    print(f"\nResultado: {c} crítico(s), {len(out['AVISO'])} aviso(s), {len(out['PENDÊNCIA'])} pendência(s). " + ('REPROVADO' if c else 'APROVADO'))
    sys.exit(1 if c else 0)

if __name__ == '__main__':
    main()
