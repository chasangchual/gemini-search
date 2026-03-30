import json
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

CACHE_DIR = Path(".cache/drive_files")
METADATA_FILE = CACHE_DIR / "metadata.json"


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_metadata() -> dict:
    if METADATA_FILE.exists():
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def _save_metadata(metadata: dict):
    _ensure_cache_dir()
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def get_credentials(credentials_path: str):
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    return service_account.Credentials.from_service_account_file(
        credentials_path, scopes=scopes
    )


def create_drive_service(credentials_path: str):
    credentials = get_credentials(credentials_path)
    return build("drive", "v3", credentials=credentials)


def download_file(service, file_id: str) -> Path:
    _ensure_cache_dir()
    metadata = _load_metadata()

    if file_id in metadata:
        cached_path = Path(metadata[file_id]["path"])
        if cached_path.exists():
            return cached_path

    file_metadata = service.files().get(fileId=file_id).execute()
    filename = file_metadata.get("name", f"{file_id}.bin")
    file_path = CACHE_DIR / filename

    request = service.files().get_media(fileId=file_id)
    with open(file_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    metadata[file_id] = {
        "path": str(file_path),
        "name": filename,
        "mime_type": file_metadata.get("mimeType"),
    }
    _save_metadata(metadata)

    return file_path


def list_files_in_folder(service, folder_id: str, recursive: bool = True) -> list[str]:
    file_ids = []
    page_token = None

    query = f"'{folder_id}' in parents and trashed = false"
    fields = "nextPageToken, files(id, name, mimeType)"

    while True:
        results = (
            service.files()
            .list(q=query, fields=fields, pageToken=page_token, pageSize=1000)
            .execute()
        )

        for item in results.get("files", []):
            mime_type = item.get("mimeType", "")
            if mime_type == "application/vnd.google-apps.folder":
                if recursive:
                    file_ids.extend(
                        list_files_in_folder(service, item["id"], recursive)
                    )
            else:
                file_ids.append(item["id"])

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return file_ids


def download_files(service, file_ids: list[str]) -> list[Path]:
    paths = []
    for file_id in file_ids:
        path = download_file(service, file_id.strip())
        paths.append(path)
    return paths


def resolve_file_ids(
    service, file_ids: str | None, folder_ids: str | None, recursive: bool = True
) -> list[str]:
    all_ids = []

    if file_ids:
        all_ids.extend([fid.strip() for fid in file_ids.split(",") if fid.strip()])

    if folder_ids:
        for folder_id in folder_ids.split(","):
            folder_id = folder_id.strip()
            if folder_id:
                print(f"Scanning folder {folder_id}...")
                folder_files = list_files_in_folder(service, folder_id, recursive)
                print(f"Found {len(folder_files)} file(s) in folder {folder_id}")
                all_ids.extend(folder_files)

    unique_ids = list(dict.fromkeys(all_ids))
    return unique_ids
