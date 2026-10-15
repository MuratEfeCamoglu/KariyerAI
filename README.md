# KariyerAI

İK ekipleri için AI destekli CV değerlendirme aracı. CV'leri (PDF/DOCX) okur, yapılandırır, ilan
kriterlerine göre 0–100 arası kanıtlı uyum puanı verir ve adayları sıralar. **Son kararı her zaman
İK uzmanı verir**; sistem otomatik eleme yapmaz.

- Kapsam, mimari, veri modeli: [ISKELET.md](ISKELET.md)
- Geliştirme komutları ve kod kuralları: [CLAUDE.md](CLAUDE.md)
- AI agent çalışma sözleşmesi: [AGENT.md](AGENT.md)
- Arayüz tasarımı: [docs/TASARIM.md](docs/TASARIM.md)

## Gereksinimler

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 24 LTS + npm

## Kurulum ve çalıştırma

Backend (`backend/` içinde):

```bash
uv sync
copy .env.example .env        # macOS/Linux: cp .env.example .env
uv run alembic upgrade head
uv run fastapi dev app/main.py   # http://localhost:8000 · sağlık: /api/health · docs: /docs
```

`.env.example` varsayılan olarak `LLM_PROVIDER=fake` kullanır; API anahtarı olmadan çalışır.
Gerçek Claude API için `.env`'de `LLM_PROVIDER=anthropic` ve `ANTHROPIC_API_KEY` ayarlayın.

Frontend (`frontend/` içinde, ayrı terminalde):

```bash
npm install
npm run dev     # http://localhost:5173 — /api istekleri :8000'e proxy'lenir
```

## Doğrulama

```bash
# backend/
uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
# frontend/
npm run lint && npm run format:check && npm run typecheck && npm run test && npm run build
```
