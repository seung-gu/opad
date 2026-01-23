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

For detailed architecture documentation, see [ARCHITECTURE.md](./ARCHITECTURE.md).

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
   
   # Node.js
   cd src/web
   npm install
   ```

3. **Set environment variables**:
   ```bash
   export REDIS_URL=redis://localhost:6379
   export MONGO_URL=mongodb://localhost:27017/
   export OPENAI_API_KEY=your-key
   export SERPER_API_KEY=your-key
   ```

4. **Run services** (in separate terminals):
   ```bash
   # API (Terminal 1)
   PYTHONPATH=src uvicorn api.main:app --reload --port 8001
   
   # Worker (Terminal 2)
   PYTHONPATH=src uv run python -m worker.main
   
   # Web (Terminal 3)
   cd src/web
   API_BASE_URL=http://localhost:8001 npm run dev
   ```

5. **Access**: Open [http://localhost:8000](http://localhost:8000)

For detailed local setup instructions, see [SETUP.md](./SETUP.md).

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
   
   **Worker service:**
   ```
   REDIS_URL=${{ api.REDIS_URL }}
   MONGO_URL=${{ api.MONGO_URL }}
   OPENAI_API_KEY=your-key
   SERPER_API_KEY=your-key
   ```

4. **Deploy**: Railway automatically builds and deploys from your repository

For detailed Railway deployment instructions, see [SETUP.md](./SETUP.md).

## Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Detailed system architecture and design
- **[SETUP.md](./SETUP.md)**: Comprehensive setup and deployment guide
- **[DEVLOG.md](./DEVLOG.md)**: Development log and milestones
- **[REFERENCE.md](./REFERENCE.md)**: API flow diagrams and reference documentation

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
