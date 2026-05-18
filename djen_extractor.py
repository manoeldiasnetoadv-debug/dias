"""
djen_extractor.py
Consulta a API pública do DJEN (Diário de Justiça Eletrônico Nacional - CNJ)
e retorna publicações que correspondem aos termos de pesquisa configurados.
"""

import logging
import time
from datetime import date, datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração central
# ---------------------------------------------------------------------------

SEARCH_TERMS: list[str] = [
    "OAB/PE 39.914",
    "Dias & Lucena Advogados",
    "Manoel Candido Dias Neto",
]

# Endpoint público do DJEN / CNJ
# Documentação: https://djen.cnj.jus.br
_BASE_URL = "https://djen.cnj.jus.br/pesquisaPublicacao"

_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (compatible; DJEN-Automator/1.0; "
        "+https://github.com/seu-repositorio)"
    ),
}

_REQUEST_TIMEOUT = 30          # segundos por requisição
_RETRY_ATTEMPTS = 3            # tentativas em caso de falha transitória
_RETRY_BACKOFF_BASE = 5        # segundos de espera entre tentativas (×2 a cada retry)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_payload(term: str, reference_date: date) -> dict[str, Any]:
    """Monta o corpo da requisição para um único termo e data."""
    return {
        "dataDisponibilizacao": reference_date.strftime("%d/%m/%Y"),
        "tipoComunicacao": "",
        "siglaTribunal": "",
        "texto": term,
        "pagina": 1,
        "qtdRegistrosPorPagina": 200,   # máximo prático por página
    }


def _request_with_retry(
    session: requests.Session,
    payload: dict[str, Any],
    term: str,
) -> list[dict[str, Any]]:
    """
    Executa a requisição ao DJEN com retries exponenciais.
    Retorna lista de publicações brutas (dicts) ou lista vazia em caso de falha.
    """
    wait = _RETRY_BACKOFF_BASE
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            logger.info(
                "Consultando DJEN | termo='%s' | tentativa %d/%d",
                term,
                attempt,
                _RETRY_ATTEMPTS,
            )
            response = session.post(
                _BASE_URL,
                json=payload,
                headers=_HEADERS,
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()

            # O CNJ pode devolver {"comunicacoes": [...]} ou {"content": [...]}
            publications = (
                data.get("comunicacoes")
                or data.get("content")
                or data.get("publicacoes")
                or []
            )

            logger.info(
                "Termo '%s' → %d publicação(ões) encontrada(s).",
                term,
                len(publications),
            )
            return publications

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Falha de conexão ao DJEN (tentativa %d): %s", attempt, exc)
        except requests.exceptions.Timeout:
            logger.warning("Timeout na requisição ao DJEN (tentativa %d).", attempt)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "N/A"
            logger.warning(
                "Erro HTTP %s ao consultar DJEN (tentativa %d): %s",
                status,
                attempt,
                exc,
            )
            # Erros 4xx não vão melhorar com retry; interrompe o loop
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                logger.error(
                    "Erro de cliente (4xx) — não será feito novo retry para '%s'.",
                    term,
                )
                break
        except ValueError as exc:
            logger.error(
                "Resposta inesperada (não-JSON) do DJEN para o termo '%s': %s",
                term,
                exc,
            )
            break

        if attempt < _RETRY_ATTEMPTS:
            logger.info("Aguardando %ds antes do próximo retry…", wait)
            time.sleep(wait)
            wait *= 2

    logger.error(
        "Todos os %d tentativas falharam para o termo '%s'. "
        "O CNJ pode estar indisponível.",
        _RETRY_ATTEMPTS,
        term,
    )
    return []


def _normalize_publication(raw: dict[str, Any], source_term: str) -> dict[str, Any]:
    """
    Normaliza um registo bruto da API para um formato interno consistente.
    Campos possíveis variam conforme a versão da API do CNJ.
    """
    return {
        "numero_processo": (
            raw.get("numeroProcesso")
            or raw.get("numero_processo")
            or raw.get("processo")
            or "Não identificado"
        ),
        "data_disponibilizacao": (
            raw.get("dataDisponibilizacao")
            or raw.get("data_disponibilizacao")
            or raw.get("dataPublicacao")
            or ""
        ),
        "tipo_comunicacao": (
            raw.get("tipoComunicacao")
            or raw.get("tipo_comunicacao")
            or raw.get("tipo")
            or ""
        ),
        "tribunal": (
            raw.get("siglaTribunal")
            or raw.get("tribunal")
            or raw.get("sigla_tribunal")
            or ""
        ),
        "texto": (
            raw.get("texto")
            or raw.get("conteudo")
            or raw.get("teor")
            or ""
        ),
        "destinatario": (
            raw.get("nomeDestinatario")
            or raw.get("destinatario")
            or raw.get("nome_destinatario")
            or ""
        ),
        "oab_destinatario": (
            raw.get("numeroOabDestintario")
            or raw.get("oab_destinatario")
            or ""
        ),
        "meio_comunicacao": (
            raw.get("meioComunicacao")
            or raw.get("meio_comunicacao")
            or ""
        ),
        "_source_term": source_term,     # qual termo gerou este resultado
        "_raw": raw,                      # preserva o original para debug
    }


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------

def extract(reference_date: date | None = None) -> dict[str, Any]:
    """
    Ponto de entrada principal.

    Parameters
    ----------
    reference_date:
        Data de referência para a consulta. Utiliza a data de hoje se omitido.

    Returns
    -------
    dict com as chaves:
        - ``date``          : data consultada (objeto date)
        - ``extracted_at``  : datetime exato da extração
        - ``publications``  : lista de publicações normalizadas (sem duplicatas)
        - ``terms_searched``: termos utilizados na pesquisa
        - ``errors``        : lista de erros não fatais registrados
    """
    if reference_date is None:
        reference_date = date.today()

    extracted_at = datetime.now()
    logger.info(
        "=== Iniciando extração DJEN | data=%s | %d termo(s) ===",
        reference_date.isoformat(),
        len(SEARCH_TERMS),
    )

    all_publications: list[dict[str, Any]] = []
    seen_ids: set[str] = set()          # deduplicação por número de processo + texto
    errors: list[str] = []

    with requests.Session() as session:
        for term in SEARCH_TERMS:
            payload = _build_payload(term, reference_date)
            raw_list = _request_with_retry(session, payload, term)

            for raw in raw_list:
                pub = _normalize_publication(raw, term)

                # Chave de deduplicação: processo + primeiros 120 chars do texto
                dedup_key = (
                    pub["numero_processo"]
                    + "|"
                    + pub["texto"][:120]
                )
                if dedup_key in seen_ids:
                    continue
                seen_ids.add(dedup_key)
                all_publications.append(pub)

    unique_processes = len(
        {p["numero_processo"] for p in all_publications if p["numero_processo"]}
    )

    logger.info(
        "=== Extração concluída | total=%d publicações | %d processos únicos ===",
        len(all_publications),
        unique_processes,
    )

    return {
        "date": reference_date,
        "extracted_at": extracted_at,
        "publications": all_publications,
        "terms_searched": SEARCH_TERMS,
        "errors": errors,
        "unique_processes": unique_processes,
    }
