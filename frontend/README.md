# QueueStorm Investigator Frontend

Streamlit UI for the FastAPI support copilot.

## Run

Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Start the frontend:

```bash
streamlit run frontend/app.py
```

Optional backend URL override:

```bash
set QUEUESTORM_API_URL=http://127.0.0.1:8000
streamlit run frontend/app.py
```

## Structure

```text
frontend/
  app.py        Streamlit analyst UI
  README.md    Frontend run notes
```

The UI sends requests to `POST /analyze-ticket` using the same JSON schema defined by the backend models.
