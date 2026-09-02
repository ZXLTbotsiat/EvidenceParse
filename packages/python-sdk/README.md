# EvidenceParse Python SDK

A small synchronous client for self-hosted EvidenceParse deployments.

```python
from evidence_parse_sdk import EvidenceParseClient

with EvidenceParseClient("http://localhost:8000", api_key="local-key") as client:
    result = client.parse_document("invoice.pdf")
    print(result["fields"]["total"])
```

The API key is sent only through the `X-API-Key` header. Callers remain
responsible for loading secrets from their own secret manager or environment;
the SDK does not persist credentials.
