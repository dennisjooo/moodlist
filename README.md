# MoodList

> AI-powered mood-based Spotify playlist generator that creates personalized playlists from natural language descriptions.

MoodList uses a sophisticated multi-agent AI system to analyze your mood and preferences, then generates perfectly curated Spotify playlists tailored to how you're feeling right now.

## Features

- **Natural Language Input**: Describe your mood in plain English - "feeling nostalgic and want something mellow" or "pumped up for a workout"
- **AI-Powered Analysis**: Multi-agent system that understands mood nuances and translates them into audio characteristics
- **Sophisticated Recommendations**: 4-strategy recommendation engine combining user history, artist discovery, seed-based, and similarity algorithms
- **Real-time Progress**: Live updates as your playlist is being generated
- **Spotify Integration**: Playlists are created directly on your Spotify account
- **Playlist Management**: View, edit, reorder tracks, and manage all your generated playlists
- **Custom Cover Art**: AI-generated cover images for each playlist

## Tech Stack

### Backend
- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL (Neon.tech) with SQLAlchemy ORM
- **AI/ML**: LangGraph + LangChain with OpenAI, Groq, and Cerebras LLMs
- **Authentication**: JWT with OAuth 2.0 for Spotify
- **Cache**: Redis (Upstash) for performance optimization
- **APIs**: Spotify API, RecoBeat recommendation engine

### Frontend
- **Framework**: Next.js 16 with React 19 and TypeScript
- **UI**: Tailwind CSS v4 + Radix UI components
- **State**: Zustand for auth and workflow state management
- **Real-time**: WebSocket, SSE, and polling fallback
- **Animations**: Framer Motion with lazy loading
- **Optimized**: Memory-efficient design, tree-shaking, code splitting

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL database
- Redis instance (optional but recommended)
- Spotify Developer Account
- OpenAI/Groq/Cerebras API key

### Backend Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/moodlist.git
cd moodlist/backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file in the `backend` directory:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/moodlist

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
JWT_REFRESH_EXPIRATION_DAYS=7

# Spotify OAuth
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://localhost:3000/callback

# LLM Provider (choose one or more)
OPENAI_API_KEY=your-openai-key
GROQ_API_KEY=your-groq-key
CEREBRAS_API_KEY=your-cerebras-key

# Optional: Redis Cache
REDIS_URL=redis://localhost:6379

# Optional: RecoBeat API
RECCOBEAT_API_KEY=your-reccobeat-key

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
FRONTEND_URL=http://localhost:3000
ENABLE_RATE_LIMITING=true
DAILY_PLAYLIST_CREATION_LIMIT=5
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. API documentation at `http://localhost:8000/docs`.

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd ../frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment variables**
Create a `.env.local` file in the `frontend` directory:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SPOTIFY_CLIENT_ID=your-spotify-client-id
NEXT_PUBLIC_SPOTIFY_REDIRECT_URI=http://localhost:3000/callback
```

4. **Start the development server**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Usage

1. **Sign in with Spotify**: Click "Login with Spotify" on the homepage
2. **Describe your mood**: Enter how you're feeling in natural language
3. **Watch the magic**: Real-time progress as AI agents analyze and generate your playlist
4. **Enjoy**: Your playlist is created on Spotify and ready to play
5. **Manage**: View, edit, reorder tracks, or create new playlists anytime

## Architecture

### Multi-Agent AI System

MoodList uses a sophisticated agent workflow powered by LangGraph:

1. **IntentAnalyzerAgent**: Extracts explicit mentions (artists, tracks, genres) from user input
2. **MoodAnalyzerAgent**: Converts mood description into Spotify audio features (valence, energy, tempo, etc.)
3. **SeedGathererAgent**: Selects anchor tracks from user's library or provided references
4. **RecommendationGeneratorAgent**: Generates tracks using 4 parallel strategies:
   - User Anchor: Based on user's listening history
   - Artist Discovery: Explores similar artists
   - Seed-based: Uses audio features and genres
   - Anchor: Similarity to selected seed tracks
5. **OrchestratorAgent**: Coordinates all agents and iteratively improves results (up to 3 rounds)
6. **PlaylistOrdererAgent**: Optimizes track ordering for cohesive listening experience

Each iteration evaluates audio feature cohesion and adjusts strategy weights for continuous improvement.

### Project Structure

```
moodlist/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── agents/         # AI agent workflows
│   │   ├── auth/           # Authentication & JWT
│   │   ├── clients/        # External API clients
│   │   ├── core/           # App config & database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── playlists/      # Playlist management
│   │   ├── repositories/   # Data access layer
│   │   ├── services/       # Business logic
│   │   └── spotify/        # Spotify integration
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   └── lib/          # Utils, hooks, stores
│   └── package.json
└── docs/                  # Technical documentation
```

## Deployment

### Current Production Setup
- **Backend**: Railway
- **Frontend**: Vercel
- **Database**: Neon.tech (PostgreSQL)
- **Cache**: Upstash (Redis)

### Deploy Your Own

#### Backend (Railway/Render)
1. Connect your GitHub repository
2. Set environment variables from `.env` example
3. Deploy from `backend` directory
4. Run migrations: `alembic upgrade head`

#### Frontend (Vercel)
1. Import project from GitHub
2. Set root directory to `frontend`
3. Configure environment variables
4. Deploy

## API Documentation

Once the backend is running, visit:
- **Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Rate Limits

- **Playlist Creation**: 5 playlists per day (configurable)
- **Workflow Start**: 10 requests per minute
- **Auth Endpoints**: Standard rate limiting applies

## Security

- JWT-based authentication with refresh tokens
- Encrypted Spotify credentials at rest
- Session tracking with IP and user-agent
- Rate limiting on all endpoints
- CORS protection
- Input validation with Pydantic

## Acknowledgments

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/) for music data
- [LangChain](https://www.langchain.com/) & [LangGraph](https://www.langchain.com/langgraph) for AI agent framework
- [RecoBeat](https://reccobeat.com/) for advanced music recommendations
- [Tailwind CSS](https://tailwindcss.com/) & [Radix UI](https://www.radix-ui.com/) for beautiful UI components
