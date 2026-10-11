#!/usr/bin/env python3
"""
confronto.py - Quadro de confronto de provas (skill subsuncao-probatoria)

Compoe dois recortes em um quadro unico de confronto visual, com rotulos,
para demonstrar contradicao entre o que a parte alegou e o que o documento
prova. Arma tipica de impugnacao por litigancia de ma-fe.

USO:
  python3 confronto.py recorte_alegacao.png recorte_prova.png \
      --rotulo1 "O que o Autor alegou (ID 111)" \
      --rotulo2 "O que o documento prova (ID 222)" \
      --saida fig3_confronto.png

  --vertical    empilha em vez de lado a lado (melhor para recortes largos)
"""

import argparse
import sys

CINZA_ESCURO = (64, 64, 64)        # #404040 identidade Dias & Lucena
AZUL = (31, 58, 95)                # #1F3A5F
VERMELHO = (180, 30, 30)
FUNDO = (255, 255, 255)
BORDA = (200, 200, 200)


def carregar_fonte(tam):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, tam)
        except Exception:
            continue
    return ImageFont.load_default()


def main():
    from PIL import Image, ImageDraw

    ap = argparse.ArgumentParser()
    ap.add_argument("img1")
    ap.add_argument("img2")
    ap.add_argument("--rotulo1", default="Versao alegada")
    ap.add_argument("--rotulo2", default="O que o documento prova")
    ap.add_argument("--vertical", action="store_true")
    ap.add_argument("--saida", required=True)
    args = ap.parse_args()

    a = Image.open(args.img1).convert("RGB")
    b = Image.open(args.img2).convert("RGB")

    # normaliza dimensoes
    if args.vertical:
        alvo_w = max(a.width, b.width)
        a = a.resize((alvo_w, int(a.height * alvo_w / a.width)), Image.LANCZOS)
        b = b.resize((alvo_w, int(b.height * alvo_w / b.width)), Image.LANCZOS)
    else:
        alvo_h = min(max(a.height, b.height), 1200)
        a = a.resize((int(a.width * alvo_h / a.height), alvo_h), Image.LANCZOS)
        b = b.resize((int(b.width * alvo_h / b.height), alvo_h), Image.LANCZOS)

    pad = 30
    faixa = 70
    fonte = carregar_fonte(34)

    def painel(img, rotulo, cor):
        p = Image.new("RGB", (img.width + 2, img.height + faixa + 2), FUNDO)
        d = ImageDraw.Draw(p)
        d.rectangle((0, 0, p.width - 1, faixa - 8), fill=cor)
        bb = d.textbbox((0, 0), rotulo, font=fonte)
        d.text(((p.width - (bb[2] - bb[0])) / 2, (faixa - 8 - (bb[3] - bb[1])) / 2 - bb[1]),
               rotulo, font=fonte, fill=(255, 255, 255))
        p.paste(img, (1, faixa))
        d.rectangle((0, faixa - 1, p.width - 1, p.height - 1), outline=BORDA, width=2)
        return p

    p1 = painel(a, args.rotulo1, CINZA_ESCURO)
    p2 = painel(b, args.rotulo2, AZUL)

    if args.vertical:
        W = max(p1.width, p2.width) + 2 * pad
        H = p1.height + p2.height + 3 * pad
        quadro = Image.new("RGB", (W, H), FUNDO)
        quadro.paste(p1, ((W - p1.width) // 2, pad))
        quadro.paste(p2, ((W - p2.width) // 2, p1.height + 2 * pad))
    else:
        W = p1.width + p2.width + 3 * pad
        H = max(p1.height, p2.height) + 2 * pad
        quadro = Image.new("RGB", (W, H), FUNDO)
        quadro.paste(p1, (pad, (H - p1.height) // 2))
        quadro.paste(p2, (p1.width + 2 * pad, (H - p2.height) // 2))

    quadro.save(args.saida)
    print(f"OK quadro de confronto: {args.saida} ({quadro.width}x{quadro.height}px)")


if __name__ == "__main__":
    main()
