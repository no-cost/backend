# migrations

```bash
# in repo root:
# create
alembic revision --autogenerate -m "message"

# upgrade
alembic upgrade head

# downgrade
alembic downgrade -1
```
