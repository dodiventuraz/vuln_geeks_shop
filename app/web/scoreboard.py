"""Route scoreboard (SSR): submit flag & lihat progres.

Mode free-form: progres disimpan di session, tidak ada akun/kompetisi.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.core import scoreboard
from app.core.security import get_current_user
from app.core.templating import templates

router = APIRouter(tags=["web-scoreboard"])


def _render(request: Request, user, *, message: str = "", ok: bool = False):
    solved = set(request.session.get("solved", []))
    items = scoreboard.all_challenges()
    return templates.TemplateResponse(
        "scoreboard.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "solved": solved,
            "solved_count": len(solved),
            "total": scoreboard.total_flags(),
            "message": message,
            "message_ok": ok,
        },
    )


@router.get("/scoreboard", response_class=HTMLResponse)
def scoreboard_view(request: Request, user=Depends(get_current_user)):
    return _render(request, user)


@router.post("/submit-flag", response_class=HTMLResponse)
def submit_flag(request: Request, flag: str = Form(...), user=Depends(get_current_user)):
    cid = scoreboard.check_flag(flag)
    if cid:
        solved = set(request.session.get("solved", []))
        already = cid in solved
        solved.add(cid)
        request.session["solved"] = sorted(solved)
        msg = f"✔ Benar! Challenge {cid} " + ("sudah tercatat." if already else "berhasil dipecahkan.")
        return _render(request, user, message=msg, ok=True)
    return _render(request, user, message="✗ Flag tidak dikenali. Coba lagi.", ok=False)
