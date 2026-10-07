"""Serves the HTML pages. Private pages redirect to /login when there is no valid session."""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.dependencies import get_optional_user
from app.database.models import User
from app.templating import templates

router = APIRouter(include_in_schema=False)

PRIVATE_PAGES = [
    ("/dashboard", "dashboard.html", "dashboard"),
    ("/roadmap", "roadmap.html", "roadmap"),
    ("/resources", "resources.html", "resources"),
    ("/tech-updates", "tech_updates.html", "tech_updates"),
    ("/tasks", "tasks.html", "tasks"),
    ("/community", "community.html", "community"),
    ("/profile", "profile.html", "profile"),
]


def _private(template: str, page: str):
    def handler(request: Request, user: Optional[User] = Depends(get_optional_user)):
        if user is None:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(request, template, {"page": page})
    return handler


for _path, _tpl, _page in PRIVATE_PAGES:
    router.add_api_route(_path, _private(_tpl, _page), methods=["GET"], response_class=HTMLResponse)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: Optional[User] = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "index.html", {"page": "home", "logged_in": user is not None})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"page": "login"})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: Optional[User] = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"page": "register"})
