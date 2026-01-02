# no-cost backend

Repository with the backend portion of [no-cost's source code](https://github.com/no-cost/backend).

## Local development

NB running the API backend locally is used only for testing the API routes/definitions.
Full tenant lifecycle should be tested by deploying to a development/separate server instead.

```bash
# .venv
python -m venv .venv
source .venv/bin/activate

# dependencies
pip install -r requirements-dev.txt
pip install -r requirements.txt

# modify env as needed
cp .envrc.template .envrc

# prepare db and run dev server
alembic upgrade head
fastapi dev
```

## Production deployment

See the [no-cost/deploy](https://github.com/no-cost/deploy) repository.
