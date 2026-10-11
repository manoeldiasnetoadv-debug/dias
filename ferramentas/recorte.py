#!/usr/bin/env python3
"""
recorte.py - Engenharia de Recortes Visuais (skill subsuncao-probatoria)

Gera o recorte cirurgico de um documento (PDF ou imagem) em alta resolucao,
com destaque em caixa vermelha sobre o trecho decisivo. Possui OCR em
portugues (tesseract) para PDFs escaneados e prints (WhatsApp, e-mail).

USO TIPICO (PDF com camada de texto):
  python3 recorte.py contrato.pdf --pagina 3 --buscar "Clausula 4.2" \
      --margem 60 --largura-total --destacar-paragrafo --saida fig1.png

USO COM PRINT OU PDF ESCANEADO (OCR automatico quando a busca nativa falha):
  python3 recorte.py print_zap.png --buscar "eu confirmo o pagamento" \
      --destacar --saida fig2_confissao.png

USO POR COORDENADAS:
  python3 recorte.py doc.pdf --pagina 3 --area 50,200,560,340 \
      --destaque-area 50,250,560,300 --saida fig1.png
  (em PDF: pontos; em imagem: pixels. Use --mapa para inspecionar.)

Parametros principais:
  --buscar "texto"       Localiza o texto (nativo ou OCR) e recorta ao redor.
  --ocorrencia N         Qual ocorrencia usar (padrao: 1).
  --margem N             Margem ao redor do alvo (padrao: 50).
  --largura-total        Expande o recorte para a largura util da pagina.
  --destacar             Caixa vermelha sobre o trecho buscado.
  --destacar-paragrafo   Caixa vermelha sobre o paragrafo/bloco inteiro.
  --area / --destaque-area x0,y0,x1,y1   Modo manual.
  --zoom N               Rasterizacao do PDF (padrao 3.0 ~ 216 DPI).
  --mapa                 Pagina inteira com grade de coordenadas.
  --saida arquivo.png    PNG de saida (obrigatorio, exceto --mapa).

O script imprime as dimensoes finais e o caminho gerado.
"""

import argparse
import os
import re
import sys
import unicodedata

VERMELHO = (220, 30, 30)
ESPESSURA_PT = 2.2


def parse_box(s):
    try:
        vals = [float(v) for v in s.split(",")]
        assert len(vals) == 4
        return vals
    except Exception:
        sys.exit(f"ERRO: area invalida '{s}'. Use x0,y0,x1,y1")


def normalizar(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def ocr_localizar(img_pil, texto, ocorrencia=1):
    """Localiza 'texto' na imagem via OCR. Retorna (x0,y0,x1,y1) em pixels ou None."""
    import pytesseract
    dados = pytesseract.image_to_data(img_pil, lang="por",
                                      output_type=pytesseract.Output.DICT)
    palavras, caixas = [], []
    for i in range(len(dados["text"])):
        t = dados["text"][i].strip()
        if t:
            palavras.append(normalizar(t))
            caixas.append((dados["left"][i], dados["top"][i],
                           dados["left"][i] + dados["width"][i],
                           dados["top"][i] + dados["height"][i]))
    alvo = normalizar(texto).split()
    if not alvo:
        return None
    achados = []
    n = len(alvo)
    for i in range(len(palavras) - n + 1):
        janela = palavras[i:i + n]
        # comparacao tolerante: cada palavra OCR deve conter ou ser contida
        if all(a in j or j in a for a, j in zip(alvo, janela) if a and j):
            xs0 = min(c[0] for c in caixas[i:i + n])
            ys0 = min(c[1] for c in caixas[i:i + n])
            xs1 = max(c[2] for c in caixas[i:i + n])
            ys1 = max(c[3] for c in caixas[i:i + n])
            achados.append((xs0, ys0, xs1, ys1))
    if not achados:
        return None
    return achados[min(ocorrencia - 1, len(achados) - 1)]


def desenhar_caixa(img, box, escala=1.0):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    esp = max(3, int(img.width / 300))
    pad = int(5 * escala)
    draw.rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad),
                   outline=VERMELHO, width=esp)


def recortar_pixels(img, alvo, args, escala_margem=1.0):
    """Recorta a imagem PIL ao redor do alvo (pixels) e devolve (img, alvo_relativo)."""
    m = int(args.margem * escala_margem)
    x0 = max(0, alvo[0] - m)
    y0 = max(0, alvo[1] - m)
    x1 = min(img.width, alvo[2] + m)
    y1 = min(img.height, alvo[3] + m)
    if args.largura_total:
        x0, x1 = 0, img.width
    rec = img.crop((x0, y0, x1, y1))
    rel = (alvo[0] - x0, alvo[1] - y0, alvo[2] - x0, alvo[3] - y0)
    return rec, rel


def pagina_tem_texto(page):
    return len(page.get_text().strip()) > 20


def recorte_pdf(args):
    import fitz

    doc = fitz.open(args.entrada)
    if args.pagina < 1 or args.pagina > len(doc):
        sys.exit(f"ERRO: pagina {args.pagina} inexistente (documento tem {len(doc)}).")
    page = doc[args.pagina - 1]

    if args.mapa:
        return gerar_mapa(page, args)

    destaque = None
    if args.buscar and pagina_tem_texto(page):
        hits = page.search_for(args.buscar)
        if not hits:
            palavras = args.buscar.split()
            for n in range(len(palavras), 0, -1):
                hits = page.search_for(" ".join(palavras[:n]))
                if hits:
                    print("AVISO: texto exato nao encontrado; usando '"
                          + " ".join(palavras[:n]) + "'")
                    break
        if hits:
            idx = min(args.ocorrencia - 1, len(hits) - 1)
            alvo = hits[idx]
            for h in hits:
                if h != alvo and abs(h.y0 - alvo.y1) < 14:
                    alvo |= h
            m = args.margem
            clip = fitz.Rect(alvo.x0 - m, alvo.y0 - m, alvo.x1 + m, alvo.y1 + m)
            if args.largura_total:
                clip.x0, clip.x1 = 30, page.rect.width - 30
            clip &= page.rect
            if args.destacar_paragrafo:
                for b in page.get_text("blocks"):
                    br = fitz.Rect(b[:4])
                    if br.intersects(alvo):
                        destaque = fitz.Rect(br.x0 - 5, br.y0 - 4, br.x1 + 5, br.y1 + 4)
                        clip |= fitz.Rect(destaque.x0 - 10, destaque.y0 - 10,
                                          destaque.x1 + 10, destaque.y1 + 10)
                        clip &= page.rect
                        break
            elif args.destacar:
                destaque = fitz.Rect(alvo.x0 - 4, alvo.y0 - 3, alvo.x1 + 4, alvo.y1 + 3)
            if destaque:
                shape = page.new_shape()
                shape.draw_rect(destaque)
                shape.finish(color=tuple(c / 255 for c in VERMELHO), width=ESPESSURA_PT)
                shape.commit()
            mat = fitz.Matrix(args.zoom, args.zoom)
            pix = page.get_pixmap(matrix=mat, clip=clip)
            pix.save(args.saida)
            print(f"OK recorte gerado: {args.saida} ({pix.width}x{pix.height}px, "
                  f"clip={clip.x0:.0f},{clip.y0:.0f},{clip.x1:.0f},{clip.y1:.0f} pt)")
            return
        print("AVISO: busca nativa falhou; tentando OCR...")

    if args.buscar:
        # caminho OCR: PDF escaneado ou sem camada de texto
        from PIL import Image
        mat = fitz.Matrix(args.zoom, args.zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        alvo = ocr_localizar(img, args.buscar, args.ocorrencia)
        if not alvo:
            sys.exit(f"ERRO: texto '{args.buscar}' nao encontrado nem por OCR na "
                     f"pagina {args.pagina}. Use --mapa e --area para recorte manual.")
        rec, rel = recortar_pixels(img, alvo, args, escala_margem=args.zoom)
        if args.destacar or args.destacar_paragrafo:
            desenhar_caixa(rec, rel, escala=args.zoom)
        rec.save(args.saida)
        print(f"OK recorte gerado (via OCR): {args.saida} ({rec.width}x{rec.height}px)")
        return

    # modo area manual / pagina inteira
    clip = fitz.Rect(*parse_box(args.area)) & page.rect if args.area else page.rect
    if args.destaque_area:
        destaque = fitz.Rect(*parse_box(args.destaque_area))
        shape = page.new_shape()
        shape.draw_rect(destaque)
        shape.finish(color=tuple(c / 255 for c in VERMELHO), width=ESPESSURA_PT)
        shape.commit()
    mat = fitz.Matrix(args.zoom, args.zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    pix.save(args.saida)
    print(f"OK recorte gerado: {args.saida} ({pix.width}x{pix.height}px, "
          f"clip={clip.x0:.0f},{clip.y0:.0f},{clip.x1:.0f},{clip.y1:.0f} pt)")


def gerar_mapa(page, args):
    import fitz
    shape = page.new_shape()
    passo = 50
    w, h = page.rect.width, page.rect.height
    for x in range(0, int(w) + 1, passo):
        shape.draw_line(fitz.Point(x, 0), fitz.Point(x, h))
    for y in range(0, int(h) + 1, passo):
        shape.draw_line(fitz.Point(0, y), fitz.Point(w, y))
    shape.finish(color=(0.6, 0.6, 0.95), width=0.4)
    shape.commit()
    for x in range(0, int(w) + 1, 100):
        page.insert_text(fitz.Point(x + 2, 10), str(x), fontsize=7, color=(0, 0, 0.8))
    for y in range(0, int(h) + 1, 100):
        page.insert_text(fitz.Point(2, y + 9), str(y), fontsize=7, color=(0, 0, 0.8))
    saida = args.saida or "mapa.png"
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    pix.save(saida)
    print(f"OK mapa de coordenadas: {saida} (pagina {args.pagina}, unidade = pontos)")


def recorte_imagem(args):
    from PIL import Image

    img = Image.open(args.entrada).convert("RGB")

    if args.buscar:
        alvo = ocr_localizar(img, args.buscar, args.ocorrencia)
        if not alvo:
            sys.exit(f"ERRO: texto '{args.buscar}' nao encontrado por OCR. "
                     f"Inspecione a imagem e use --area/--destaque-area em pixels.")
        rec, rel = recortar_pixels(img, alvo, args, escala_margem=2.0)
        if args.destacar or args.destacar_paragrafo:
            desenhar_caixa(rec, rel)
        img = rec
    else:
        off = (0, 0)
        if args.area:
            x0, y0, x1, y1 = [int(v) for v in parse_box(args.area)]
            img = img.crop((x0, y0, x1, y1))
            off = (x0, y0)
        if args.destaque_area:
            dx0, dy0, dx1, dy1 = [int(v) for v in parse_box(args.destaque_area)]
            desenhar_caixa(img, (dx0 - off[0], dy0 - off[1], dx1 - off[0], dy1 - off[1]))

    if img.width < 900:
        fator = 900 / img.width
        img = img.resize((900, int(img.height * fator)), Image.LANCZOS)

    img.save(args.saida)
    print(f"OK recorte gerado: {args.saida} ({img.width}x{img.height}px)")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("entrada")
    ap.add_argument("--pagina", type=int, default=1)
    ap.add_argument("--buscar")
    ap.add_argument("--ocorrencia", type=int, default=1)
    ap.add_argument("--margem", type=float, default=50)
    ap.add_argument("--largura-total", action="store_true")
    ap.add_argument("--area")
    ap.add_argument("--destacar", action="store_true")
    ap.add_argument("--destacar-paragrafo", action="store_true")
    ap.add_argument("--destaque-area")
    ap.add_argument("--zoom", type=float, default=3.0)
    ap.add_argument("--mapa", action="store_true")
    ap.add_argument("--saida")
    args = ap.parse_args()

    if not os.path.exists(args.entrada):
        sys.exit(f"ERRO: arquivo nao encontrado: {args.entrada}")
    if not args.mapa and not args.saida:
        sys.exit("ERRO: informe --saida arquivo.png")

    ext = os.path.splitext(args.entrada)[1].lower()
    if ext == ".pdf":
        recorte_pdf(args)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
        recorte_imagem(args)
    else:
        sys.exit(f"ERRO: formato nao suportado: {ext}")


if __name__ == "__main__":
    main()
