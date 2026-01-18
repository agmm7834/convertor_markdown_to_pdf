import argparse
import asyncio
from pathlib import Path

import markdown as md
from playwright.async_api import async_playwright


DEFAULT_CSS = r"""
:root { color-scheme: light; }
body {
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 12.5pt;
  line-height: 1.55;
  color: #111;
  padding: 24px;
}
h1,h2,h3 { line-height: 1.25; margin: 1.1em 0 0.5em; }
h1 { font-size: 2.0em; }
h2 { font-size: 1.6em; }
h3 { font-size: 1.25em; }

p { margin: 0.6em 0; }
ul,ol { margin: 0.6em 0 0.6em 1.3em; }
blockquote {
  margin: 0.8em 0;
  padding: 0.2em 1em;
  border-left: 4px solid #ddd;
  color: #444;
}
hr { border: none; border-top: 1px solid #e5e5e5; margin: 1.2em 0; }

table { border-collapse: collapse; margin: 0.8em 0; width: 100%; }
th, td { border: 1px solid #e5e5e5; padding: 8px 10px; vertical-align: top; }
th { background: #fafafa; }

code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
pre {
  background: #0b1021;
  color: #e6e6e6;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
}
pre code { color: inherit; }

img { max-width: 100%; height: auto; }
a { color: #0b57d0; text-decoration: none; }
a:hover { text-decoration: underline; }

@page { size: A4; margin: 16mm 14mm; }
"""

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def pick_file_dialog() -> Path | None:
    """
    Windows file picker. Не требует никаких библиотек, tkinter идет с Python.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Выбери Markdown файл",
        filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
    )
    root.destroy()

    if not file_path:
        return None
    return Path(file_path)


def markdown_to_html(md_text: str) -> str:
    return md.markdown(
        md_text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "sane_lists",
        ],
        output_format="html5",
    )


async def render_pdf(html_path: Path, pdf_path: Path, timeout_ms: int = 60000) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # file:// чтобы относительные картинки работали
        await page.goto(html_path.as_uri(), wait_until="networkidle", timeout=timeout_ms)

        await page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )

        await browser.close()


def main():
    ap = argparse.ArgumentParser(description="Convert Markdown to PDF via Chromium (Playwright).")
    ap.add_argument("input_md", nargs="?", help="Path to input .md (optional, will open picker if omitted).")
    ap.add_argument("-o", "--output", help="Path to output .pdf (default: рядом с md).")
    ap.add_argument("--css", help="Optional path to extra CSS file to append.")
    args = ap.parse_args()

    md_path = Path(args.input_md).resolve() if args.input_md else None

    # Если путь не передали или он битый - откроем picker
    if md_path is None or not md_path.exists():
        if md_path is not None and not md_path.exists():
            print(f"Input not found: {md_path}\nОткрою выбор файла...")
        picked = pick_file_dialog()
        if not picked:
            raise SystemExit("Не выбран файл. Выход.")
        md_path = picked.resolve()

    if md_path.suffix.lower() != ".md":
        print("Предупреждение: выбран файл не .md, но попробую конвертнуть как текст.")

    pdf_path = Path(args.output).resolve() if args.output else md_path.with_suffix(".pdf")

    md_text = md_path.read_text(encoding="utf-8")
    body_html = markdown_to_html(md_text)

    css = DEFAULT_CSS
    if args.css:
        css_path = Path(args.css).resolve()
        if css_path.exists():
            css += "\n\n" + css_path.read_text(encoding="utf-8")
        else:
            print(f"CSS файл не найден: {css_path} (пропускаю)")

    full_html = HTML_TEMPLATE.format(css=css, body=body_html)

    # Временный html кладем рядом с md, чтобы относительные пути (картинки) работали.
    tmp_name = f".__md2pdf__{md_path.stem}.html"
    html_path = md_path.parent / tmp_name

    # <base href="..."> чтобы ./img.png точно нашлись
    base_href = md_path.parent.as_uri() + "/"
    full_html = full_html.replace("<head>", f"<head>\n  <base href=\"{base_href}\">", 1)

    html_path.write_text(full_html, encoding="utf-8")

    try:
        asyncio.run(render_pdf(html_path, pdf_path))
        print(f"OK: {pdf_path}")
    finally:
        try:
            html_path.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
