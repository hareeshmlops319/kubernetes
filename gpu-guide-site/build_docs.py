"""Split NVIDIA-GPU-Operator-Guide.md into one MkDocs page per top-level section.

Run from anywhere:  python build_docs.py
Re-run whenever the source guide changes; docs/ is regenerated.
"""
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "NVIDIA-GPU-Operator-Guide.md"
PAGES = HERE / "pages"  # standalone pages, copied as-is and listed after the guide
DOCS = HERE / "docs"

SECTION_RE = re.compile(r"^## (\d+)\. (.+)$")


def slugify(text):
    # Matches Python-Markdown's toc slugify (and GitHub's for these headings).
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def page_name(num, title):
    short = slugify(title.split(":")[0])
    return f"{int(num):02d}-{short}.md"


def main():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()

    # Intro = everything before the first numbered section, minus the manual TOC.
    first = next(i for i, l in enumerate(lines) if SECTION_RE.match(l))
    intro = lines[:first]

    sections = []  # (num, title, filename, body_lines)
    current = None
    for line in lines[first:]:
        m = SECTION_RE.match(line)
        if m:
            num, title = m.groups()
            current = (num, title, page_name(num, title), [])
            sections.append(current)
        else:
            current[3].append(line)

    # Map each section's anchor to its page so in-guide links keep working.
    anchor_to_page = {slugify(f"{n}. {t}"): f for n, t, f, _ in sections}

    def fix_links(text):
        def repl(m):
            anchor = m.group(1)
            return f"]({anchor_to_page[anchor]})" if anchor in anchor_to_page else m.group(0)
        return re.sub(r"\]\(#([^)]+)\)", repl, text)

    def demote(body):
        out, in_fence = [], False
        for l in body:
            if l.lstrip().startswith("```"):
                in_fence = not in_fence
            if not in_fence and re.match(r"^#{3,6} ", l):
                l = l[1:]
            out.append(l)
        # Drop trailing horizontal rule separators between sections.
        while out and out[-1].strip() in ("", "---"):
            out.pop()
        return out

    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()

    extra_pages = []  # (title, filename)
    for p in sorted(PAGES.glob("*.md")) if PAGES.exists() else []:
        text = p.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), p.stem)
        extra_pages.append((title, p.name))
        shutil.copyfile(p, DOCS / p.name)

    # Home page: intro without the hand-written TOC (the site nav replaces it).
    home, skip = [], False
    for l in intro:
        if l.startswith("## Table of Contents"):
            skip = True
            home.append("## Contents\n")
            for n, t, f, _ in sections:
                home.append(f"{n}. [{t}]({f})")
            if extra_pages:
                home.append("\n## More guides\n")
                for title, f in extra_pages:
                    home.append(f"- [{title}]({f})")
            continue
        if skip:
            if l.strip() == "---":
                skip = False
                home.append("")
            continue
        home.append(l)
    (DOCS / "index.md").write_text(fix_links("\n".join(home)).rstrip() + "\n", encoding="utf-8")

    for n, t, f, body in sections:
        page = [f"# {n}. {t}", ""] + demote(body)
        (DOCS / f).write_text(fix_links("\n".join(page)).rstrip() + "\n", encoding="utf-8")

    print(f"Wrote index.md + {len(sections)} section pages + {len(extra_pages)} extra pages to {DOCS}")


if __name__ == "__main__":
    main()
