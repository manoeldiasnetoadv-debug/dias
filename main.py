"""
main.py
Orquestrador do DJEN Automator.

Agenda a execução do fluxo completo duas vezes por dia:
  • 09:00 — extração matinal
  • 15:00 — extração vespertina

Cada execução grava um ficheiro HTML independente em 'relatorios_gerados/'
com nome baseado em data e hora (ex: relatorio_djen_20260517_0900.html).
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

import djen_extractor
import report_generator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    log_format = (
        "%(asctime)s  %(levelname)-8s  %(name)-22s  %(message)s"
    )
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Silencia logs de baixo nível de bibliotecas externas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Configuração de caminhos
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).parent / "relatorios_gerados"


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Directório de saída: %s", OUTPUT_DIR.resolve())


def _report_filename(ts: datetime) -> Path:
    """Gera o caminho completo do ficheiro HTML com timestamp."""
    filename = f"relatorio_djen_{ts.strftime('%Y%m%d_%H%M')}.html"
    return OUTPUT_DIR / filename


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    """
    Executa o pipeline completo:
      1. Extrai publicações do DJEN para a data de hoje.
      2. Gera o relatório HTML.
      3. Grava o relatório em disco.
    """
    start = datetime.now()
    logger.info("━━━ Pipeline iniciado (%s) ━━━", start.strftime("%Y-%m-%d %H:%M:%S"))

    # ── Passo 1: Extração ────────────────────────────────────────────────
    try:
        data = djen_extractor.extract()
    except Exception as exc:                                # pylint: disable=broad-except
        logger.critical(
            "Falha inesperada durante a extração: %s — pipeline interrompido.", exc,
            exc_info=True,
        )
        return

    # ── Passo 2: Geração do relatório ────────────────────────────────────
    try:
        html_content = report_generator.generate(data)
    except Exception as exc:                                # pylint: disable=broad-except
        logger.critical(
            "Falha inesperada durante a geração do relatório: %s — pipeline interrompido.",
            exc,
            exc_info=True,
        )
        return

    # ── Passo 3: Gravação em disco ───────────────────────────────────────
    report_path = _report_filename(data["extracted_at"])
    try:
        report_path.write_text(html_content, encoding="utf-8")
        logger.info("Relatório gravado: %s", report_path.resolve())
    except OSError as exc:
        logger.error(
            "Não foi possível gravar o ficheiro '%s': %s", report_path, exc
        )
        return

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(
        "━━━ Pipeline concluído em %.1fs | %d publicação(ões) | ficheiro: %s ━━━",
        elapsed,
        len(data.get("publications", [])),
        report_path.name,
    )


# ---------------------------------------------------------------------------
# Agendamento
# ---------------------------------------------------------------------------

SCHEDULE_TIMES = ["09:00", "15:00"]


def _setup_schedule() -> None:
    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(run_pipeline)
        logger.info("Tarefa agendada para as %s.", t)


def _log_next_run() -> None:
    next_run = schedule.next_run()
    if next_run:
        logger.info(
            "Próxima execução agendada: %s",
            next_run.strftime("%Y-%m-%d %H:%M:%S"),
        )


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_logging()
    _ensure_output_dir()

    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║         DJEN AUTOMATOR — iniciando           ║")
    logger.info("╚══════════════════════════════════════════════╝")
    logger.info("Termos configurados: %s", djen_extractor.SEARCH_TERMS)

    _setup_schedule()

    # Executa imediatamente na primeira vez para validar o fluxo
    logger.info("Executando pipeline imediatamente na inicialização…")
    run_pipeline()

    _log_next_run()

    logger.info("Aguardando agendamentos (Ctrl+C para encerrar)…")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)          # verifica a agenda a cada 30 segundos
    except KeyboardInterrupt:
        logger.info("Encerrado pelo utilizador (KeyboardInterrupt).")
        sys.exit(0)


if __name__ == "__main__":
    main()
