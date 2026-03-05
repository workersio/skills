# Axiom Configuration

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AXLE_API_KEY` | no* | -- | API authentication key |
| `AXLE_API_URL` | no | `https://axle.axiommath.ai` | Server endpoint |
| `AXLE_TIMEOUT_SECONDS` | no | `1800` (30 min) | Base timeout for retry window when service is temporarily unavailable |
| `AXLE_MAX_CONCURRENCY` | no | `20` | Maximum concurrent requests |

*The API works without a key but is rate-limited to 1 concurrent request. Obtain keys at [axle.axiommath.ai/app/console](https://axle.axiommath.ai/app/console).

## Lean Environments

Every API call requires an `environment` parameter specifying the Lean version.

### Discover Available Environments

```bash
# HTTP
curl -s https://axle.axiommath.ai/v1/environments | jq

# CLI
axle environments

# Python
environments = await client.environments()
```

### Common Environments

| Environment | Description |
|---|---|
| `lean-4.28.0` | **Recommended** -- latest with full Mathlib support |
| `lean-4.27.0` | Previous stable release |
| `lean-4.21.0` | Older stable release |
| Custom (e.g., `pnt-4.26.0`) | Project-specific environments |

Choose the environment matching your project's `lean-toolchain` file. If unsure, use `lean-4.28.0`.

## Authentication Methods

### HTTP API

Pass the API key in the `Authorization` header:

```bash
curl -X POST https://axle.axiommath.ai/api/v1/check \
  -H "Authorization: Bearer $AXLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "environment": "lean-4.28.0"}'
```

### CLI

The CLI reads `AXLE_API_KEY` from the environment automatically:

```bash
export AXLE_API_KEY="your-key"
axle check file.lean --environment lean-4.28.0
```

### Python Client

```python
from axle import AxleClient

# Reads AXLE_API_KEY from environment
client = AxleClient()

# Or with explicit key and settings
client = AxleClient(
    api_key="your-api-key",
    url="https://axle.axiommath.ai",
    base_timeout_seconds=1800,
    max_concurrency=20
)

result = await client.check(content="...", environment="lean-4.28.0")
```
