"""The HomeKeep website (Flask). The rules, lookup, map and PDFs live in titlecheck/; this is just the pages.

HomeKeep Pro (pro/ and web/pro_routes.py) is registered on the same app under /pro and /f. The free pages never use
its database or sign-in.
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from titlecheck.i18n import t
from web.markup import md

ROOT = Path(__file__).resolve().parent.parent


def create_app(pro_config=None) -> Flask:
    from pro.config import ProConfig
    from pro.db import make_engine

    # public/ holds the stylesheet and script. Vercel serves that folder itself; Flask serves it when run locally.
    app = Flask(__name__, static_folder=str(ROOT / "public"), static_url_path="")
    app.jinja_env.filters["md"] = md
    app.jinja_env.globals["t"] = t           # {{ t("English text") }} in templates, translated for the visitor

    cfg = pro_config or ProConfig()
    app.secret_key = cfg.session_secret()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),
                      MAX_CONTENT_LENGTH=cfg.max_upload_bytes + 64 * 1024)
    app.extensions["homekeep_pro"] = {"cfg": cfg, "engine": make_engine(cfg.database_url)}

    from web.routes import bp
    from web.pro_routes import bp as pro_bp
    app.register_blueprint(bp)
    app.register_blueprint(pro_bp)

    if cfg.pro_site:
        # The stand-alone Pro deployment: its home page is the Pro landing page. The free checkup stays at its own site.
        from flask import redirect, request

        @app.before_request
        def pro_site_home():
            if request.path == "/":
                return redirect("/pro", code=302)
    return app
