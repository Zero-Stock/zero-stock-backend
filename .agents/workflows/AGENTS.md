---
description: Standardized guidelines for writing backend API documentation
---

# API Documentation Guidelines (Agent/MCP Guidelines)

## Project summary

- This system is based on Python / Django REST Framework.
- Client-server interactions follow a strict, unified data envelope format globally.
- Both successful and error responses for all endpoints are wrapped in a standard "Envelope":
  `{"message": "...", "error": null | {type, details}, "results": ...}`

## Code style and conventions

All newly generated API documentation must strictly follow the typography and format of `docs/dishes_api.md` and be created as `<feature>_api.md` inside the `docs/` directory. The following sections must be included:

### 1. Title & Overview
- Must start with an H1 heading, for example: `# <Feature> API Documentation`
- Followed by `## Overview`, explaining the core functionality of the module in 1-2 sentences.
- You must use exactly this standard blockquote to declare the global response format:
  `> **Response Envelope**: All endpoints return {"message": "...", "error": null|{type, details}, "results": ...}.`

### 2. Endpoint Details (Numbered H2 Headings)
For each endpoint, use an ordered name as the H2 heading, for example: `## 1. Unified Search ⭐`, `## 2. Create/Update Dish`.
Under each endpoint, include the following standard structure sequentially:
- **HTTP Method and Path**: Use bold text, for example: `**POST** /api/<feature>/search/`
- **### Input Data**: Declare the request parameters using a Markdown table. The header must be: `| Parameter | Type | Required | Description |`
- **### Output Data**: Declare the specific fields inside `results` using a Markdown table. The header must be: `| Field | Type | Description |`. When encountering nested arrays or objects, you are strictly required to use "dot notation" (for example: `results.results[].name`).
- **### Sample**: Provide a clear request example and response example (JSON format). **Crucial note**: The response example **MUST INCLUDE** the `message`, `error`, and `results` outer envelope.

### 3. Special API Conventions
- **Search endpoints**: If it is a unified query endpoint, you must include pagination (`page`, `page_size`) and sorting (`ordering`) fields in the Input Data, and explain pagination metadata like `total` in the Output Data.
- **Batch Processing / Creation**: Clearly indicate if the payload expects an array of objects.
- **RESTful Design**: Strictly label methods as `GET` / `POST` / `PUT` / `PATCH` / `DELETE` along with path parameters like `{id}`.

### 4. Required Ending (Error Type Reference)
MANDATORY: At the very end of EVERY API documentation file, you **MUST append verbatim** the global error code reference block:

```markdown
---

## Error Type Reference

All error responses use the structure `{"type": "...", "details": ...}`:

| HTTP Status | error.type | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Field validation failures |
| 401 | `AUTHENTICATION_ERROR` | Not authenticated |
| 403 | `PERMISSION_DENIED` | Forbidden |
| 404 | `NOT_FOUND` | Resource not found |
| 5xx | `SERVER_ERROR` | Internal server error |
```

## Additional context

- Never guess unimplemented fields. Always write documentation based strictly on the actual fields in the Views and Serializers.
- Casual JSON response examples missing the outer Envelope shell should never appear in the documentation.
- Primarily use English for descriptions; if the original system logic heavily relies on Chinese concepts, you may provide bilingual explanations in the Description column.
