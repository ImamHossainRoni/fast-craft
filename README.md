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
apps/       # feature modules (users, ...)
core/       # shared/core utilities (db session, management commands, etc.)
config.py   # settings loaded from .env
main.py     # FastAPI app + routers
manage.py   # CLI entrypoint for management commands
run.py      # entrypoint
```

## Management commands

Django-style CLI for project tasks, run via `manage.py`:

```bash
python manage.py <command> [args...]
```

### `startapp`

Scaffolds a new feature module inside `apps/`, following the same pattern as the existing `users` app (`models.py`, `schemas.py`, `dao.py`, `services.py`, `views.py`, `urls.py`).

```bash
python manage.py startapp <app_name>
```

After creating the app, wire its router into `main.py`:

```python
from apps.<app_name>.urls import router as <app_name>_router
app.include_router(<app_name>_router, prefix="/<app_name>", tags=["<AppName>"])
```

New commands can be added under `core/management/commands/` by subclassing `BaseCommand` — they're auto-discovered, no registration needed.

More modules and proper auth are on the way.
