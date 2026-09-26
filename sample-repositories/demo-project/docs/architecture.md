# Architecture

## Overview

`demo-project` is a minimal REST API for managing users.
It is a single-process Node.js application written in TypeScript.

---

## System Architecture

```text
HTTP Client (browser / curl / API client)
            │
            ▼
   Express HTTP Server  (src/main.ts)
            │
            ▼
    UserService layer   (src/services/userService.ts)
            │
            ▼
     In-memory store    (Map<id, User>)
```

---

## Components

| Component              | File                              | Responsibility                          |
|------------------------|-----------------------------------|-----------------------------------------|
| HTTP server            | `src/main.ts`                     | Route definitions, request validation   |
| User service           | `src/services/userService.ts`     | CRUD logic, in-memory persistence       |
| API client             | `src/api.ts`                      | Typed client for consuming the API      |

---

## Data Model

```typescript
interface User {
  id: string        // UUID v4
  name: string
  email: string
  createdAt: string // ISO 8601
}
```

---

## Entry Points

- **`src/main.ts`** — starts the Express server

---

## Testing

Tests live in `tests/` and use Jest with ts-jest for TypeScript support.

```bash
npm test
```
