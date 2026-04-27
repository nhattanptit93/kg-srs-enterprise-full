import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from core.logger import get_logger
from controller.workflow import build_app

logger = get_logger("main")


def load_input(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Input file not found: {p.resolve()}. "
            f"Create it or pass another path as CLI arg."
        )
    return p.read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "input.md"
    raw_rd = load_input(path)
    logger.info(f"Loaded RD from {path} ({len(raw_rd)} chars)")

    app = build_app()
    final = app.invoke({"input": raw_rd})

    logger.info("=" * 60)
    logger.info("FINAL SRS")
    logger.info("=" * 60)
    logger.info("\n" + final.get("srs", "(no SRS produced)"))
    logger.info(f"Score: {final.get('score')} | Iterations: {final.get('iterations')}")

    srs_path = Path("workspace/current_srs.md").resolve()
    logger.info("=" * 60)
    logger.info(f"📄 SRS FILE: file:///{srs_path}")
    logger.info("=" * 60)
