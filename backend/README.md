# MoodList Backend API

A FastAPI-based backend for the MoodList application that provides JWT authentication, user management, and Spotify integration.

## Features

- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **User Management**: User registration, login, and session management
- **Database Integration**: PostgreSQL with SQLAlchemy ORM
- **Spotify Integration**: OAuth flow and API integration
- **Request Logging**: Comprehensive logging of all API requests to database
- **Middleware**: Custom middleware for logging and invocation status checking

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                   # Core application modules
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection and session management
│   │   ├── middleware.py      # Custom middleware
│   │   └── init_db.py         # Database initialization script
│   ├── models/                # Database models
│   │   ├── user.py           # User model
│   │   ├── session.py        # Session model
│   │   ├── playlist.py       # Playlist model
│   │   ├── invocation.py     # Invocation logging model
│   │   └── __init__.py
│   └── auth/                  # Authentication modules
│       ├── security.py       # JWT and password utilities
│       ├── dependencies.py   # FastAPI dependencies
│       ├── schemas.py        # Pydantic schemas
│       └── routes.py         # Authentication routes
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Setup

### 1. Environment Configuration

Copy the environment template and configure your environment:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/moodlist_db

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
JWT_REFRESH_EXPIRATION_DAYS=7

# Session Configuration
SESSION_SECRET_KEY=your-session-secret-key-change-this-in-production
SESSION_EXPIRATION_MINUTES=30

# Spotify API Configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/auth/spotify/callback

# Application Configuration
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO

# CORS Configuration
FRONTEND_URL=http://localhost:3000
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

Initialize the database tables:

```bash
python -m app.core.init_db
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication

- `POST /api/auth/login` - Login with Spotify tokens
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/verify` - Verify authentication status

### Spotify Integration

- `GET /api/spotify/profile` - Get user's Spotify profile
- `GET /api/spotify/token/refresh` - Refresh Spotify access token
- `GET /api/spotify/playlists` - Get user's playlists
- `POST /api/spotify/playlists/create` - Create a new playlist
- `POST /api/spotify/playlists/{playlist_id}/tracks` - Add tracks to playlist

### Health Check

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## Database Models

### User
- `id`: Primary key
- `spotify_id`: Spotify user ID (unique)
- `email`: User email (optional)
- `display_name`: Display name
- `access_token`: Encrypted Spotify access token
- `refresh_token`: Encrypted Spotify refresh token
- `token_expires_at`: Token expiration time
- `profile_image_url`: Profile image URL
- `is_active`: Whether user is active
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Session
- `id`: Primary key
- `user_id`: Foreign key to User
- `session_token`: Unique session token
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `expires_at`: Session expiration time
- `created_at`: Creation timestamp
- `last_activity`: Last activity timestamp

### Playlist
- `id`: Primary key
- `user_id`: Foreign key to User
- `spotify_playlist_id`: Spotify playlist ID
- `mood_prompt`: Original mood prompt
- `playlist_data`: JSON playlist metadata
- `track_count`: Number of tracks
- `duration_ms`: Total duration in milliseconds
- `status`: Playlist status (created, generating, completed, failed)
- `error_message`: Error message if failed
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Invocation
- `id`: Primary key
- `user_id`: Foreign key to User (optional)
- `playlist_id`: Foreign key to Playlist (optional)
- `endpoint`: API endpoint called
- `method`: HTTP method
- `status_code`: HTTP status code
- `request_data`: JSON request data
- `response_data`: JSON response data
- `error_message`: Error message if any
- `processing_time_ms`: Processing time in milliseconds
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `created_at`: Creation timestamp

## Security Features

- JWT tokens with configurable expiration
- Password hashing with bcrypt
- Token encryption for storage
- Session management with expiration
- Request logging for audit trails
- CORS configuration
- Input validation with Pydantic

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
isort app/
```

### Type Checking

```bash
mypy app/
```

## Production Deployment

1. Set `APP_ENV=production` in environment variables
2. Configure proper database connection
3. Set up proper CORS origins
4. Configure logging level
5. Use a proper WSGI server like Gunicorn
6. Set up SSL/TLS certificates
7. Configure proper secret keys

## License

This project is licensed under the MIT License.