"""
report_generator.py
Gera um relatório HTML com CSS embutido a partir dos dados extraídos do DJEN.
Aplica princípios de Visual Law e UI/UX:
  - Dashboard de métricas no topo
  - Cards de publicação com triagem automática de urgência
  - Destaque tipográfico para termos críticos
"""

import html
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Termos que activam a triagem de urgência
# ---------------------------------------------------------------------------

URGENCY_TERMS: list[str] = [
    "prazo",
    "urgente",
    "urgência",
    "audiência",
    "intimação",
    "intimar",
    "citar",
    "citação",
    "liminar",
    "medida cautelar",
    "suspensão",
    "embargo",
]

# Termos a destacar em negrito no corpo do texto
HIGHLIGHT_TERMS: list[str] = [
    "OAB/PE 39.914",
    "Dias & Lucena Advogados",
    "Manoel Candido Dias Neto",
]

# ---------------------------------------------------------------------------
# CSS embutido (Visual Law — tipografia limpa, cores sóbrias, acessível)
# ---------------------------------------------------------------------------

_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --clr-bg:        #f4f6f9;
    --clr-surface:   #ffffff;
    --clr-primary:   #1a3a5c;
    --clr-accent:    #2b6cb0;
    --clr-text:      #2d3748;
    --clr-muted:     #718096;
    --clr-border:    #e2e8f0;
    --clr-urgent-bg: #fff5f5;
    --clr-urgent-bd: #c53030;
    --clr-badge-ok:  #276749;
    --clr-badge-urg: #c53030;
    --radius:        8px;
    --shadow:        0 1px 3px rgba(0,0,0,.10), 0 1px 2px rgba(0,0,0,.06);
    --shadow-lg:     0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.05);
  }

  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--clr-bg);
    color: var(--clr-text);
    line-height: 1.6;
    padding: 2rem 1rem;
  }

  /* ── Cabeçalho ────────────────────────────────────────────────────────── */
  .header {
    background: var(--clr-primary);
    color: #fff;
    border-radius: var(--radius);
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 1rem;
    box-shadow: var(--shadow-lg);
  }
  .header__logo {
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 0.4rem;
  }
  .header__title { font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
  .header__subtitle { font-size: 0.95rem; opacity: 0.8; margin-top: 0.3rem; }
  .header__meta { text-align: right; font-size: 0.85rem; opacity: 0.85; }
  .header__meta strong { display: block; font-size: 1.05rem; }

  /* ── Dashboard ────────────────────────────────────────────────────────── */
  .dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }
  .metric-card {
    background: var(--clr-surface);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--shadow);
    border-top: 4px solid var(--clr-accent);
  }
  .metric-card__label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--clr-muted);
    margin-bottom: 0.4rem;
  }
  .metric-card__value {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--clr-primary);
    line-height: 1;
  }
  .metric-card__sub {
    font-size: 0.8rem;
    color: var(--clr-muted);
    margin-top: 0.3rem;
  }

  /* ── Secção ───────────────────────────────────────────────────────────── */
  .section-title {
    font-size: 1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--clr-muted);
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--clr-border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  /* ── Cards de publicação ──────────────────────────────────────────────── */
  .card {
    background: var(--clr-surface);
    border-radius: var(--radius);
    border: 1.5px solid var(--clr-border);
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: var(--shadow);
    transition: box-shadow .15s;
  }
  .card:hover { box-shadow: var(--shadow-lg); }

  .card--urgent {
    background: var(--clr-urgent-bg);
    border-color: var(--clr-urgent-bd);
    border-left-width: 5px;
  }

  .card__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .card__process {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--clr-primary);
    font-variant-numeric: tabular-nums;
  }

  .badge {
    display: inline-block;
    padding: 0.2em 0.65em;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge--normal  { background: #ebf8ff; color: var(--clr-badge-ok); }
  .badge--urgent  { background: #fff5f5; color: var(--clr-badge-urg); }

  .card__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-size: 0.82rem;
    color: var(--clr-muted);
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--clr-border);
  }
  .card__meta span::before { content: attr(data-icon) " "; }

  .card__body {
    font-size: 0.92rem;
    line-height: 1.75;
    color: var(--clr-text);
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* Termos em destaque */
  .hl-term {
    font-weight: 700;
    background: #ebf8ff;
    border-radius: 3px;
    padding: 0 2px;
  }
  .hl-urgent-term {
    font-weight: 700;
    color: var(--clr-badge-urg);
    background: #fff5f5;
    border-radius: 3px;
    padding: 0 2px;
  }

  /* ── Estado vazio ─────────────────────────────────────────────────────── */
  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--clr-muted);
    background: var(--clr-surface);
    border-radius: var(--radius);
    border: 1.5px dashed var(--clr-border);
  }
  .empty-state__icon { font-size: 3rem; margin-bottom: 1rem; }
  .empty-state__text { font-size: 1rem; }

  /* ── Rodapé ───────────────────────────────────────────────────────────── */
  .footer {
    margin-top: 3rem;
    text-align: center;
    font-size: 0.78rem;
    color: var(--clr-muted);
    padding-top: 1.5rem;
    border-top: 1px solid var(--clr-border);
  }

  @media (max-width: 600px) {
    .header { flex-direction: column; }
    .header__meta { text-align: left; }
    .card__header { flex-direction: column; }
  }
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_urgent(text: str) -> bool:
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in URGENCY_TERMS)


def _apply_highlights(text: str) -> str:
    """
    Aplica destaque HTML aos termos configurados no corpo do texto.
    Urgency terms → classe 'hl-urgent-term'
    Highlight terms → classe 'hl-term'
    Usa expressões regulares para ser case-insensitive e preservar acentos.
    """
    # Urgency terms primeiro (prioridade visual maior)
    for term in URGENCY_TERMS:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(
            lambda m: f'<span class="hl-urgent-term">{html.escape(m.group(0))}</span>',
            text,
        )
    for term in HIGHLIGHT_TERMS:
        escaped_term = re.escape(term)
        pattern = re.compile(escaped_term, re.IGNORECASE)
        text = pattern.sub(
            lambda m: f'<span class="hl-term">{html.escape(m.group(0))}</span>',
            text,
        )
    return text


def _render_card(pub: dict[str, Any], is_urgent: bool) -> str:
    card_class = "card card--urgent" if is_urgent else "card"
    badge_class = "badge badge--urgent" if is_urgent else "badge badge--normal"
    badge_text = "&#9888; URGENTE" if is_urgent else "Normal"

    process = html.escape(pub.get("numero_processo") or "Processo não identificado")
    tribunal = html.escape(pub.get("tribunal") or "—")
    tipo = html.escape(pub.get("tipo_comunicacao") or "—")
    data_disp = html.escape(pub.get("data_disponibilizacao") or "—")
    destinatario = html.escape(pub.get("destinatario") or "")
    meio = html.escape(pub.get("meio_comunicacao") or "")
    source_term = html.escape(pub.get("_source_term") or "")

    # Corpo do texto: escapa HTML e depois aplica destaques
    raw_body = pub.get("texto") or "Texto não disponível."
    body_escaped = html.escape(raw_body)
    body_highlighted = _apply_highlights(body_escaped)

    meta_parts = [
        f'<span data-icon="📅">{data_disp}</span>',
        f'<span data-icon="⚖️">{tribunal}</span>',
        f'<span data-icon="📋">{tipo}</span>',
    ]
    if destinatario:
        meta_parts.append(f'<span data-icon="👤">{destinatario}</span>')
    if meio:
        meta_parts.append(f'<span data-icon="📡">{meio}</span>')
    if source_term:
        meta_parts.append(f'<span data-icon="🔍">Termo: {source_term}</span>')

    meta_html = "\n        ".join(meta_parts)

    return f"""
    <div class="{card_class}">
      <div class="card__header">
        <div class="card__process">{process}</div>
        <span class="{badge_class}">{badge_text}</span>
      </div>
      <div class="card__meta">
        {meta_html}
      </div>
      <div class="card__body">{body_highlighted}</div>
    </div>"""


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

def generate(data: dict[str, Any]) -> str:
    """
    Gera e retorna o conteúdo HTML do relatório.

    Parameters
    ----------
    data : dict retornado por ``djen_extractor.extract()``

    Returns
    -------
    str : conteúdo HTML completo pronto para gravar em ficheiro.
    """
    extracted_at: datetime = data.get("extracted_at", datetime.now())
    ref_date = data.get("date")
    publications: list[dict[str, Any]] = data.get("publications", [])
    terms: list[str] = data.get("terms_searched", [])
    unique_processes: int = data.get("unique_processes", 0)

    logger.info(
        "Gerando relatório HTML | %d publicação(ões) | %d processo(s) único(s)",
        len(publications),
        unique_processes,
    )

    # Triagem: separar urgentes vs normais
    urgent_pubs = []
    normal_pubs = []
    for pub in publications:
        if _is_urgent(pub.get("texto") or ""):
            urgent_pubs.append(pub)
        else:
            normal_pubs.append(pub)

    # Renderiza cards (urgentes primeiro)
    urgent_cards_html = "".join(_render_card(p, True) for p in urgent_pubs)
    normal_cards_html = "".join(_render_card(p, False) for p in normal_pubs)

    # Secções
    if not publications:
        publications_section = """
        <div class="empty-state">
          <div class="empty-state__icon">📭</div>
          <div class="empty-state__text">
            Nenhuma publicação encontrada para os termos pesquisados nesta data.
          </div>
        </div>"""
    else:
        urgent_section = ""
        if urgent_pubs:
            urgent_section = f"""
        <div class="section-title">&#9888; Publicações Urgentes ({len(urgent_pubs)})</div>
        {urgent_cards_html}"""

        normal_section = ""
        if normal_pubs:
            normal_section = f"""
        <div class="section-title">&#10003; Publicações Regulares ({len(normal_pubs)})</div>
        {normal_cards_html}"""

        publications_section = urgent_section + normal_section

    # Termos pesquisados (lista formatada)
    terms_list = "".join(f"<li>{html.escape(t)}</li>" for t in terms)

    # Data e hora formatadas em pt-BR
    date_fmt = ref_date.strftime("%d/%m/%Y") if ref_date else "—"
    extracted_fmt = extracted_at.strftime("%d/%m/%Y às %H:%M:%S")
    file_ts = extracted_at.strftime("%Y%m%d_%H%M")

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório DJEN — {date_fmt}</title>
  <style>
{_CSS}
  </style>
</head>
<body>

  <!-- ── Cabeçalho ──────────────────────────────────────────────────── -->
  <header class="header">
    <div>
      <div class="header__logo">CNJ — Diário de Justiça Eletrônico Nacional</div>
      <div class="header__title">Relatório de Publicações</div>
      <div class="header__subtitle">Referência: {date_fmt}</div>
    </div>
    <div class="header__meta">
      <span>Extraído em</span>
      <strong>{extracted_fmt}</strong>
      <span style="display:block;margin-top:.5rem;font-size:.78rem;">
        Gerado automaticamente por DJEN Automator
      </span>
    </div>
  </header>

  <!-- ── Dashboard ──────────────────────────────────────────────────── -->
  <section class="dashboard" aria-label="Métricas rápidas">
    <div class="metric-card">
      <div class="metric-card__label">Total de Publicações</div>
      <div class="metric-card__value">{len(publications)}</div>
      <div class="metric-card__sub">encontradas hoje</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__label">Processos Únicos</div>
      <div class="metric-card__value">{unique_processes}</div>
      <div class="metric-card__sub">números distintos</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__label">Publicações Urgentes</div>
      <div class="metric-card__value">{len(urgent_pubs)}</div>
      <div class="metric-card__sub">requerem atenção</div>
    </div>
    <div class="metric-card">
      <div class="metric-card__label">Publicações Regulares</div>
      <div class="metric-card__value">{len(normal_pubs)}</div>
      <div class="metric-card__sub">sem alerta de urgência</div>
    </div>
  </section>

  <!-- ── Termos pesquisados ──────────────────────────────────────────── -->
  <details style="margin-bottom:1.5rem;background:var(--clr-surface);
                  border-radius:var(--radius);padding:1rem 1.25rem;
                  box-shadow:var(--shadow);border:1.5px solid var(--clr-border);">
    <summary style="cursor:pointer;font-weight:600;color:var(--clr-primary);">
      🔍 Termos pesquisados ({len(terms)})
    </summary>
    <ul style="margin-top:.75rem;padding-left:1.5rem;color:var(--clr-muted);
               font-size:.9rem;line-height:2;">
      {terms_list}
    </ul>
  </details>

  <!-- ── Publicações ────────────────────────────────────────────────── -->
  <main>
    {publications_section}
  </main>

  <!-- ── Rodapé ─────────────────────────────────────────────────────── -->
  <footer class="footer">
    Relatório gerado automaticamente &mdash; DJEN Automator &mdash;
    {extracted_fmt} &mdash; Apenas para uso profissional interno.
  </footer>

</body>
</html>"""

    logger.info("Relatório HTML gerado com sucesso (timestamp: %s).", file_ts)
    return html_content
