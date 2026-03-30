# Gemini Search

CLI RAG chat application using Gemini with Google Drive files.

## Setup

### 1. Install dependencies with uv

```bash
uv sync
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### 3. Google Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create a Service Account
5. Download the JSON key file
6. Share your Google Drive files/folders with the service account email

### 4. Get Gemini API Key

Get your API key from [Google AI Studio](https://aistudio.google.com/)

## Configuration

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON file |
| `GOOGLE_DRIVE_FILE_IDS` | Comma-separated Google Drive file IDs (optional) |
| `GOOGLE_DRIVE_FOLDER_IDS` | Comma-separated Google Drive folder IDs - recursively includes all files (optional) |
| `GEMINI_MODEL` | Gemini model to use (default: `gemini-2.0-flash`) |

You can use `GOOGLE_DRIVE_FILE_IDS`, `GOOGLE_DRIVE_FOLDER_IDS`, or both together.

## Usage

Run the interactive REPL:

```bash
uv run gemini-search
```

Or with command-line options:

```bash
uv run gemini-search --api-key YOUR_KEY --file-ids FILE_ID1,FILE_ID2
```

## How to Get Google Drive IDs

**File IDs:**
1. Open the file in Google Drive
2. The URL looks like: `https://drive.google.com/file/d/FILE_ID_HERE/view`
3. Copy the `FILE_ID_HERE` part

**Folder IDs:**
1. Open the folder in Google Drive
2. The URL looks like: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Copy the `FOLDER_ID_HERE` part
4. All files in the folder (and subfolders) will be included recursively

## Features

- Interactive REPL with command history
- Downloads files from Google Drive via service account
- Caches files locally to avoid re-downloading
- Uploads files to Gemini File API
- Multi-turn conversation with context retention