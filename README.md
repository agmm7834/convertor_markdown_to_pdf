# Markdown to PDF (Python, Windows uchun qulay)

Bu kichik loyiha Markdown (.md) faylni PDF’ga sifatli konvert qiladi:
- jadval (tables), fenced code
- kod uchun highlight (pygments)
- rasm va nisbiy yo’llar (./images/...)
- PDF chiqarish Chromium (Playwright) orqali, Windows’da odatda eng barqaror yo’l

## Talablar
- Python 3.10+ tavsiya qilinadi

## O’rnatish (Windows)

### 1) Virtualenv
```bash
python -m venv venv
venv\Scripts\activate

pip install markdown pygments playwright
playwright install chromium

python main.py docs\readme.md -o out.pdf
