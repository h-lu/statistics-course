from __future__ import annotations

import csv
import io
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import db
from .config import Settings
from .questions import CURRENT_BANKS, DEFAULT_BANK, bank_for_lesson


PHASE_LABELS = {
    "closed": "尚未开始",
    "a": "A 版基础题",
    "learn": "AI 学习",
    "b": "B 版变式题",
    "result": "反馈",
}
CONFIDENCE_LABELS = {
    "guess": "猜测",
    "unsure": "不太确定",
    "sure": "确定",
}


def format_timestamp(value: object) -> str:
    if not value:
        return "—"
    try:
        shanghai = datetime.fromisoformat(str(value)).astimezone(ZoneInfo("Asia/Shanghai"))
        return shanghai.strftime("%Y-%m-%d %H:%M 上海时间")
    except ValueError:
        return str(value)


def empty_session() -> dict[str, object]:
    return {
        "id": 0,
        "lesson_id": "—",
        "title": "尚未创建场次",
        "phase": "closed",
        "phase_ends_at": None,
        "created_at": None,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    db.initialize(
        settings.database_path, DEFAULT_BANK.lesson_id, DEFAULT_BANK.title
    )

    app = FastAPI(title="Stat Check", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="statcheck_session",
        path=settings.base_path,
        same_site="lax",
        https_only=settings.secure_cookie,
        max_age=60 * 60 * 10,
    )

    app_dir = Path(__file__).parent
    app.mount(
        f"{settings.base_path}/static",
        StaticFiles(directory=app_dir / "static"),
        name="static",
    )
    templates = Jinja2Templates(directory=app_dir / "templates")
    router = APIRouter(prefix=settings.base_path)

    def ensure_csrf(request: Request) -> str:
        token = request.session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(24)
            request.session["csrf_token"] = token
        return str(token)

    def verify_csrf(request: Request, token: str) -> None:
        expected = request.session.get("csrf_token")
        if not expected or not secrets.compare_digest(str(expected), token):
            raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试")

    def current_user(request: Request):
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        return db.get_user(settings.database_path, int(user_id))

    def require_user(request: Request):
        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录")
        return user

    def require_teacher(request: Request):
        user = require_user(request)
        if user["role"] != "teacher":
            raise HTTPException(status_code=403, detail="仅教师可访问")
        return user

    def bank_for_session(session):
        try:
            return bank_for_lesson(str(session["lesson_id"]))
        except LookupError as error:
            raise HTTPException(
                status_code=500,
                detail="当前场次对应的题库不存在，请联系教师",
            ) from error

    def phase_expired(session) -> bool:
        raw_deadline = session["phase_ends_at"]
        if not raw_deadline:
            return False
        return datetime.fromisoformat(str(raw_deadline)) <= db.utc_now()

    def render(request: Request, name: str, **context) -> HTMLResponse:
        payload = {
            "request": request,
            "base_path": settings.base_path,
            "csrf_token": ensure_csrf(request),
            "user": current_user(request),
            "phase_labels": PHASE_LABELS,
            "format_timestamp": format_timestamp,
            **context,
        }
        return templates.TemplateResponse(
            request=request, name=name, context=payload
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @router.get("/healthz")
    def healthz() -> dict[str, str]:
        session = db.current_session(settings.database_path)
        if session is not None:
            bank_for_session(session)
        return {"status": "ok"}

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request):
        user = current_user(request)
        if user is None:
            return render(request, "login.html", oauth_ready=bool(settings.gitea_client_id))
        destination = "teacher" if user["role"] == "teacher" else "current"
        return RedirectResponse(
            f"{settings.base_path}/{destination}", status_code=303
        )

    @router.get("/login")
    def login(request: Request):
        if not settings.gitea_client_id or not settings.gitea_client_secret:
            raise HTTPException(status_code=503, detail="Gitea 登录尚未配置")
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        query = urlencode(
            {
                "client_id": settings.gitea_client_id,
                "redirect_uri": f"{settings.public_base_url}/auth/callback",
                "response_type": "code",
                "scope": "read:user",
                "state": state,
            }
        )
        return RedirectResponse(
            f"{settings.gitea_base_url}/login/oauth/authorize?{query}",
            status_code=302,
        )

    @router.get("/auth/callback")
    async def oauth_callback(request: Request, code: str, state: str):
        expected = request.session.pop("oauth_state", None)
        if not expected or not secrets.compare_digest(str(expected), state):
            raise HTTPException(status_code=400, detail="登录状态无效，请重新登录")
        redirect_uri = f"{settings.public_base_url}/auth/callback"
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                f"{settings.gitea_base_url}/login/oauth/access_token",
                data={
                    "client_id": settings.gitea_client_id,
                    "client_secret": settings.gitea_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_response.is_error:
                # Authorization codes are single-use. A browser retry or a
                # stale callback should return to the login page instead of
                # exposing an Internal Server Error.
                return RedirectResponse(
                    f"{settings.base_path}/?oauth_error=retry", status_code=303
                )
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Gitea 未返回访问令牌")
            user_response = await client.get(
                f"{settings.gitea_base_url}/api/v1/user",
                headers={"Authorization": f"token {access_token}"},
            )
            user_response.raise_for_status()
            profile = user_response.json()
        login_name = str(profile["login"])
        display_name = str(profile.get("full_name") or login_name)
        role = (
            "teacher"
            if login_name.casefold() in settings.teacher_logins
            else "student"
        )
        user = db.upsert_user(
            settings.database_path,
            gitea_id=int(profile["id"]),
            login=login_name,
            display_name=display_name,
            role=role,
        )
        request.session.clear()
        request.session["user_id"] = int(user["id"])
        return RedirectResponse(f"{settings.base_path}/", status_code=303)

    @router.post("/logout")
    def logout(request: Request, csrf_token: str = Form(...)):
        verify_csrf(request, csrf_token)
        request.session.clear()
        return RedirectResponse(f"{settings.base_path}/", status_code=303)

    @router.get("/current", response_class=HTMLResponse, name="student_current")
    def student_current(request: Request):
        user = require_user(request)
        session = db.current_session(settings.database_path)
        if session is None:
            return render(
                request,
                "waiting.html",
                session=empty_session(),
                title="尚未创建自查场次",
                message="请等待教师创建本节课的自查场次。",
            )
        bank = bank_for_session(session)
        phase = str(session["phase"])
        if phase in {"a", "learn", "b"} and phase_expired(session):
            return render(
                request,
                "waiting.html",
                session=session,
                title=f"{PHASE_LABELS[phase]}计时已结束",
                message="本阶段不再接受提交，请等待教师开放下一阶段。",
            )
        if phase in {"a", "b"}:
            existing = {
                row["concept_id"]
                for row in db.responses_for_user(
                    settings.database_path, int(session["id"]), int(user["id"])
                )
                if row["phase"] == phase
            }
            next_concept = next(
                (concept for concept in bank.concept_ids if concept not in existing),
                None,
            )
            if next_concept:
                item = bank.item(next_concept)
                return render(
                    request,
                    "attempt.html",
                    session=session,
                    phase=phase,
                    item=item,
                    question=bank.question(next_concept, phase),
                    question_number=len(existing) + 1,
                    question_total=len(bank.items),
                    confidence_labels=CONFIDENCE_LABELS,
                )
            return render(
                request,
                "waiting.html",
                session=session,
                title=f"{PHASE_LABELS[phase]}已完成",
                message="答案已经锁定，请等待教师开放下一阶段。",
            )
        if phase == "learn":
            return render(
                request,
                "learn.html",
                session=session,
                items=bank.items,
                completed=db.learning_complete(
                    settings.database_path, int(session["id"]), int(user["id"])
                ),
            )
        if phase == "result":
            rows = db.responses_for_user(
                settings.database_path, int(session["id"]), int(user["id"])
            )
            response_map = {
                (row["concept_id"], row["phase"]): row for row in rows
            }
            results = []
            for item in bank.items:
                concept_id = str(item["concept_id"])
                results.append(
                    {
                        "title": item["title"],
                        "a": response_map.get((concept_id, "a")),
                        "b": response_map.get((concept_id, "b")),
                        "explanation": item["pair"]["b"]["explanation"],
                    }
                )
            return render(
                request, "result.html", session=session, results=results
            )
        return render(
            request,
            "waiting.html",
            session=session,
            title="本节自查尚未开始",
            message="教师开放 A 版后，页面会自动更新；也可以点击下方按钮刷新。",
        )

    @router.get("/state")
    def student_state(request: Request) -> dict[str, str | int | None]:
        require_user(request)
        session = db.current_session(settings.database_path)
        if session is None:
            return {"session_id": None, "phase": "closed", "phase_ends_at": None}
        bank_for_session(session)
        return {
            "session_id": int(session["id"]),
            "phase": str(session["phase"]),
            "phase_ends_at": session["phase_ends_at"],
        }

    @router.post("/answer")
    def submit_answer(
        request: Request,
        csrf_token: str = Form(...),
        session_id: int = Form(...),
        concept_id: str = Form(...),
        phase: str = Form(...),
        option_id: str = Form(...),
        confidence: str = Form(...),
    ):
        verify_csrf(request, csrf_token)
        user = require_user(request)
        session = db.current_session(settings.database_path)
        if session is None:
            raise HTTPException(status_code=409, detail="当前没有开放的自查场次")
        if session_id != int(session["id"]):
            raise HTTPException(status_code=409, detail="当前场次已经变化")
        bank = bank_for_session(session)
        if phase not in {"a", "b"} or session["phase"] != phase:
            raise HTTPException(status_code=409, detail="当前阶段已经变化")
        if phase_expired(session):
            raise HTTPException(status_code=409, detail="本阶段计时已经结束")
        if concept_id not in bank.concept_ids:
            raise HTTPException(status_code=400, detail="题目不存在")
        question = bank.question(concept_id, phase)
        valid_options = {str(option["id"]) for option in question["options"]}
        if option_id not in valid_options or confidence not in CONFIDENCE_LABELS:
            raise HTTPException(status_code=400, detail="答案不完整")
        try:
            db.save_response(
                settings.database_path,
                session_id=int(session["id"]),
                user_id=int(user["id"]),
                concept_id=concept_id,
                phase=phase,
                option_id=option_id,
                confidence=confidence,
                correct=option_id == str(question["answer"]),
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="本题已经提交并锁定") from error
        return RedirectResponse(f"{settings.base_path}/current", status_code=303)

    @router.post("/learn/complete")
    def complete_learning(
        request: Request,
        csrf_token: str = Form(...),
        session_id: int = Form(...),
    ):
        verify_csrf(request, csrf_token)
        user = require_user(request)
        session = db.current_session(settings.database_path)
        if session is None:
            raise HTTPException(status_code=409, detail="当前没有开放的自查场次")
        if session_id != int(session["id"]):
            raise HTTPException(status_code=409, detail="当前场次已经变化")
        bank_for_session(session)
        if session["phase"] != "learn":
            raise HTTPException(status_code=409, detail="当前不是学习阶段")
        if phase_expired(session):
            raise HTTPException(status_code=409, detail="学习阶段计时已经结束")
        db.mark_learning_complete(
            settings.database_path, int(session["id"]), int(user["id"])
        )
        return RedirectResponse(f"{settings.base_path}/current", status_code=303)

    @router.get("/teacher", response_class=HTMLResponse, name="teacher_dashboard")
    def teacher_dashboard(request: Request, session_id: int | None = None):
        require_teacher(request)
        current = db.current_session(settings.database_path)
        if current is None:
            return render(
                request,
                "teacher.html",
                session=empty_session(),
                no_session=True,
                summary={"students": 0, "completed": {"a": 0, "learn": 0, "b": 0}, "aggregates": []},
                concepts=[],
                phases=("closed", "a", "learn", "b", "result"),
                question_banks=CURRENT_BANKS,
                session_history=[],
                viewing_history=False,
                current_session_id=None,
            )
        session = current if session_id is None else db.get_session(settings.database_path, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="场次不存在")
        bank = bank_for_session(session)
        summary = db.dashboard_summary(
            settings.database_path, int(session["id"]), len(bank.items)
        )
        aggregate_map = {
            (row["concept_id"], row["phase"]): row
            for row in summary["aggregates"]
        }
        concepts = []
        for item in bank.items:
            concept = {"title": item["title"], "a": None, "b": None}
            for phase in ("a", "b"):
                row = aggregate_map.get((item["concept_id"], phase))
                if row and row["answered"]:
                    concept[phase] = round(
                        100 * row["correct_count"] / row["answered"]
                    )
            concepts.append(concept)
        return render(
            request,
            "teacher.html",
            session=session,
            summary=summary,
            concepts=concepts,
            phases=("closed", "a", "learn", "b", "result"),
            question_banks=CURRENT_BANKS,
            session_history=db.session_history(settings.database_path),
            viewing_history=session_id is not None and int(session["id"]) != int(current["id"]),
            current_session_id=int(current["id"]),
            no_session=False,
        )

    @router.post("/teacher/session")
    def teacher_create_session(
        request: Request,
        csrf_token: str = Form(...),
        lesson_id: str = Form(...),
    ):
        verify_csrf(request, csrf_token)
        require_teacher(request)
        try:
            bank = bank_for_lesson(lesson_id)
        except LookupError as error:
            raise HTTPException(status_code=400, detail="所选课次不存在") from error
        db.create_session(settings.database_path, bank.lesson_id, bank.title)
        return RedirectResponse(f"{settings.base_path}/teacher", status_code=303)

    @router.post("/teacher/session/delete")
    def teacher_delete_session(
        request: Request,
        csrf_token: str = Form(...),
        session_id: int = Form(...),
        force: bool = Form(False),
    ):
        verify_csrf(request, csrf_token)
        require_teacher(request)
        error = db.delete_session(settings.database_path, session_id, force=force)
        if error:
            raise HTTPException(status_code=409, detail=error)
        return RedirectResponse(f"{settings.base_path}/teacher", status_code=303)

    @router.post("/teacher/session/close-delete")
    def teacher_close_delete_session(
        request: Request,
        csrf_token: str = Form(...),
        session_id: int = Form(...),
        force: bool = Form(False),
    ):
        verify_csrf(request, csrf_token)
        require_teacher(request)
        session = db.current_session(settings.database_path)
        if session is None:
            raise HTTPException(status_code=409, detail="当前没有场次")
        if session_id != int(session["id"]):
            raise HTTPException(status_code=409, detail="只能关闭并删除当前场次")
        if session["phase"] != "closed":
            db.set_phase(settings.database_path, session_id, "closed", None)
        error = db.delete_session(settings.database_path, session_id, force=force)
        if error:
            raise HTTPException(status_code=409, detail=error)
        return RedirectResponse(f"{settings.base_path}/teacher", status_code=303)

    @router.post("/teacher/phase")
    def teacher_phase(
        request: Request,
        csrf_token: str = Form(...),
        session_id: int = Form(...),
        phase: str = Form(...),
    ):
        verify_csrf(request, csrf_token)
        require_teacher(request)
        if phase not in PHASE_LABELS:
            raise HTTPException(status_code=400, detail="未知阶段")
        session = db.current_session(settings.database_path)
        if session is None:
            raise HTTPException(status_code=409, detail="请先创建自查场次")
        if session_id != int(session["id"]):
            raise HTTPException(status_code=409, detail="当前场次已经变化")
        bank = bank_for_session(session)
        durations = {
            "a": bank.durations["attempt_a"],
            "learn": bank.durations["learn"],
            "b": bank.durations["attempt_b"],
        }
        db.set_phase(
            settings.database_path,
            int(session["id"]),
            phase,
            durations.get(phase),
        )
        return RedirectResponse(f"{settings.base_path}/teacher", status_code=303)

    @router.get("/teacher/export.csv")
    def teacher_export(request: Request, session_id: int | None = None):
        require_teacher(request)
        if session_id is None:
            session = db.current_session(settings.database_path)
            if session is None:
                raise HTTPException(status_code=404, detail="当前没有场次")
        else:
            session = db.get_session(settings.database_path, session_id)
            if session is None:
                raise HTTPException(status_code=404, detail="场次不存在")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["gitea_login", "name", "a_count", "a_correct", "learned", "b_count", "b_correct"]
        )
        for row in db.export_rows(settings.database_path, int(session["id"])):
            writer.writerow(
                [
                    row["login"],
                    row["display_name"],
                    row["a_count"],
                    row["a_correct"],
                    row["learned"],
                    row["b_count"],
                    row["b_correct"],
                ]
            )
        return Response(
            content="\ufeff" + output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=stat-check.csv"},
        )

    if settings.testing:

        @router.get("/test-login")
        def test_login(request: Request, login: str = "student1", role: str = "student"):
            if role not in {"student", "teacher"}:
                raise HTTPException(status_code=400)
            numeric_id = 900000 + sum(ord(char) for char in login)
            user = db.upsert_user(
                settings.database_path,
                gitea_id=numeric_id,
                login=login,
                display_name=login,
                role=role,
            )
            request.session.clear()
            request.session["user_id"] = int(user["id"])
            return RedirectResponse(f"{settings.base_path}/", status_code=303)

    app.include_router(router)
    return app


app = create_app()
