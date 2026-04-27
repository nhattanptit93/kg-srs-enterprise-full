"""Split bilingual SKILLS.md files into EN-only (SKILLS.md) and VI-only (SKILLS-vn.md).

Run from project root:
    python tools/split_skills.py [--dry-run] [--check]

The split logic mirrors ``core.llm._strip_vi`` for the EN side. The VI side
is built by collecting every Vietnamese span the strip logic would have
removed, then re-emitting them in the same line order so the result is
readable as a standalone document.

Idempotent: running twice on already-split files is safe — files that
contain no Vietnamese diacritics are left untouched, and the EN file
won't grow a second VI section.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VI_DIACRITICS = re.compile(
    "[ăâđêôơưĂÂĐÊÔƠƯ"
    "áàảãạắằẳẵặầấẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẦẤẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ]"
)


def has_vi(s: str) -> bool:
    return bool(VI_DIACRITICS.search(s))


def strip_to_en(content: str) -> str:
    """EN-only version of a bilingual document. Mirrors core.llm._strip_vi."""
    # 1. Italic *( ... )* VI annotations
    content = re.sub(
        r"\*\(.+?\)\*",
        lambda m: "" if has_vi(m.group(0)) else m.group(0),
        content,
    )

    # 2. Heading slash suffix: "## EN / Tiếng Việt" -> "## EN"
    def _heading_slash_sub(m: "re.Match[str]") -> str:
        head, tail = m.group(1), m.group(2)
        return head.rstrip() if has_vi(tail) else m.group(0)

    content = re.sub(
        r"^(#{1,6}[^\n/]*?)\s+/\s+([^\n]+)$",
        _heading_slash_sub,
        content,
        flags=re.MULTILINE,
    )

    # 3. Pure-VI heading lines
    def _heading_line_sub(m: "re.Match[str]") -> str:
        line = m.group(0)
        text = re.sub(r"^#{1,6}\s*", "", line)
        return "" if has_vi(text) else line

    content = re.sub(r"^#{1,6}[^\n]+$", _heading_line_sub, content, flags=re.MULTILINE)

    # 4. Bracketed "/ [VI]" template markers
    content = re.sub(
        r"\s*/\s*\[[^\]\n]+\]",
        lambda m: "" if has_vi(m.group(0)) else m.group(0),
        content,
    )

    # 5. Bold inline "EN / VI:**" -> keep ":**"
    content = re.sub(
        r"\s+/\s+([^/\n*]+?)(:?\*+)",
        lambda m: m.group(2) if has_vi(m.group(1)) else m.group(0),
        content,
    )

    # 6. Trailing "EN / Vietnamese..." (template / glossary)
    content = re.sub(
        r"\s+/\s+[^/\n]+$",
        lambda m: "" if has_vi(m.group(0)) else m.group(0),
        content,
        flags=re.MULTILINE,
    )

    # 6b. Multi-slash variant: "EN / EN / EN: [...] / VI / VI"
    #     Split by " / " and drop everything from the first VI segment onward.
    def _multi_slash_split(line: str) -> str:
        parts = line.split(" / ")
        if len(parts) < 2:
            return line
        en_count = 0
        for p in parts:
            if has_vi(p):
                break
            en_count += 1
        if en_count == 0 or en_count == len(parts):
            return line
        return " / ".join(parts[:en_count])

    content = "\n".join(_multi_slash_split(l) for l in content.split("\n"))

    # 7. Standalone (Vietnamese...) parenthetical lines
    content = re.sub(
        r"^[ \t]*\([^)\n]+\)[ \t]*$",
        lambda m: "" if has_vi(m.group(0)) else m.group(0),
        content,
        flags=re.MULTILINE,
    )

    # 7b. Multi-line VI parenthetical blocks
    content = re.sub(
        r"^[ \t]*\([^()\n][^()]*?\)[ \t]*$",
        lambda m: "" if has_vi(m.group(0)) else m.group(0),
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    # 7c. Inline " (Tiếng Việt)" annotations after EN words
    content = re.sub(
        r"[ \t]+\([^()\n]{2,}\)",
        lambda m: ""
        if has_vi(m.group(0)) and not re.search(r"[A-Za-z]{4,}", m.group(0))
        else m.group(0),
        content,
    )

    # 7d. VI-density pass: drop lines whose post-quote/post-id text is
    #     dominated by Vietnamese diacritic characters. We compare diacritic
    #     count to the total letter count rather than counting "EN words",
    #     because many VI words contain no diacritics (thanh, sang, trong)
    #     and would inflate a naïve EN-word count.
    out_lines: list[str] = []
    for line in content.split("\n"):
        if not has_vi(line):
            out_lines.append(line)
            continue
        # Strip backtick / quoted strings first — backticked example text
        # like `Given ... "Phở" ...` is intentional EN content.
        plain = re.sub(r"`[^`]*`|\"[^\"]*\"|'[^']*'", "", line)
        plain = re.sub(r"\b[A-Z]+(?:-[A-Z]+)*-\d+\b", "", plain)
        plain = re.sub(r"\b[a-z]+(?:_[a-z0-9]+)+\b", "", plain)
        vi_count = len(VI_DIACRITICS.findall(plain))
        letters = len(re.findall(r"[A-Za-zÀ-ỹ]", plain))
        density = vi_count / letters if letters else 0.0
        if vi_count >= 4 and density > 0.10:
            continue
        out_lines.append(line)
    content = "\n".join(out_lines)

    # 8. Collapse runs of blank lines and trailing whitespace
    content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip() + "\n"


def extract_vi(content: str) -> str:
    """Build a VI-only document from the bilingual source.

    Strategy: walk the source line by line, emitting:
      * pure-VI lines as-is,
      * the VI half of "EN / VI" headings & lines,
      * unwrapped italic `*(VI)*` annotations,
      * standalone `(VI)` parenthetical lines.

    Lines without any VI diacritics are skipped.
    """
    out_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line

        # Heading "## EN / Tiếng Việt" -> emit "## Tiếng Việt"
        m = re.match(r"^(#{1,6})([^\n/]*?)\s+/\s+([^\n]+)$", line)
        if m and has_vi(m.group(3)):
            out_lines.append(f"{m.group(1)} {m.group(3).strip()}")
            continue

        # Pure-VI heading line
        if re.match(r"^#{1,6}\s+", line) and has_vi(line):
            out_lines.append(line)
            continue

        # Italic *( ... )* VI annotation as a standalone line
        ms = re.match(r"^\s*\*\((.+?)\)\*\s*$", line)
        if ms and has_vi(ms.group(1)):
            out_lines.append(ms.group(1).strip())
            continue

        # Italic *( ... )* embedded mid-line: extract the VI portion
        if has_vi(line):
            embedded = re.findall(r"\*\((.+?)\)\*", line)
            if embedded and all(has_vi(e) for e in embedded):
                # Pure VI inside a `*( )*` wrapper — emit each
                for e in embedded:
                    out_lines.append(e.strip())
                continue

        # "EN / VI:**" inline within bold — emit "**VI:**"
        m2 = re.match(r"^(.*?)\s+/\s+([^/\n*]+?)(:?\*+)$", line)
        if m2 and has_vi(m2.group(2)):
            prefix_markup = re.match(r"^\s*\*+", m2.group(1))
            opener = prefix_markup.group(0) if prefix_markup else ""
            out_lines.append(f"{opener}{m2.group(2).strip()}{m2.group(3)}")
            continue

        # "/ [VI]" bracketed template marker
        if re.search(r"\s*/\s*\[[^\]\n]+\]", line):
            for vi_chunk in re.findall(r"/\s*\[([^\]\n]+)\]", line):
                if has_vi(vi_chunk):
                    out_lines.append(f"[{vi_chunk}]")
            continue

        # Trailing " / <Vietnamese...>" full-line tail
        m3 = re.match(r"^(.*?)\s+/\s+([^/\n]+)$", line)
        if m3 and has_vi(m3.group(2)):
            out_lines.append(m3.group(2).strip())
            continue

        # Standalone (VI) parenthetical line
        m4 = re.match(r"^[ \t]*\(([^)\n]+)\)[ \t]*$", line)
        if m4 and has_vi(m4.group(1)):
            out_lines.append(m4.group(1).strip())
            continue

        # Inline " (VI)" annotation after EN words: emit just the VI portion
        if has_vi(line):
            ann = re.findall(r"\(([^()\n]{2,})\)", line)
            vi_anns = [a for a in ann if has_vi(a) and not re.search(r"[A-Za-z]{4,}", a)]
            if vi_anns:
                for a in vi_anns:
                    out_lines.append(a.strip())
                continue
            # Fallback: line still has VI but didn't match any pattern — keep verbatim
            out_lines.append(line.strip())
            continue

        # No VI in this line — skip
        # (preserve a paragraph break if previous emission was non-empty and this
        # is a blank separator between VI blocks: handled by collapse below)

    body = "\n\n".join(l for l in out_lines if l.strip())
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def split_file(skills_path: Path, dry_run: bool = False) -> tuple[int, int, int]:
    """Returns (orig_size, en_size, vi_size)."""
    original = skills_path.read_text(encoding="utf-8")

    if not has_vi(original):
        return len(original), len(original), 0

    en = strip_to_en(original)
    vi = extract_vi(original)

    vi_path = skills_path.parent / "SKILLS-vn.md"

    if not dry_run:
        skills_path.write_text(en, encoding="utf-8")
        vi_path.write_text(vi, encoding="utf-8")

    return len(original), len(en), len(vi)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report sizes; do not write.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that SKILLS.md files contain no VI diacritics. Non-zero exit on failure.",
    )
    parser.add_argument(
        "--root",
        default="agents",
        help="Directory to scan for SKILLS.md files (default: agents).",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"Root directory not found: {root}", file=sys.stderr)
        return 2

    skills_files = sorted(root.glob("*/SKILLS.md"))
    if not skills_files:
        print(f"No SKILLS.md files under {root}/*/", file=sys.stderr)
        return 1

    if args.check:
        # Allow VI characters inside backtick / quoted spans — those are
        # intentional sample-AC strings (e.g. ``"Phở"``). Only flag VI text
        # that escapes those wrappers.
        def _strip_quoted(s: str) -> str:
            return re.sub(r"`[^`\n]*`|\"[^\"\n]*\"|'[^'\n]*'", "", s)

        bad: list[tuple[Path, list[str]]] = []
        for f in skills_files:
            text = f.read_text(encoding="utf-8")
            outside = _strip_quoted(text)
            if has_vi(outside):
                offenders = [
                    line
                    for line in text.splitlines()
                    if has_vi(_strip_quoted(line))
                ]
                bad.append((f, offenders))
        if bad:
            print("VI diacritics still present (outside quoted spans) in:")
            for path, lines in bad:
                print(f"  - {path}")
                for line in lines[:5]:
                    print(f"      {line[:160]}")
            return 1
        print(f"OK — all {len(skills_files)} SKILLS.md files are EN-only.")
        return 0

    total_orig = total_en = total_vi = 0
    for f in skills_files:
        orig, en_n, vi_n = split_file(f, dry_run=args.dry_run)
        total_orig += orig
        total_en += en_n
        total_vi += vi_n
        action = "[dry-run]" if args.dry_run else "wrote"
        print(f"{f}: {orig} -> EN {en_n} (-{(1-en_n/orig)*100:.1f}%) | VI {vi_n} | {action}")

    print("-" * 80)
    print(
        f"TOTAL: {total_orig} -> EN {total_en} (-{(1 - total_en / total_orig) * 100:.1f}%) "
        f"| VI {total_vi}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
