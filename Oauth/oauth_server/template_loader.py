"""Shared Jinja2Templates instance — avoids circular imports."""

from pathlib import Path

from starlette.templating import Jinja2Templates

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
