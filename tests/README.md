# Tests

## Unit tests

Unit tests are ran automatically on every commit, to ensure the code is working as expected. They require the dev dependencies to be installed. See [`./.github/workflows/test.yml`](./.github/workflows/test.yml).

Unit tests do not require full dev server setup (database, PHP-FPM, etc.), they only test basic operations and API routes.

### Running unit tests manually

In repo root: install dependencies and dev dependencies:

```bash
pip install -r requirements-dev.txt
pip install -r requirements.txt
```

Then, run the tests:

```bash
pytest
```

## Integration tests

Integration tests are ran once per deployment **on the dev server** (they are initiated via tasks in the [no-cost/deploy](https://github.com/no-cost/deploy) repository). They ensure that the API is working as expected. There is no need for `requirements-dev.txt` to be installed, because they are also part of prod deployment. This also means that they should be ran only after all the previous tasks in the deployment pipeline have been completed successfully (basically, they are from the perspective of the user).

Integration tests will:

1. Assume that the server is already set up (all services are running, database is ready, etc.);
2. Send API requests to the FastAPI instance to create each service;
3. Do something with the provisioned instances (clear cache in the API, download data, etc.);
4. Remove the provisioned instances by deleting the account through the API;
5. Report some basic stats (such as time it took to provision each service, etc.);

Integration tests are considered successful if all the steps outlined above have been completed successfully;

### Running integration tests manually

Run with this command on the deployed server (not locally):

```bash
python -m tests.integration
```
