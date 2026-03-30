import pathlib
import time
from google import genai
from google.genai import types


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)
        self.uploaded_files: list = []
        self.chat_session = None

    def upload_file(self, file_path: pathlib.Path):
        print(f"Uploading {file_path.name}...")
        uploaded_file = self.client.files.upload(file=str(file_path))
        print(f"Uploaded: {uploaded_file.name}")

        while uploaded_file.state.name == "PROCESSING":
            print("Processing file...")
            time.sleep(2)
            uploaded_file = self.client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"File processing failed: {uploaded_file.name}")

        self.uploaded_files.append(uploaded_file)
        return uploaded_file

    def upload_files(self, file_paths: list[pathlib.Path]):
        for file_path in file_paths:
            self.upload_file(file_path)

    def start_chat(self):
        self.chat_session = self.client.chats.create(model=self.model_name)
        return self.chat_session

    def send_message(self, message: str):
        if not self.chat_session:
            self.start_chat()

        if self.uploaded_files:
            content = self.uploaded_files + [message]
            response = self.chat_session.send_message_stream(content)
        else:
            response = self.chat_session.send_message_stream(message)

        return response

    def cleanup(self):
        for uploaded_file in self.uploaded_files:
            try:
                self.client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
