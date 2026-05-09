# 🔄 API Types Synchronization

This directory contains the **tools and generated artifacts** for the automated pipeline that synchronizes backend (FastAPI) data models into frontend (TypeScript) types.

By treating the backend as the Single Source of Truth (SSoT), we ensure the API contract between the frontend and the backend is always strictly aligned.

## 📂 File Structure & Purpose

Every file in this folder exists for a single purpose: **"Automated Frontend Type Generation"**.

* `sync_from_backend.py`: A Python script that loads the backend FastAPI app to extract the OpenAPI specification.
* `openapi.json` *(Generated)*: The intermediate artifact containing the extracted OpenAPI 3.0 spec data.
* `api.generated.ts` *(Generated)*: The final TypeScript type definition file automatically generated from the JSON spec.

> **💡 Why is a Python script in the `client/` directory?**
> `sync_from_backend.py` is entirely independent of the backend server's domain logic (business logic, API routing, etc.). It is simply a "tool" for syncing frontend types. From a Clean Architecture perspective, we placed it under the client package to maintain the purity of the backend container (`server/`) and to achieve high cohesion by grouping type-generation tools and their resulting artifacts together.

## ⚙️ Type Generation Pipeline

Type synchronization is automated through the following pipeline:

1. **BE Pydantic (SSoT):** Backend developers modify Pydantic/FastAPI models in `server/api/models.py`, etc.
2. **OpenAPI Spec Extraction:** `sync_from_backend.py` is executed, parses the Pydantic models, and overwrites `openapi.json`.
3. **TS Types Generation:** The `openapi-typescript` library reads `openapi.json` and converts it into `api.generated.ts`.
4. **FE Type Wrapping:** Instead of using the raw generated types directly throughout the codebase, frontend developers safely wrap them using the `Omit` utility and intersection types (`&`) in domain files (e.g., `client/libs/types/article.ts`) to adapt them strictly for the frontend environment.

## 🚀 How is it executed? (Automation)

You do not need to run this pipeline manually. 
It is automatically triggered by the **Husky Pre-commit Hook** configured at the project root whenever changes are detected in the backend API contract files (`server/api/**/*.py`). The generated files are then automatically staged with your commit.

If you need to run the pipeline manually, use the following npm scripts:
```bash
# 1. Extract the OpenAPI JSON spec from the backend
pnpm export:openapi

# 2. Generate TypeScript types based on the JSON spec
pnpm generate:types