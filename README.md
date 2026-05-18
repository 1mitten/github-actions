# Playwright via SSM — drop-in package

A complete Playwright + GitHub Actions setup for running smoke / regression
tests against private EC2-hosted applications, tunnelled through AWS SSM.

## What's in here

```
.github/
├── actions/
│   └── playwright-via-ssm/
│       ├── action.yml          # The composite action
│       └── README.md           # Action-level docs (inputs, outputs, AWS setup)
└── workflows/
    ├── smoke-tests.yml         # Reusable workflow (workflow_call)
    └── smoke-tests-manual.yml  # Manual trigger (workflow_dispatch)

tests/
└── playwright/
    ├── requirements.txt        # playwright, pytest, pytest-playwright
    ├── pytest.ini              # Marker declarations
    ├── conftest.py             # Host header + base URL fixtures
    └── tests/
        ├── test_widgets.py     # Example app test
        └── test_orders.py      # Example app test
```

## Quick start

1. **Copy the files into your repo**, preserving the paths above.

2. **Set up the AWS OIDC role** with permissions for `ssm:StartSession` against
   your tenant instances and `s3:PutObject` / `s3:GetObject` against the
   artefacts bucket. See `.github/actions/playwright-via-ssm/README.md` for
   the policy.

3. **Create the artefacts bucket** (default name `test-xxx-ci-playwright-artifacts`).
   Block all public access. Add CORS for `https://trace.playwright.dev` if you
   want trace viewer links to work.

4. **Store the OIDC role ARN** as a repo or org secret named `AWS_OIDC_ROLE_ARN`.

5. **Trigger manually** via the Actions tab → "Smoke tests (manual)" → "Run
   workflow", supplying an instance ID and remote host.

6. **Wire into your deploy pipeline** by calling the reusable workflow:

   ```yaml
   smoke:
     needs: deploy
     uses: ./.github/workflows/smoke-tests.yml
     with:
       tenant_slug: acme
       instance_id: i-0abc123def456
       remote_host: acme.internal.example.com
       app_host_header: acme.example.com
       apps: '["widgets","orders"]'
     secrets:
       AWS_OIDC_ROLE_ARN: ${{ secrets.AWS_OIDC_ROLE_ARN }}
   ```

## Customising for your tenants

The example tests assume a `.NET MVC` app with standard routes (`/Widgets`,
`/Orders`). Replace `tests/playwright/tests/*.py` with tests that match your
actual app surface. Add markers in `pytest.ini` for any new apps, e.g.:

```ini
[pytest]
markers =
    smoke: ...
    widgets: ...
    your_new_app: tests for YourNewApp
```

Then call the action with `app_name: your_new_app` and Playwright will run
tests marked with that name.

## Local development

Run tests locally against any reachable environment (no tunnel needed):

```bash
cd tests/playwright
pip install -r requirements.txt
playwright install chromium
BASE_URL=https://staging.example.com APP_HOST_HEADER=staging.example.com \
  pytest -m "widgets and smoke"
```

When `BASE_URL` and `APP_HOST_HEADER` match, the conftest fixture acts as a
no-op — same tests, same code, just no tunnel.

## Verifying the setup

Once everything's in place, the smoke test for the action itself:

1. Push to a feature branch
2. Actions tab → "Smoke tests (manual)" → "Run workflow"
3. Provide a known-good tenant's `instance_id` and `remote_host`
4. Choose `app_name: widgets`, `capture_on_failure: all`
5. Watch the run — first time through, expect to fix 1-2 things (IAM perms,
   security groups). After that, every subsequent run is the real deal.

See `.github/actions/playwright-via-ssm/README.md` for the full input
reference, AWS configuration, and troubleshooting.
