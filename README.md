# FastCraft

A minimal FastAPI starter kit I'm using to bootstrap backend projects without redoing the same setup every time.

Comes with async SQLAlchemy, a simple project structure (`app/` for features, `core/` for shared stuff), and env-based config via `python-decouple`. Still early — just a basic users module in place for now, with JWT settings wired up for auth to come later.

## Stack

- FastAPI
- SQLAlchemy (async, SQLite via `aiosqlite`)
- Pydantic v2 / pydantic-settings
- Uvicorn

## Getting started

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.sample .env
# fill in your own SECRET_KEY etc.

python run.py
```

App runs on `http://localhost:8000`. Docs at `/docs`.

## Structure

```
app/        # feature modules (users, ...)
core/       # shared/core utilities (db session, etc.)
config.py   # settings loaded from .env
main.py     # FastAPI app + routers
run.py      # entrypoint
```

More modules and proper auth are on the way.
