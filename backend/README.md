# Render Backend Wrapper

This directory is the self-contained Render backend service.

Use these Render commands with this directory:

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:$PORT app:app
```

The React frontend source lives in `code/`.
