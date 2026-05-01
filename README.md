# Memoria Medical Hub

AI-powered medical hub built with Flask + Ollama.

## Features

- User login/logout with per-user records
- Medical profile storage (name, age, allergies, conditions, medications, notes)
- Symptom tracker with severity history
- AI health chat with last-10-message memory
- PDF/DOCX upload and AI medical document analysis
- Allergy safety warning when medicine suggestions conflict with profile allergies
- Medication tracker integrated with AI context
- Health timeline combining symptoms, documents, and chat summaries
- Smart alerts for repeated high-severity symptoms
- Quick action APIs for fever and cough

## Install

```bash
pip install -r requirements.txt
pip install flask flask-login flask-cors PyPDF2 python-docx
```

## Run Ollama

```bash
ollama run llama3
```

## Run App

```bash
python app.py
```

Default login:

- username: memoria
- password: memoria

You can override these with `DEFAULT_USER_USERNAME` and `DEFAULT_USER_PASSWORD`.

## API Endpoints

- POST /login
- POST /logout
- GET /profile
- POST /profile/update
- POST /medications
- GET /medications
- POST /symptoms/add
- GET /symptoms/history
- POST /chat
- POST /upload
- GET /timeline
- GET /alerts
- GET /quick/fever
- GET /quick/cough
- GET /status

## Project Structure

```
app.py
routes/
    api_routes.py
services/
    ai_service.py
    doc_reader.py
    memory.py
data/
    users.json
    medical_records.json
tests/
    test_app.py
```

## Tests

```bash
python -m pytest -q
```
