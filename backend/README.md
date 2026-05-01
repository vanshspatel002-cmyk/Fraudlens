# Render Backend Wrapper

This directory exists for Render services whose Root Directory is set to `backend`.
The real Flask backend source lives in `code/backend`.

Use these Render commands with this directory:

```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:$PORT app:app
```

If you prefer not to use this wrapper, set Render Root Directory to `code/backend`
and use the same commands there.
