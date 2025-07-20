# FreeFlarum Backend

Repository with the backend portion of [FreeFlarum's source code](https://github.com/FreeFlarum/freeflarum).

## Local Development

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

## Deployment

Go to the [FreeFlarum/deploy](https://github.com/FreeFlarum/deploy) repository and follow the instructions there.
