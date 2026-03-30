import os
import click
from dotenv import load_dotenv

from .drive_client import create_drive_service, download_files, resolve_file_ids
from .gemini_client import GeminiClient
from .chat import run_repl

load_dotenv()


@click.command()
@click.option(
    "--api-key", envvar="GEMINI_API_KEY", required=False, help="Gemini API key"
)
@click.option(
    "--credentials",
    envvar="GOOGLE_APPLICATION_CREDENTIALS",
    required=False,
    help="Path to Google service account JSON",
)
@click.option(
    "--file-ids",
    envvar="GOOGLE_DRIVE_FILE_IDS",
    required=False,
    help="Comma-separated Google Drive file IDs",
)
@click.option(
    "--folder-ids",
    envvar="GOOGLE_DRIVE_FOLDER_IDS",
    required=False,
    help="Comma-separated Google Drive folder IDs (recursively includes all files)",
)
@click.option(
    "--model",
    envvar="GEMINI_MODEL",
    default="gemini-2.0-flash",
    help="Gemini model to use",
)
def main(
    api_key: str | None,
    credentials: str | None,
    file_ids: str | None,
    folder_ids: str | None,
    model: str,
):
    api_key = os.environ.get("GEMINI_API_KEY") or api_key
    credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or credentials
    file_ids = os.environ.get("GOOGLE_DRIVE_FILE_IDS") or file_ids
    folder_ids = os.environ.get("GOOGLE_DRIVE_FOLDER_IDS") or folder_ids
    model = os.environ.get("GEMINI_MODEL") or model

    if not api_key:
        raise click.ClickException(
            "GEMINI_API_KEY is required. Set it in .env or pass --api-key"
        )

    client = GeminiClient(api_key=api_key, model_name=model)

    if credentials and (file_ids or folder_ids):
        print("Connecting to Google Drive...")
        drive_service = create_drive_service(credentials)

        ids_list = resolve_file_ids(drive_service, file_ids, folder_ids)
        if not ids_list:
            print("No files found to download.")
        else:
            print(f"Downloading {len(ids_list)} file(s) from Google Drive...")
            file_paths = download_files(drive_service, ids_list)

            print("Uploading files to Gemini...")
            client.upload_files(file_paths)
            print("Files uploaded successfully.\n")

    try:
        run_repl(client)
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()
