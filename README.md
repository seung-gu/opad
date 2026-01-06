# OPAD (One Paragraph A Day)

OPAD is an AI-powered system that automatically creates educational reading materials from news articles for language learners. Using [crewAI](https://crewai.com), it finds relevant news articles, selects the most appropriate one, and adapts it to match the learner's proficiency level.

## Project Overview

OPAD transforms current news articles into personalized reading materials by:
1. **Finding** recent news articles on a specified topic
2. **Selecting** the best article based on topic relevance, difficulty, and educational value
3. **Adapting** the selected article to match the target language level and length

## Purpose

The goal of OPAD is to provide language learners with:
- **Current, relevant content**: Real news articles instead of outdated textbook materials
- **Appropriate difficulty**: Content adapted to the learner's proficiency level
- **Complete source attribution**: Original source information preserved for reference
- **Personalized learning**: Materials tailored to specific topics, languages, and levels

This enables learners to practice reading with engaging, up-to-date content while maintaining appropriate difficulty levels for effective language acquisition.

## Installation

### Prerequisites
- Python >=3.10 <3.14
- Node.js >= 18
- Docker (for deployment)

### Local Development

1. Install Python dependencies:
```bash
pip install uv
crewai install
```

2. Install Node.js dependencies:
```bash
cd web
npm install
```

3. Set up environment variables:
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key

# For R2 storage (optional for local development)
R2_ACCOUNT_ID=your_r2_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=your_r2_bucket_name
```

### Running Locally

1. Run the Python script to generate reading materials:
```bash
python src/opad/main.py
```

2. Start the Next.js development server:
```bash
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the web interface.

## Deployment (Railway + R2)

### 1. Set up Cloudflare R2
- Create an R2 bucket in Cloudflare dashboard
- Generate API credentials (Account ID, Access Key ID, Secret Access Key)

### 2. Deploy to Railway
- Push your code to GitHub
- Create a new project in Railway from your GitHub repository
- Set the following environment variables in Railway:
  - `OPENAI_API_KEY`
  - `SERPER_API_KEY`
  - `R2_ACCOUNT_ID`
  - `R2_ACCESS_KEY_ID`
  - `R2_SECRET_ACCESS_KEY`
  - `R2_BUCKET_NAME`
- Railway will automatically build and deploy using the Dockerfile

### 3. Generate articles via web interface
- Visit your deployed Railway URL
- Click "Generate New Article"
- Fill in the form (language, level, length, topic)
- The article will be generated in the background and automatically uploaded to R2
- The page will automatically refresh when the article is ready

## Customizing

- Modify `src/opad/config/agents.yaml` to define your agents
- Modify `src/opad/config/tasks.yaml` to define your tasks
- Modify `src/opad/crew.py` to add your own logic, tools and specific args
- Modify `src/opad/main.py` to add custom inputs for your agents and tasks

## Architecture

### Backend (Python + CrewAI)
- **Agents**: Three specialized AI agents work together:
  - `paragraph_finder`: Searches for news articles using SerperDev
  - `article_picker`: Selects the best article based on criteria
  - `paragraph_writer`: Adapts the article for language learners and extracts vocabulary
- **Storage**: Generated articles are uploaded to Cloudflare R2 for persistence

### Frontend (Next.js)
- **Web Interface**: React-based UI for viewing and generating articles
- **API Routes**:
  - `/api/article`: Fetches the latest article from R2
  - `/api/generate`: Triggers Python script to generate new articles
- **Real-time Updates**: Auto-polling to detect when new articles are ready

### Infrastructure
- **Docker**: Multi-stage build for optimized image size
- **Railway**: PaaS deployment with automatic builds
- **Cloudflare R2**: S3-compatible object storage for markdown files

## Changelog

### Version 0.2.0 (2026-01-06)
- **Railway Deployment**: Added Docker-based deployment on Railway
- **R2 Storage Integration**: Integrated Cloudflare R2 for markdown file storage
  - Upload generated articles directly to R2
  - Fetch articles from R2 in web viewer
  - No more Git-based file updates
- **Dynamic API Routes**: Configured Next.js API routes with `force-dynamic` for runtime environment variable access
- **Background Processing**: Python CrewAI script runs in background via API trigger
- **Logging Improvements**: Replaced print statements with Python logging module
- **Docker Optimization**: Multi-stage Docker build for reduced image size
- **Web UI Enhancements**: 
  - Added input form for generating new articles
  - Automatic polling for article updates
  - Refresh button for manual reload

### Version 0.1.0
- Improved JSON output format validation
- Added source URL and author verification
- Enhanced level-based vocabulary filtering
- Improved markdown section structure
- Added Next.js web viewer for reading materials
- Implemented interactive vocabulary click feature

## Support

For support, questions, or feedback regarding the Opad Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
