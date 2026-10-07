#!/usr/bin/env python3
"""Split Projeto Machado dump into one raw .txt per main novel (with/without PER names).

NER masking uses spaCy Portuguese models and is imperfect on 19th-century literary
Portuguese: toponyms and missed person entities can still leak the book label.
Only PER entities are replaced; LOC is left intact.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DUMP_PATH = ROOT / "projetomachado" / "textonormalizado1000.txt"
OUT_WITH = ROOT / "livros_com_nomes"
OUT_WITHOUT = ROOT / "livros_sem_nomes"
MANIFEST_PATH = ROOT / "manifest.json"

# Canonical novels present in the dump (Ressurreição is missing).
NOVELS: dict[str, str] = {
    "A MAO E A LUVA": "a_mao_e_a_luva",
    "HELENA": "helena",
    "IAIA GARCIA": "iaia_garcia",
    "MEMORIAS POSTUMAS DE BRAS CUBAS": "memorias_postumas_de_bras_cubas",
    "QUINCAS BORBA": "quincas_borba",
    "DOM CASMURRO": "dom_casmurro",
    "ESAU E JACO": "esau_e_jaco",
    "MEMORIAL DE AIRES": "memorial_de_aires",
}

TITLE_BY_SLUG = {
    "a_mao_e_a_luva": "A Mão e a Luva",
    "helena": "Helena",
    "iaia_garcia": "Iaiá Garcia",
    "memorias_postumas_de_bras_cubas": "Memórias Póstumas de Brás Cubas",
    "quincas_borba": "Quincas Borba",
    "dom_casmurro": "Dom Casmurro",
    "esau_e_jaco": "Esaú e Jacó",
    "memorial_de_aires": "Memorial de Aires",
}

AUTHOR_LINE = "Machado de Assis"
NAME_TOKEN = "[NOME]"
SPACY_MODELS = ("pt_core_news_lg", "pt_core_news_md", "pt_core_news_sm")


def normalize_title(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def looks_like_title(title: str) -> bool:
    if not (2 <= len(title) <= 80):
        return False
    if title[-1:] in ",;:":
        return False
    if "Fonte:" in title:
        return False
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(c.isupper() for c in letters) / len(letters)
    return upper_ratio >= 0.55


def detect_work_starts(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (start_line_idx, raw_title, normalized_title) for likely work starts."""
    starts: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        if line.strip() != AUTHOR_LINE:
            continue
        if i == 0:
            continue
        title = lines[i - 1].strip()
        if not looks_like_title(title):
            continue
        # Prefer starting at Biblioteca Nacional header when present just above title.
        start = i - 1
        if (
            i >= 4
            and lines[i - 4].strip() == "MINISTÉRIO DA CULTURA"
            and lines[i - 3].strip() == "Fundação Biblioteca Nacional"
            and lines[i - 2].strip() == "Departamento Nacional do Livro"
        ):
            start = i - 4
        starts.append((start, title, normalize_title(title)))

    # Drop near-duplicate consecutive starts with the same normalized title.
    cleaned: list[tuple[int, str, str]] = []
    for start, title, norm in starts:
        if cleaned and cleaned[-1][2] == norm and start - cleaned[-1][0] < 300:
            continue
        cleaned.append((start, title, norm))
    return cleaned


def extract_novels(lines: list[str]) -> dict[str, dict]:
    starts = detect_work_starts(lines)
    # All starts define slice ends so novel boundaries respect intervening works.
    ends = [s[0] for s in starts[1:]] + [len(lines)]

    best: dict[str, dict] = {}
    for (start, raw_title, norm), end in zip(starts, ends):
        slug = NOVELS.get(norm)
        if slug is None:
            continue
        text = "\n".join(lines[start:end])
        if not text.endswith("\n"):
            text += "\n"
        candidate = {
            "slug": slug,
            "title": TITLE_BY_SLUG[slug],
            "raw_title": raw_title,
            "start_line": start + 1,  # 1-based for humans
            "end_line": end,
            "n_lines": end - start,
            "n_chars": len(text),
            "text": text,
        }
        prev = best.get(slug)
        if prev is None or candidate["n_chars"] > prev["n_chars"]:
            best[slug] = candidate

    missing = [slug for slug in TITLE_BY_SLUG if slug not in best]
    if missing:
        raise RuntimeError(f"Missing novels in dump: {missing}")
    if len(best) != len(NOVELS):
        raise RuntimeError(f"Expected {len(NOVELS)} novels, got {len(best)}")
    return best


def load_spacy():
    import spacy

    last_err: Exception | None = None
    for name in SPACY_MODELS:
        try:
            return spacy.load(name), name
        except Exception as exc:  # noqa: BLE001 - try next model
            last_err = exc
    raise RuntimeError(
        "No Portuguese spaCy model found. Install with: "
        "python -m spacy download pt_core_news_lg"
    ) from last_err


def mask_person_names(text: str, nlp) -> tuple[str, int]:
    """Replace PER entities with NAME_TOKEN. Returns (masked_text, n_replacements)."""
    # spaCy default max length is 1M chars; novels can be longer.
    if len(text) > nlp.max_length:
        nlp.max_length = len(text) + 1000

    parts: list[str] = []
    n_repl = 0
    # Process in chunks to keep memory reasonable, preserving offsets via join.
    chunk_size = 400_000
    if len(text) <= chunk_size:
        chunks = [text]
    else:
        chunks = []
        i = 0
        while i < len(text):
            j = min(i + chunk_size, len(text))
            if j < len(text):
                # Prefer splitting on newline to avoid cutting entities.
                nl = text.rfind("\n", i, j)
                if nl > i:
                    j = nl + 1
            chunks.append(text[i:j])
            i = j

    for chunk in chunks:
        doc = nlp(chunk)
        out = list(chunk)
        # Replace from the end so indices stay valid.
        for ent in sorted(doc.ents, key=lambda e: e.start_char, reverse=True):
            if ent.label_ != "PER":
                continue
            out[ent.start_char : ent.end_char] = list(NAME_TOKEN)
            n_repl += 1
        parts.append("".join(out))
    return "".join(parts), n_repl


def write_outputs(novels: dict[str, dict], nlp, model_name: str) -> list[dict]:
    OUT_WITH.mkdir(parents=True, exist_ok=True)
    OUT_WITHOUT.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for slug in sorted(novels, key=lambda s: TITLE_BY_SLUG[s]):
        book = novels[slug]
        path_with = OUT_WITH / f"{slug}.txt"
        path_without = OUT_WITHOUT / f"{slug}.txt"

        path_with.write_text(book["text"], encoding="utf-8")
        masked, n_names = mask_person_names(book["text"], nlp)
        path_without.write_text(masked, encoding="utf-8")

        entry = {
            "title": book["title"],
            "slug": slug,
            "raw_title_in_dump": book["raw_title"],
            "start_line": book["start_line"],
            "end_line": book["end_line"],
            "n_lines": book["n_lines"],
            "n_chars": book["n_chars"],
            "n_nome_tokens": n_names,
            "file_com_nomes": str(path_with.relative_to(ROOT)),
            "file_sem_nomes": str(path_without.relative_to(ROOT)),
            "spacy_model": model_name,
        }
        manifest.append(entry)
        print(
            f"{book['title']}: {book['n_chars']} chars, "
            f"{n_names} PER -> {NAME_TOKEN} (start line {book['start_line']})"
        )
    return manifest


def main() -> None:
    if not DUMP_PATH.is_file():
        raise FileNotFoundError(f"Dump not found: {DUMP_PATH}")

    print(f"Reading {DUMP_PATH} ...")
    lines = DUMP_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    novels = extract_novels(lines)
    print(f"Selected {len(novels)} novels (longest edition each).")

    nlp, model_name = load_spacy()
    print(f"Loaded spaCy model: {model_name}")

    manifest = write_outputs(novels, nlp, model_name)
    payload = {
        "source": str(DUMP_PATH.relative_to(ROOT)),
        "n_novels": len(manifest),
        "name_token": NAME_TOKEN,
        "note": (
            "Raw slices from the dump (no page/short-line cleanup). "
            "Only PER entities are masked in livros_sem_nomes; NER is imperfect."
        ),
        "books": manifest,
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
