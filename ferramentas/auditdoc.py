#!/usr/bin/env python3
"""auditdoc — extração forense de metadados e validação de identificadores brasileiros.

Uso:
  python3 auditdoc.py meta ARQUIVO [ARQUIVO...]   # PDF, DOCX/XLSX, JPG/PNG/HEIC, TXT
  python3 auditdoc.py revisoes ARQUIVO.pdf         # separa revisões incrementais e compara o texto
  python3 auditdoc.py cpf 123.456.789-09
  python3 auditdoc.py cnpj 12.345.678/0001-95      # aceita CNPJ alfanumérico (jul/2026)
  python3 auditdoc.py nfe CHAVE_44_DIGITOS
  python3 auditdoc.py boleto LINHA_DIGITAVEL_OU_CODIGO_BARRAS
  python3 auditdoc.py pix ID_END_TO_END
  python3 auditdoc.py data 15/03/2021 [22/04/2021 ...]
Saída em texto; itens com "!!" são alertas a examinar, não conclusões.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import zipfile

ALERTA = "!!"


# ----------------------------------------------------------------- utilidades
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def pdf_date(s):
    """D:20210315143000-03'00' -> '2021-03-15 14:30:00 -03:00'."""
    if not s:
        return None
    s = str(s)
    m = re.match(r"D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?", s)
    if not m:
        return s
    y, mo, d, h, mi, se, tz, tzh, tzm = m.groups()
    out = f"{y}-{mo or '01'}-{d or '01'} {h or '00'}:{mi or '00'}:{se or '00'}"
    if tz in ("Z", "z"):
        out += " UTC"
    elif tz:
        out += f" {tz}{tzh or '00'}:{tzm or '00'}"
    return out


# ----------------------------------------------------------------------- PDF
def meta_pdf(path):
    from pypdf import PdfReader

    raw = open(path, "rb").read()
    r = {"tipo": "PDF"}
    r["versao_cabecalho"] = raw[:8].decode("latin-1", "ignore").strip()
    eofs = raw.count(b"%%EOF")
    r["marcadores_%%EOF"] = eofs
    r["secoes_xref/startxref"] = raw.count(b"startxref")
    alertas = []
    n_sig_bruto = raw.count(b"/ByteRange")
    if eofs > 1 and eofs - 1 > n_sig_bruto:
        alertas.append(f"{eofs} marcadores %%EOF e {n_sig_bruto} assinatura(s): há revisão incremental não explicada "
                       "por assinatura (edição, preenchimento ou anotação posterior à geração). Comparar revisões.")
    elif eofs > 1:
        r["obs_revisoes"] = f"{eofs - 1} revisão(ões) incremental(is), compatível(is) com o número de assinaturas"
    import shutil
    import subprocess
    if shutil.which("pdfsig"):
        try:
            out = subprocess.run(["pdfsig", path], capture_output=True, text=True, timeout=60).stdout.strip()
            if out and "does not contain any signatures" not in out:
                r["pdfsig(validação poppler)"] = out
                if "Signature is Invalid" in out:
                    alertas.append("pdfsig: ASSINATURA INVÁLIDA (conteúdo não corresponde ao que foi assinado).")
                if "Not total document signed" in out:
                    alertas.append("pdfsig: a assinatura não cobre o arquivo inteiro — houve acréscimo posterior à "
                                   "assinatura (pode ser outra assinatura legítima; comparar revisões).")
                if "isn't Trusted" in out or "not Trusted" in out:
                    r["obs_certificado"] = ("cadeia não reconhecida pelo poppler local — normal para ICP-Brasil; "
                                            "validar no Verificador do ITI (validar.iti.gov.br)")
        except Exception:
            pass
    try:
        rd = PdfReader(path, strict=False)
    except Exception as e:  # noqa
        r["erro"] = f"falha ao abrir com pypdf: {e}"
        alertas.append("Estrutura do PDF corrompida ou atípica (o leitor falhou). Pode ser dano na cópia, "
                       "geração por software incomum ou manipulação manual do arquivo — pedir o nativo.")
        if shutil.which("pdfinfo"):
            r["pdfinfo"] = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout.strip()
        return r, alertas
    if rd.is_encrypted:
        r["criptografado"] = True
        try:
            rd.decrypt("")
        except Exception:
            pass
    info = rd.metadata or {}
    r["info"] = {k.lstrip("/"): str(v) for k, v in info.items()} if info else {}
    cd, md = info.get("/CreationDate"), info.get("/ModDate")
    r["criacao"], r["modificacao"] = pdf_date(cd), pdf_date(md)
    if cd and md and pdf_date(md)[:19] < pdf_date(cd)[:19]:
        alertas.append(f"ModDate ({pdf_date(md)}) ANTERIOR à CreationDate ({pdf_date(cd)}): metadado impossível na "
                       "geração normal — indica edição manual de metadados, relógio adulterado ou regravação.")
    elif cd and md and str(cd)[:16] != str(md)[:16]:
        alertas.append(f"CreationDate ({pdf_date(cd)}) ≠ ModDate ({pdf_date(md)}): arquivo alterado após a geração.")
    prod = " | ".join(str(info.get(k, "")) for k in ("/Producer", "/Creator"))
    for sw in ("Photoshop", "GIMP", "Illustrator", "Inkscape", "PDFescape", "Sejda", "iLovePDF", "Smallpdf",
               "PDFelement", "Foxit PhantomPDF", "Nitro", "Canva", "PDF-XChange Editor", "Acrobat Pro",
               "LibreOffice Draw", "Wondershare"):
        if sw.lower() in prod.lower():
            alertas.append(f"Software de edição/manipulação no Producer/Creator: '{sw}'. Não é prova de fraude — "
                           "confrontar com a origem declarada do documento.")
    try:
        xmp = rd.xmp_metadata
        if xmp is not None:
            xr = {}
            for attr in ("xmp_create_date", "xmp_modify_date", "xmp_metadata_date", "xmp_creator_tool",
                         "pdf_producer", "xmpmm_document_id", "xmpmm_instance_id"):
                try:
                    v = getattr(xmp, attr)
                    if v:
                        xr[attr] = str(v)
                except Exception:
                    pass
            r["xmp"] = xr
            if xr.get("xmpmm_document_id") and xr.get("xmpmm_instance_id") and \
                    xr["xmpmm_document_id"].split(":")[-1] != xr["xmpmm_instance_id"].split(":")[-1]:
                alertas.append("XMP DocumentID ≠ InstanceID: o arquivo é uma versão derivada/salva de outro.")
    except Exception:
        pass
    r["paginas"] = len(rd.pages)
    tamanhos, fontes_pag, sem_texto, imagens = set(), [], [], 0
    obj_por_fonte = {}
    for i, p in enumerate(rd.pages, 1):
        mb = p.mediabox
        tamanhos.add((round(float(mb.width)), round(float(mb.height)), int(p.get("/Rotate", 0) or 0)))
        fs = set()
        try:
            res = p.get("/Resources") or {}
            res = res.get_object() if hasattr(res, "get_object") else res
            fonts = res.get("/Font") or {}
            fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
            nomes_pag = {}
            for ref in fonts.values():
                f = ref.get_object()
                nome = str(f.get("/BaseFont", "?"))
                fs.add(nome)
                oid = getattr(ref, "idnum", id(f))
                obj_por_fonte.setdefault(nome, set()).add(oid)
                nomes_pag.setdefault(nome, set()).add(oid)
            for nome, oids in nomes_pag.items():
                if len(oids) > 1 and "+" in nome:
                    alertas.append(f"Pág. {i}: a fonte embutida '{nome}' aparece em {len(oids)} objetos distintos NA "
                                   "MESMA PÁGINA — indício forte de sobreposição/inserção de texto posterior. "
                                   "Examinar a página (camadas de conteúdo, retângulos brancos, texto sobreposto).")
            xo = res.get("/XObject") or {}
            xo = xo.get_object() if hasattr(xo, "get_object") else xo
            for x in xo.values():
                if x.get_object().get("/Subtype") == "/Image":
                    imagens += 1
        except Exception:
            pass
        fontes_pag.append(sorted(fs))
        try:
            txt = (p.extract_text() or "").strip()
        except Exception:
            txt = ""
        if len(txt) < 20:
            sem_texto.append(i)
        if p.get("/Annots"):
            try:
                tipos = {str(a.get_object().get("/Subtype")) for a in p["/Annots"]}
                if tipos - {"/Link", "/Widget"}:
                    alertas.append(f"Pág. {i}: anotações sobrepostas {sorted(tipos)} — podem cobrir/alterar conteúdo visível.")
            except Exception:
                pass
    r["formatos_pagina(w,h,rot)"] = sorted(tamanhos)
    if len(tamanhos) > 1:
        alertas.append("Páginas com formatos/rotações diferentes: possível montagem a partir de fontes distintas.")
    r["imagens_embutidas"] = imagens
    r["paginas_sem_camada_de_texto"] = sem_texto
    todas = sorted({f for fs in fontes_pag for f in fs})
    r["fontes"] = todas
    subsets = {}
    for f in todas:
        m = re.match(r"/?([A-Z]{6})\+(.+)", f.lstrip("/"))
        if m:
            subsets.setdefault(m.group(2), set()).add(m.group(1))
    for base, prefs in subsets.items():
        if len(prefs) > 1:
            alertas.append(f"Fonte '{base}' embutida em {len(prefs)} subconjuntos distintos: indício típico de "
                           "texto inserido/editado depois (ou concatenação de arquivos). Localizar as páginas.")
    for nome, oids in obj_por_fonte.items():
        if len(oids) > 1 and "+" in nome and len(rd.pages) > 1:
            r.setdefault("fontes_embutidas_repetidas_no_arquivo", {})[nome] = len(oids)
    ref = fontes_pag[0] if fontes_pag else []
    destoantes = [i for i, fs in enumerate(fontes_pag, 1) if fs and ref and set(fs) != set(ref)]
    if destoantes and len(fontes_pag) > 1:
        r["paginas_com_fontes_diferentes_da_1a"] = destoantes
    # assinaturas digitais
    sigs = []
    try:
        for f in (rd.get_fields() or {}).values():
            if f.get("/FT") == "/Sig":
                v = f.get("/V")
                v = v.get_object() if v is not None else None
                if v is not None:
                    br = list(v.get("/ByteRange", []))
                    cobertura = (br[2] + br[3]) if len(br) == 4 else None
                    sigs.append({"nome": str(v.get("/Name", "")), "data": pdf_date(v.get("/M")),
                                 "motivo": str(v.get("/Reason", "")), "subfiltro": str(v.get("/SubFilter", "")),
                                 "bytes_cobertos": cobertura, "tamanho_arquivo": len(raw)})
                    if cobertura and cobertura < len(raw):
                        alertas.append(f"Assinatura '{v.get('/Name', '?')}' cobre {cobertura} de {len(raw)} bytes: "
                                       "houve alteração/acréscimo APÓS a assinatura. Verificar se é só outra "
                                       "assinatura/carimbo do tempo ou mudança de conteúdo.")
    except Exception:
        pass
    r["assinaturas_digitais"] = sigs
    if b"/JavaScript" in raw or b"/JS " in raw:
        alertas.append("Contém JavaScript embutido.")
    if b"/OCProperties" in raw:
        alertas.append("Contém camadas (OCG): conteúdo pode estar oculto/visível conforme a camada.")
    if b"/EmbeddedFile" in raw:
        alertas.append("Contém arquivos anexados embutidos — extrair e examinar.")
    for tag in (b"pje", b"PJe", b"TJPE", b"eproc", b"projudi"):
        if tag in raw[:4096] or tag in prod.encode():
            alertas.append("Arquivo aparenta ter sido regerado pelo sistema do tribunal: metadados refletem a "
                           "geração pelo PJe/eproc, não o arquivo original. Metadado ausente aqui NÃO é indício "
                           "de nada; pedir o arquivo nativo (art. 425, § 1º, CPC) se a integridade importar.")
            break
    return r, alertas


# ---------------------------------------------------------------- DOCX/XLSX
def meta_ooxml(path):
    r, alertas = {"tipo": "OOXML (docx/xlsx/pptx)"}, []
    with zipfile.ZipFile(path) as z:
        nomes = z.namelist()

        def rd(n):
            return z.read(n).decode("utf-8", "ignore") if n in nomes else ""
        core, app = rd("docProps/core.xml"), rd("docProps/app.xml")
        for tag in ("dc:creator", "cp:lastModifiedBy", "dcterms:created", "dcterms:modified", "cp:revision",
                    "cp:lastPrinted", "dc:title", "cp:keywords"):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", core, re.S)
            if m:
                r[tag] = m.group(1)
        for tag in ("Application", "AppVersion", "Company", "Template", "TotalTime", "Pages", "Words"):
            m = re.search(rf"<{tag}>(.*?)</{tag}>", app, re.S)
            if m:
                r[tag] = m.group(1)
        doc = rd("word/document.xml")
        if doc:
            r["revisoes_rastreadas(ins/del)"] = (len(re.findall(r"<w:ins ", doc)), len(re.findall(r"<w:del ", doc)))
            autores = sorted(set(re.findall(r'w:author="([^"]+)"', doc)))
            if autores:
                r["autores_de_revisoes"] = autores
            r["texto_oculto(w:vanish)"] = doc.count("<w:vanish/>")
            rsids = set(re.findall(r'w:rsidR="([0-9A-F]{8})"', doc))
            r["sessoes_de_edicao(rsid)"] = len(rsids)
            if r["texto_oculto(w:vanish)"]:
                alertas.append("Há texto oculto no documento — exibir e ler.")
            if sum(r["revisoes_rastreadas(ins/del)"]):
                alertas.append("Há alterações rastreadas não aceitas — ler o que foi inserido/excluído e por quem.")
        if "word/comments.xml" in nomes:
            r["comentarios"] = rd("word/comments.xml").count("<w:comment ")
            alertas.append("Há comentários internos no arquivo — podem revelar negociação/intenção.")
        c, m = r.get("dcterms:created"), r.get("dcterms:modified")
        if c and m and c > m:
            alertas.append("Data de criação posterior à de modificação — metadado incoerente (cópia/ajuste de relógio).")
        if r.get("TotalTime") == "0":
            alertas.append("TotalTime=0: arquivo provavelmente gerado por cópia/salvar-como/conversão, não digitado.")
    return r, alertas


# ------------------------------------------------------------------- IMAGENS
def meta_img(path):
    from PIL import Image, ExifTags
    r, alertas = {"tipo": "imagem"}, []
    im = Image.open(path)
    r["formato"], r["dimensoes"], r["modo"] = im.format, im.size, im.mode
    exif = {}
    try:
        raw = im.getexif()
        for k, v in raw.items():
            exif[ExifTags.TAGS.get(k, k)] = str(v)
        try:
            for k, v in raw.get_ifd(0x8769).items():
                exif[ExifTags.TAGS.get(k, k)] = str(v)
        except Exception:
            pass
        try:
            gps = raw.get_ifd(0x8825)
            if gps:
                exif["GPS"] = {ExifTags.GPSTAGS.get(k, k): str(v) for k, v in gps.items()}
        except Exception:
            pass
    except Exception:
        pass
    keep = ("Make", "Model", "Software", "DateTime", "DateTimeOriginal", "DateTimeDigitized",
            "OffsetTimeOriginal", "LensModel", "GPS", "ImageDescription", "Artist")
    r["exif"] = {k: v for k, v in exif.items() if k in keep}
    if not exif:
        alertas.append("Sem EXIF: comum em prints, imagens enviadas por WhatsApp/redes (que removem metadados) "
                       "ou reexportadas. Ausência não é prova de adulteração, mas elimina a autenticação por metadado.")
    sw = exif.get("Software", "")
    if any(s in sw for s in ("Photoshop", "GIMP", "Lightroom", "Snapseed", "Picsart", "Canva", "Pixelmator")):
        alertas.append(f"Imagem processada em editor ('{sw}').")
    if exif.get("DateTime") and exif.get("DateTimeOriginal") and exif["DateTime"] != exif["DateTimeOriginal"]:
        alertas.append("DateTime (última gravação) ≠ DateTimeOriginal (captura): imagem regravada após a captura.")
    return r, alertas


def revisoes(path):
    """Separa cada revisão incremental de um PDF e compara o texto entre elas."""
    from pypdf import PdfReader
    raw = open(path, "rb").read()
    cortes = [m.end() for m in re.finditer(rb"%%EOF[\r\n]*", raw)]
    if len(cortes) < 2:
        print("Apenas uma revisão — nada a comparar.")
        return
    base = os.path.splitext(path)[0]
    textos = []
    for n, fim in enumerate(cortes, 1):
        out = f"{base}_rev{n}.pdf"
        open(out, "wb").write(raw[:fim])
        try:
            t = "\n".join((pg.extract_text() or "") for pg in PdfReader(out, strict=False).pages)
        except Exception as e:  # noqa
            t = f"<ilegível: {e}>"
        textos.append(t)
        print(f"revisão {n}: {out} ({fim} bytes)")
    import difflib
    for n in range(1, len(textos)):
        diff = [ln for ln in difflib.unified_diff(textos[n - 1].splitlines(), textos[n].splitlines(), lineterm="", n=0)
                if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
        print(f"--- diferença de texto rev{n} -> rev{n + 1}: " + ("nenhuma no texto extraível (mudança pode ser "
              "visual, de metadado, anotação ou assinatura — renderizar e comparar)" if not diff else ""))
        for ln in diff[:200]:
            print("   " + ln)


def meta(paths):
    for p in paths:
        print("=" * 78)
        print(f"ARQUIVO: {p}")
        if not os.path.exists(p):
            print("  não encontrado")
            continue
        st = os.stat(p)
        print(f"  tamanho: {st.st_size} bytes | SHA-256: {sha256(p)}")
        print(f"  mtime do sistema de arquivos: {dt.datetime.fromtimestamp(st.st_mtime)} "
              "(reflete a cópia local, não a origem)")
        ext = p.lower().rsplit(".", 1)[-1]
        try:
            if ext == "pdf":
                r, a = meta_pdf(p)
            elif ext in ("docx", "xlsx", "pptx", "docm", "xlsm"):
                r, a = meta_ooxml(p)
            elif ext in ("jpg", "jpeg", "png", "tif", "tiff", "webp", "heic", "gif", "bmp"):
                r, a = meta_img(p)
            else:
                r, a = {"tipo": ext, "obs": "sem extrator específico; use hash e leitura direta"}, []
        except Exception as e:  # noqa
            r, a = {"erro": repr(e)}, []
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
        for x in a:
            print(f"  {ALERTA} {x}")
        if not a:
            print("  (nenhum alerta automático — isso não certifica integridade)")


# ------------------------------------------------------------ identificadores
def so_dig(s):
    return re.sub(r"\D", "", s)


def cpf(s):
    d = so_dig(s)
    if len(d) != 11 or d == d[0] * 11:
        return f"CPF {s}: INVÁLIDO (formato/sequência repetida)"
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(d[n]):
            return f"CPF {s}: INVÁLIDO (dígito verificador {n - 8} esperado {dv})"
    regiao = {"0": "RS", "1": "DF/GO/MS/MT/TO", "2": "AC/AM/AP/PA/RO/RR", "3": "CE/MA/PI", "4": "AL/PB/PE/RN",
              "5": "BA/SE", "6": "MG", "7": "ES/RJ", "8": "SP", "9": "PR/SC"}[d[8]]
    return f"CPF {s}: dígitos válidos | região fiscal de emissão (9º dígito): {regiao}"


def cnpj(s):
    c = re.sub(r"[^0-9A-Za-z]", "", s).upper()
    if len(c) != 14 or not c[-2:].isdigit() or c == c[0] * 14:
        return f"CNPJ {s}: INVÁLIDO (formato)"
    val = [ord(ch) - 48 for ch in c]
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(v * p for v, p in zip(val[:n], pesos))
        dv = 0 if soma % 11 < 2 else 11 - soma % 11
        if dv != val[n]:
            return f"CNPJ {s}: INVÁLIDO (dígito verificador {n - 11} esperado {dv})"
    tipo = "matriz" if c[8:12] == "0001" else f"filial {c[8:12]}"
    alfa = " | alfanumérico (formato vigente a partir de jul/2026)" if not c[:12].isdigit() else ""
    return f"CNPJ {s}: dígitos válidos | {tipo}{alfa}"


UF_IBGE = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
           "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
           "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


def nfe(s):
    d = so_dig(s)
    if len(d) != 44:
        return f"Chave {s}: INVÁLIDA (precisa de 44 dígitos, tem {len(d)})"
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(x) * pesos[i % 8] for i, x in enumerate(reversed(d[:43])))
    dv = 0 if soma % 11 < 2 else 11 - soma % 11
    ok = "válido" if dv == int(d[43]) else f"INVÁLIDO (esperado {dv})"
    mod = {"55": "NF-e", "65": "NFC-e", "57": "CT-e", "58": "MDF-e", "67": "CT-e OS"}.get(d[20:22], d[20:22])
    return (f"Chave {d}\n  DV: {ok}\n  UF emitente: {UF_IBGE.get(d[:2], d[:2])} | emissão: {d[4:6]}/20{d[2:4]}\n"
            f"  CNPJ/CPF emitente: {d[6:20]} -> {cnpj(d[6:20]) if not d[6:9] == '000' else 'possível CPF'}\n"
            f"  modelo: {mod} | série {int(d[22:25])} | número {int(d[25:34])} | tpEmis {d[34]}\n"
            "  Conferir: mês/ano da chave x data impressa; CNPJ da chave x emitente; consulta pública na SEFAZ.")


def mod10(num):
    soma, peso = 0, 2
    for ch in reversed(num):
        p = int(ch) * peso
        soma += p // 10 + p % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def mod11_boleto(num):
    soma, peso = 0, 2
    for ch in reversed(num):
        soma += int(ch) * peso
        peso = 2 if peso == 9 else peso + 1
    r = 11 - soma % 11
    return 1 if r in (0, 10, 11) else r


def fator_para_data(f):
    f = int(f)
    if f == 0:
        return "sem vencimento"
    base_antiga = dt.date(1997, 10, 7) + dt.timedelta(days=f)
    base_nova = dt.date(2025, 2, 22) + dt.timedelta(days=f - 1000)
    if base_antiga < dt.date(2025, 2, 22):
        return f"{base_antiga:%d/%m/%Y} (ciclo anterior) ou {base_nova:%d/%m/%Y} (ciclo reiniciado em 22/02/2025)"
    return f"{base_antiga:%d/%m/%Y}"


def boleto(s):
    d = so_dig(s)
    if len(d) == 47:
        campos = [(d[0:9], d[9]), (d[10:20], d[20]), (d[21:31], d[31])]
        msgs = [f"campo {i + 1}: {'ok' if mod10(c) == int(v) else 'DV INVÁLIDO'}" for i, (c, v) in enumerate(campos)]
        barras = d[0:4] + d[32] + d[33:47] + d[4:9] + d[10:20] + d[21:31]
    elif len(d) == 44:
        barras, msgs = d, []
        if d[0] == "8":
            return "Código de arrecadação (concessionária/tributo, inicia com 8): layout diferente — conferir no órgão."
    elif len(d) == 48 and d[0] == "8":
        return "Linha de arrecadação (concessionária/tributo): layout diferente — conferir valor e órgão no próprio convênio."
    else:
        return f"Boleto {s}: tamanho {len(d)} não reconhecido (esperado 47 linha digitável ou 44 código de barras)"
    dv_geral = mod11_boleto(barras[:4] + barras[5:])
    msgs.append(f"DV geral: {'ok' if dv_geral == int(barras[4]) else 'INVÁLIDO'}")
    valor = int(barras[9:19]) / 100
    return (f"Banco emissor: {barras[:3]} | moeda {barras[3]}\n  vencimento (fator {barras[5:9]}): "
            f"{fator_para_data(barras[5:9])}\n  valor codificado: R$ {valor:,.2f}".replace(",", "X").replace(".", ",")
            .replace("X", ".") + "\n  " + " | ".join(msgs) +
            "\n  Conferir: valor/vencimento codificados x impressos; banco x beneficiário declarado.")


def pix(s):
    s = s.strip()
    m = re.fullmatch(r"([ED])(\d{8})(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})([0-9A-Za-z]{11})", s)
    if not m:
        return f"ID {s}: fora do padrão E2E do Pix (32 caracteres: E + ISPB 8 + AAAAMMDDHHMM + 11)"
    _, ispb, a, mo, d, h, mi, _ = m.groups()
    try:
        utc = dt.datetime(int(a), int(mo), int(d), int(h), int(mi), tzinfo=dt.timezone.utc)
        brt = utc.astimezone(dt.timezone(dt.timedelta(hours=-3)))
        return (f"ID E2E válido no formato | ISPB do participante pagador: {ispb}\n  data/hora codificada: "
                f"{utc:%d/%m/%Y %H:%M} UTC = {brt:%d/%m/%Y %H:%M} (Brasília)\n"
                "  Conferir com a data/hora impressa no comprovante e com o banco declarado (ISPB).")
    except ValueError:
        return f"ID {s}: data codificada impossível ({d}/{mo}/{a} {h}:{mi}) — {ALERTA} forte indício de ID forjado"


def pascoa(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mes = (h + l_ - 7 * m + 114) // 31
    dia = (h + l_ - 7 * m + 114) % 31 + 1
    return dt.date(y, mes, dia)


def feriados(y):
    fx = {(1, 1): "Confraternização Universal", (4, 21): "Tiradentes", (5, 1): "Dia do Trabalho",
          (9, 7): "Independência", (10, 12): "N. Sra. Aparecida", (11, 2): "Finados",
          (11, 15): "Proclamação da República", (12, 25): "Natal"}
    if y >= 2024:
        fx[(11, 20)] = "Consciência Negra (nacional desde 2024)"
    out = {dt.date(y, m, d): n for (m, d), n in fx.items()}
    p = pascoa(y)
    out[p - dt.timedelta(days=2)] = "Sexta-feira Santa"
    out[p - dt.timedelta(days=47)] = "Carnaval (ponto facultativo nacional; conferir lei local)"
    out[p - dt.timedelta(days=46)] = "Quarta de Cinzas (ponto facultativo até 14h)"
    out[p + dt.timedelta(days=60)] = "Corpus Christi (ponto facultativo; feriado municipal em vários)"
    return out


def datas(args):
    nomes = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    ds = []
    for a in args:
        try:
            d = dt.datetime.strptime(a, "%d/%m/%Y").date()
        except ValueError:
            print(f"{a}: {ALERTA} DATA IMPOSSÍVEL/inválida")
            continue
        ds.append(d)
        fer = feriados(d.year).get(d)
        extra = f" | {ALERTA} {fer}" if fer else ""
        fds = f" | {ALERTA} fim de semana" if d.weekday() >= 5 else ""
        print(f"{d:%d/%m/%Y}: {nomes[d.weekday()]}{fds}{extra}")
    for x, y in zip(ds, ds[1:]):
        print(f"  {x:%d/%m/%Y} -> {y:%d/%m/%Y}: {(y - x).days} dias corridos")
    print("  (feriados estaduais/municipais e suspensões de expediente forense não estão cobertos: conferir)")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "meta":
        meta(args)
    elif cmd == "revisoes":
        for a in args:
            revisoes(a)
    elif cmd == "data":
        datas(args)
    else:
        fn = {"cpf": cpf, "cnpj": cnpj, "nfe": nfe, "boleto": boleto, "pix": pix}.get(cmd)
        if not fn:
            print(__doc__)
            sys.exit(1)
        for a in args:
            print(fn(a))


if __name__ == "__main__":
    main()
