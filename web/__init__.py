"""The Home Title Checkup website (Flask). The rules, lookup, map and PDFs live in titlecheck/; this is just the pages."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from web.markup import md

ROOT = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    # public/ holds the stylesheet and script. Vercel serves that folder itself; Flask serves it when run locally.
    app = Flask(__name__, static_folder=str(ROOT / "public"), static_url_path="")
    app.jinja_env.filters["md"] = md
    from web.routes import bp
    app.register_blueprint(bp)
    return app
