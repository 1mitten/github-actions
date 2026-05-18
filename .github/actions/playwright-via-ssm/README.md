# playwright-via-ssm

Composite GitHub Action that runs Python Playwright tests against a private
EC2-hosted application via an AWS SSM port-forwarding tunnel. Captures
configurable artefacts on failure (screenshot, video, trace) and uploads to
both S3 (with `trace.playwright.dev` viewer links) and GitHub Actions
artefacts.

## Why this exists

Tests need to reach an app that lives in a private VPC. The usual options
(self-hosted runners in the VPC, public ALB, VPN) are heavy or insecure for
post-deploy smoke testing. This action opens an SSM tunnel from the runner
through a jump instance to the target host, runs Playwright through the
tunnel, and tears the tunnel down — no inbound network changes required.

## Usage

```yaml
jobs:
  smoke:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # for OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_OIDC_ROLE_ARN }}
          aws-region: eu-west-2

      - uses: ./.github/actions/playwright-via-ssm
        with:
          app_name: widgets
          instance_id: i-0abc123def456
          remote_host: acme.internal.example.com
          app_host_header: acme.example.com
          # Optional — these have sensible defaults:
          # tenant_slug: test
          # test_tags: smoke
          # capture_on_failure: screenshot,trace,junit
          # artefact_bucket: test-xxx-ci-playwright-artifacts
```

## Inputs

### Test selection

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `app_name` | yes | — | Application name. Maps to pytest marker (`-m widgets`). |
| `test_tags` | no | `smoke` | Additional marker expression, ANDed with `app_name`. |
| `tests_dir` | no | `tests/playwright` | Working directory for pytest. |

### Target

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `tenant_slug` | no | `test` | Identifier for artefact paths and logging. |
| `instance_id` | yes | — | EC2 instance ID to tunnel through. |
| `remote_host` | yes | — | Hostname on the remote side of the tunnel. |
| `remote_port` | no | `443` | Port on the remote host. |
| `local_port` | no | `8443` | Local port to bind on the runner. |
| `app_host_header` | no | `<remote_host>` | Host header for host-based routing. |

### Environment

| Input | Required | Default |
|-------|----------|---------|
| `python_version` | no | `3.12` |
| `aws_region` | no | `eu-west-2` |

### Failure capture

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `capture_on_failure` | no | `screenshot,trace,junit` | Comma-separated list. Valid: `screenshot`, `video`, `trace`, `junit`, `html`. Shortcuts: `all`, `none`. |
| `artefact_bucket` | no | `test-xxx-ci-playwright-artifacts` | S3 bucket. Empty string disables S3 upload. |
| `upload_to_github` | no | `true` | Upload as GitHub Actions artefact too. |
| `artefact_retention_days` | no | `7` | Retention for GH artefacts. |

### Tunnel behaviour

| Input | Required | Default |
|-------|----------|---------|
| `tunnel_wait_seconds` | no | `30` |
| `skip_tunnel_healthcheck` | no | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `test_outcome` | `success` or `failure`. |
| `s3_prefix` | S3 prefix where artefacts were uploaded (empty if none). |
| `trace_viewer_urls` | Newline-separated `trace.playwright.dev` URLs. |

## AWS requirements

### IAM role (GitHub OIDC)

The role assumed via OIDC needs:

```hcl
data "aws_iam_policy_document" "playwright_ci" {
  statement {
    actions = [
      "ssm:StartSession",
      "ssm:TerminateSession",
      "ssm:ResumeSession",
    ]
    resources = [
      "arn:aws:ec2:*:*:instance/i-*",
      "arn:aws:ssm:*::document/AWS-StartPortForwardingSessionToRemoteHost",
    ]
  }

  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",  # required for presign
    ]
    resources = ["arn:aws:s3:::test-xxx-ci-playwright-artifacts/*"]
  }
}
```

Tighten the instance ARN list to specific tenant instances if you can.

### Instance requirements

- SSM Agent installed (>= 3.0 for `ToRemoteHost`)
- IAM instance profile with `AmazonSSMManagedInstanceCore`
- Outbound HTTPS to SSM endpoints (NAT gateway or VPC endpoint)
- Security group on `remote_host` allowing connections from the instance

### S3 bucket configuration

Block all public access. For trace viewer support, add CORS:

```json
[
  {
    "AllowedOrigins": ["https://trace.playwright.dev"],
    "AllowedMethods": ["GET"],
    "AllowedHeaders": ["*"]
  }
]
```

Recommended lifecycle: expire objects after 30 days (presigned URLs cap at 7
days anyway).

## How `capture_on_failure` works

The value drives which pytest flags are added when tests fail:

| Token | Pytest flag |
|-------|-------------|
| `screenshot` | `--screenshot=only-on-failure` |
| `video` | `--video=retain-on-failure` |
| `trace` | `--tracing=retain-on-failure` |
| `junit` | `--junit-xml=test-results/junit.xml` |
| `html` | `--html=test-results/report.html` (needs `pytest-html`) |

Examples:

```yaml
capture_on_failure: 'trace'                       # just the trace
capture_on_failure: 'screenshot,video,trace'      # everything except reports
capture_on_failure: 'all'                         # everything
capture_on_failure: 'none'                        # no artefacts, fail fast
```

## Test layout expectations

Your tests directory (`tests_dir`, default `tests/playwright`) must contain:

- `requirements.txt` with `playwright`, `pytest`, `pytest-playwright`
- `pytest.ini` declaring the markers used (one per app, plus `smoke`, etc.)
- `conftest.py` that reads `BASE_URL` and `APP_HOST_HEADER` from env

See the example test harness in this repo at `tests/playwright/`.

## Limitations

- Tunnel is per-job; matrix parallelism within a single runner would clash on
  `local_port` (default 8443). Use one matrix entry per runner, or parameterise.
- OIDC short-lived credentials clip the effective presigned-URL lifetime to
  the session duration (typically 1 hour), even with `--expires-in 604800`.
- Ubuntu runners only — the Session Manager plugin install step uses `.deb`.
