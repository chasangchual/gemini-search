import os
import uuid
import json
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Cookie, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from itsdangerous import Signer
import uvicorn

from .drive_client import create_drive_service, download_files, resolve_file_ids
from .gemini_client import GeminiClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

sessions: dict[str, dict] = {}
signer = Signer(os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"))


def get_session_id(session_cookie: Optional[str]) -> str:
    if session_cookie:
        try:
            session_id = signer.unsign(session_cookie).decode()
            if session_id in sessions:
                return session_id
        except Exception:
            pass
    return create_new_session()


def create_new_session() -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "messages": [],
        "client": None,
        "files_uploaded": False,
    }
    return session_id


def get_or_create_client(session_id: str) -> GeminiClient:
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    session = sessions[session_id]
    if session["client"] is None:
        session["client"] = GeminiClient(api_key=api_key, model_name=model)
    return session["client"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    file_ids = os.environ.get("GOOGLE_DRIVE_FILE_IDS")
    folder_ids = os.environ.get("GOOGLE_DRIVE_FOLDER_IDS")

    if credentials and (file_ids or folder_ids):
        print("Pre-loading files from Google Drive...")
        drive_service = create_drive_service(credentials)
        ids_list = resolve_file_ids(drive_service, file_ids, folder_ids)
        if ids_list:
            print(f"Downloading {len(ids_list)} file(s)...")
            file_paths = download_files(drive_service, ids_list)
            print("Files downloaded and cached.")
    yield
    for session_data in sessions.values():
        if session_data.get("client"):
            session_data["client"].cleanup()


app = FastAPI(title="Gemini Search", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Optional[str] = Cookie(None)):
    session_id = get_session_id(session)
    session_data = sessions[session_id]

    signed_session = signer.sign(session_id.encode()).decode()

    template = jinja_env.get_template("index.html")
    html = template.render(
        request=request,
        messages=session_data["messages"],
        session=signed_session,
    )
    return HTMLResponse(content=html)


@app.post("/chat")
async def chat(
    message: str = Form(...),
    session: Optional[str] = Cookie(None),
):
    session_id = get_session_id(session)
    session_data = sessions[session_id]
    client = get_or_create_client(session_id)

    async def generate():
        session_data["messages"].append({"role": "user", "content": message})
        yield f"data: {await serialize_message('user', message)}\n\n"

        try:
            response = client.send_message(message)
            full_response = ""

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield f"data: {await serialize_message('assistant', chunk.text, partial=True)}\n\n"

            session_data["messages"].append(
                {"role": "assistant", "content": full_response}
            )
            yield f"data: {await serialize_message('assistant', full_response, done=True)}\n\n"
        except Exception as e:
            yield f"data: {await serialize_message('error', str(e))}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/new")
async def new_chat(session: Optional[str] = Cookie(None)):
    old_session_id = get_session_id(session)

    if sessions[old_session_id].get("client"):
        sessions[old_session_id]["client"].cleanup()

    new_session_id = create_new_session()
    signed_session = signer.sign(new_session_id.encode()).decode()

    return {"status": "ok", "session": signed_session}


async def serialize_message(
    role: str,
    content: str,
    partial: bool = False,
    done: bool = False,
    error: bool = False,
) -> str:
    import json

    return json.dumps(
        {
            "role": role,
            "content": content,
            "partial": partial,
            "done": done,
            "error": error,
        }
    )


def main():
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", "8000"))
    uvicorn.run("gemini_search.web:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
