# HTTP API Contract Card


## Example of an existing endpoint (read current code before using)

The template contains `WorkItemController` under `com.calpil.template.workitems.adapter.in.web`; its collection path is `/api/v1/work-items`, with create/list and status transitions. **WorkItems may be removed**; treat this as illustration only.

```bash
# Run only after the service starts and authentication requirements are understood.
# On the demonstrative template the request body contains title and description.
curl -i -X POST 'http://localhost:8080/api/v1/work-items' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Check tug readiness","description":"Illustrative input"}'

curl -i 'http://localhost:8080/api/v1/work-items?offset=0&limit=20'
```

If the service has real security enabled, use an authorized bearer token obtained through approved means and **never** paste it in repo logs. Confirm the actual local port and routes before copying.

## Contract card for new APIs

```yaml
api: <name>
exposure: public|private
basePath: /api/v1/<resource>
method: POST
security:
  audience: <registered-app>
  scope: <scope>
  resourceOwnership: <rule>
request:
  fields: []
  maxBodyBytes: <number>
response:
  success: 201
  locationHeader: true
  sample: {}
errors:
  400: invalid-request
  401: unauthenticated
  403: unauthorized-resource
  409: conflict
idempotency: <policy>
backwardCompatibility: <consumers>
```
