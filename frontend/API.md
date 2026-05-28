# EvalPlatform Backend API Documentation
**Version:** 0.1.0

The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.

## Endpoints

### POST /v1/events
**Summary:** Ingest Events

Ingest a batch of runtime telemetry events asynchronously.
Returns 202 Accepted immediately.

**Request Body:** (application/json)

**Responses:**
- **202**: Successful Response
- **422**: Validation Error

---

### GET /v1/metrics
**Summary:** List Metrics

**Responses:**
- **200**: Successful Response

---

### POST /v1/metrics
**Summary:** Save Metric

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | query | No |  |


**Request Body:** (application/json)

**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### GET /v1/metrics/{name}
**Summary:** Get Metric

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | path | Yes |  |


**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### PUT /v1/metrics/{name}
**Summary:** Save Metric

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | path | Yes |  |


**Request Body:** (application/json)

**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### GET /v1/pipelines
**Summary:** List Pipelines

**Responses:**
- **200**: Successful Response

---

### POST /v1/pipelines
**Summary:** Save Pipeline

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | query | No |  |


**Request Body:** (application/json)

**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### GET /v1/pipelines/{name}
**Summary:** Get Pipeline

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | path | Yes |  |


**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### PUT /v1/pipelines/{name}
**Summary:** Save Pipeline

**Parameters:**
| Name | In | Required | Description |
| --- | --- | --- | --- |
| name | path | Yes |  |


**Request Body:** (application/json)

**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### POST /v1/agent/chat
**Summary:** Chat With Agent

**Request Body:** (application/json)

**Responses:**
- **200**: Successful Response
- **422**: Validation Error

---

### GET /healthz
**Summary:** Healthz

**Responses:**
- **200**: Successful Response

---

