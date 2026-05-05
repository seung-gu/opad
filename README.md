# OPAD (One Paragraph A Day)

OPAD is an AI-powered system that **transforms** current news articles into personalized educational reading materials for language learners using [crewAI](https://crewai.com).

**How it works:**
- 🔍 **Finding** - Searches for recent news articles on a specified topic
- 📰 **Selecting** - Chooses the best article based on topic relevance, difficulty, and educational value
- ✏️ **Transforming** - Adapts and transforms the selected article to match the target language level and length

## Purpose

OPAD provides language learners with:
- **Current, relevant content**: Real news articles instead of outdated textbook materials
- **Appropriate difficulty**: Content adapted to the learner's proficiency level
- **Complete source attribution**: Original source information preserved
- **Personalized learning**: Materials tailored to specific topics, languages, and levels

## Overview

OPAD uses a **3-service architecture** (Web/API/Worker) with asynchronous job processing:

- **Web (Next.js)**: User interface for generating and viewing articles
- **API (FastAPI)**: REST API for article CRUD operations and job queue management
- **Worker (Python)**: Background job processor that runs CrewAI to generate articles

**Data Storage:**
- **MongoDB**: Article metadata and content storage
- **Redis**: Job queue and status tracking

For detailed architecture documentation, see [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Installation & Deployment

### Prerequisites

- Python >=3.10 <3.14
- Node.js >=18
- Docker (for containerized deployment)
- MongoDB and Redis (provided by Railway add-ons or local Docker)

### Local Development (Docker)

1. **Start dependencies** (MongoDB and Redis):
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

2. **Install dependencies**:
   ```bash
   # Python
   pip install uv
   uv pip install -e .

   # Node.js / monorepo
   pnpm install
   pnpm prepare
   ```

   > If you make backend API changes under `server/api`, regenerate the shared client types with:
   > ```bash
   > pnpm export:openapi
   > pnpm generate:types
   > ```

3. **Set environment variables**:
   ```bash
   export REDIS_URL=redis://localhost:6379
   export MONGO_URL=mongodb://localhost:27017/
   export OPENAI_API_KEY=your-key
   export SERPER_API_KEY=your-key

   # JWT Authentication (Required)
   # Generate a secure key: openssl rand -hex 32
   export JWT_SECRET_KEY=your-secure-random-secret-key-here

   # CORS (Optional, default: "*")
   export CORS_ORIGINS=http://localhost:8000
   ```

4. **Run services** (in separate terminals):
   ```bash
   # API (Terminal 1)
   PYTHONPATH=server uvicorn api.main:app --reload --port 8001
   
   # Worker (Terminal 2)
   PYTHONPATH=server uv run python -m worker.main
   
   # Web (Terminal 3)
   cd client/apps/web
   API_BASE_URL=http://localhost:8001 npm run dev
   ```

5. **Access**: Open [http://localhost:8000](http://localhost:8000)

For detailed local setup instructions, see [SETUP.md](./docs/SETUP.md).

### Railway Deployment

1. **Create Railway project** with 3 services:
   - `web` (Next.js) - Use `Dockerfile.web`
   - `api` (FastAPI) - Use `Dockerfile.api`
   - `worker` (Python) - Use `Dockerfile.worker`

2. **Add add-ons**:
   - MongoDB add-on (provides `MONGO_URL`)
   - Redis add-on (provides `REDIS_URL`)

3. **Configure environment variables**:
   
   **Web service:**
   ```
   API_BASE_URL=https://${{ api.RAILWAY_PUBLIC_DOMAIN }}
   ```

   **API service:**
   ```
   JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
   CORS_ORIGINS=https://${{ web.RAILWAY_PUBLIC_DOMAIN }}
   OPENAI_API_KEY=your-key
   SERPER_API_KEY=your-key
   ```

   **Worker service:**
   ```
   REDIS_URL=${{ api.REDIS_URL }}
   MONGO_URL=${{ api.MONGO_URL }}
   OPENAI_API_KEY=your-key
   SERPER_API_KEY=your-key
   ```

4. **Deploy**: Railway automatically builds and deploys from your repository

For detailed Railway deployment instructions, see [SETUP.md](./docs/SETUP.md).

## API Type Generation

This project uses **openapi-typescript** to automatically generate TypeScript types from the FastAPI OpenAPI schema. This ensures client and server types stay in sync.

### How It Works

1. **Export OpenAPI Schema**: FastAPI introspects the application and exports the OpenAPI specification:
   ```bash
   pnpm export:openapi
   ```
   Generates: `server/openapi.json`

2. **Generate TypeScript Types**: openapi-typescript converts the OpenAPI schema to TypeScript:
   ```bash
   pnpm generate:types
   ```
   Generates: `client/libs/types/api.generated.ts`

3. **Wrap Generated Types**: Wrapper types in `client/libs/types/article.ts` provide backward compatibility and handle API nullability:
   ```typescript
   export type Article = Omit<components['schemas']['ArticleResponse'], 'status'> & {
     status: ArticleStatus;
   };
   ```

### Automatic Type Regeneration

A **Husky pre-commit hook** automatically regenerates types when you modify API contracts:

```bash
# Triggered when modifying any of these files:
server/api/main.py
server/api/models.py
server/api/routes/*.py
server/api/dependencies.py
```

The hook runs:
```bash
pnpm export:openapi && pnpm generate:types
```

Then stages the generated files for commit.

### Manual Type Generation

Regenerate types at any time:
```bash
# Step 1: Export OpenAPI schema to JSON
pnpm export:openapi

# Step 2: Generate TypeScript types from the schema
pnpm generate:types

# Both steps together
pnpm export:openapi && pnpm generate:types
```

### Type Validation

Both web and mobile packages validate types during build:
```bash
pnpm --filter @opad/web exec tsc --noEmit
pnpm --filter @opad/mobile exec tsc --noEmit
```

## Documentation

- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)**: Detailed system architecture and design
- **[SETUP.md](./docs/SETUP.md)**: Comprehensive setup and deployment guide
- **[DEVLOG.md](./docs/DEVLOG.md)**: Development log and milestones
- **[REFERENCE.md](./docs/REFERENCE.md)**: API flow diagrams and reference documentation
- **[CLAUDE.md](./CLAUDE.md)**: AI agent pipeline and development guidelines
- **[CHANGELOG.md](./docs/CHANGELOG.md)**: Version history and release notes

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
