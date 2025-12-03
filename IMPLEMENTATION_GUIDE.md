# MoodList Feature Implementation Guide

Quick start guide for implementing proposed features with code examples and file locations.

---

## 🚀 Getting Started with New Features

### Step 1: Create Feature Branch
```bash
git checkout -b feature/feature-name
```

### Step 2: Update Database (if needed)
```bash
# Create migration
alembic revision --autogenerate -m "Add feature_name table"

# Review migration file
vim alembic/versions/xxxxx_add_feature_name.py

# Apply migration
alembic upgrade head
```

### Step 3: Backend Implementation
```
backend/app/
├── models/          # Add DB models here
├── schemas/         # Add Pydantic schemas
├── services/        # Add business logic
├── repositories/    # Add data access layer
└── routes/          # Add API endpoints
```

### Step 4: Frontend Implementation
```
frontend/src/
├── components/      # React components
├── hooks/          # Custom hooks
├── lib/            # Utilities
└── app/            # Pages
```

---

## Feature Implementation Examples

### 1️⃣ Playlist Descriptions (HIGHEST PRIORITY)

**Backend Changes:**

```python
# backend/app/models/playlist.py - Add field
class Playlist(Base):
    __tablename__ = "playlist"
    # ... existing fields ...
    description: str = Column(String(1000), nullable=True)  # NEW
    ai_generated_description: bool = Column(Boolean, default=False)  # NEW
```

**Migration:**
```bash
alembic revision --autogenerate -m "Add description field to playlist"
```

**New Agent:**
```python
# backend/app/agents/description_agent.py
class DescriptionGeneratorAgent:
    """Generate witty descriptions for playlists."""
    
    async def generate_description(
        self,
        mood_prompt: str,
        recommendations: List[TrackRecommendation],
        mood_analysis: dict
    ) -> str:
        """Generate description using LLM."""
        prompt = f"""
        Create a witty, poetic 1-2 sentence description for a playlist based on:
        Mood: {mood_prompt}
        Audio Features: {mood_analysis}
        Sample Tracks: {[r.track_name for r in recommendations[:3]]}
        
        Description should be engaging and capture the mood's essence.
        """
        # Call LLM and return description
```

**API Endpoint:**
```python
# backend/app/playlists/routes.py
@router.post("/playlists/{session_id}/regenerate-description")
async def regenerate_description(
    session_id: str,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service),
):
    """Regenerate playlist description."""
    playlist = await playlist_service.get_playlist_by_session(session_id)
    description = await description_agent.generate_description(
        playlist.mood_prompt,
        playlist.recommendations_data,
        playlist.mood_analysis_data
    )
    await playlist_service.update_description(playlist.id, description)
    return {"description": description}
```

**Frontend Display:**
```typescript
// frontend/src/components/features/playlist/PlaylistDescription.tsx
export function PlaylistDescription({ playlist }: { playlist: Playlist }) {
  return (
    <div className="description-section">
      <p className="text-sm text-gray-600">{playlist.description}</p>
      <button
        onClick={() => regenerateDescription(playlist.id)}
        className="text-xs text-blue-500 hover:underline"
      >
        ✨ Regenerate
      </button>
    </div>
  )
}
```

**Testing Checklist:**
- [ ] Description generates on playlist completion
- [ ] Description updates when regenerated
- [ ] Empty/null descriptions handled gracefully
- [ ] Descriptions display correctly in all UI views
- [ ] Performance: LLM generation doesn't block UI

---

### 2️⃣ Favorites & Collections

**Database Schema:**
```python
# backend/app/models/playlist.py
class Playlist(Base):
    is_favorite: bool = Column(Boolean, default=False)

# backend/app/models/collection.py
class Collection(Base):
    __tablename__ = "collection"
    
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("user.id"), nullable=False)
    name: str = Column(String(255), nullable=False)
    description: str = Column(String(500), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    playlists = relationship("Playlist", secondary="collection_playlist")
```

**Repository Methods:**
```python
# backend/app/repositories/playlist_repository.py
async def toggle_favorite(self, playlist_id: int, user_id: int) -> bool:
    """Toggle favorite status."""
    query = select(Playlist).where(
        (Playlist.id == playlist_id) & (Playlist.user_id == user_id)
    )
    playlist = await self.session.scalar(query)
    if playlist:
        playlist.is_favorite = not playlist.is_favorite
        await self.session.commit()
        return playlist.is_favorite
    raise NotFoundException("Playlist", str(playlist_id))

async def get_user_collections(self, user_id: int) -> List[Collection]:
    """Get all collections for user."""
    query = select(Collection).where(Collection.user_id == user_id)
    return await self.session.scalars(query)
```

**API Endpoints:**
```python
# backend/app/playlists/routes.py
@router.post("/playlists/{playlist_id}/favorite")
async def toggle_favorite(
    playlist_id: int,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service),
):
    """Toggle playlist favorite status."""
    is_favorite = await playlist_service.toggle_favorite(
        playlist_id, current_user.id
    )
    return {"playlist_id": playlist_id, "is_favorite": is_favorite}

@router.get("/collections")
async def get_collections(
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service),
):
    """Get user's collections."""
    collections = await playlist_service.get_user_collections(current_user.id)
    return {"collections": collections}

@router.post("/collections")
async def create_collection(
    name: str,
    description: Optional[str] = None,
    current_user: User = Depends(require_auth),
    playlist_service: PlaylistService = Depends(get_playlist_service),
):
    """Create new collection."""
    collection = await playlist_service.create_collection(
        user_id=current_user.id,
        name=name,
        description=description
    )
    return {"collection": collection}
```

**Frontend Component:**
```typescript
// frontend/src/components/features/playlist/PlaylistCard.tsx
export function PlaylistCard({ playlist, onFavorite }: PlaylistCardProps) {
  const [isFavorite, setIsFavorite] = useState(playlist.is_favorite)
  
  const handleFavorite = async () => {
    await api.post(`/playlists/${playlist.id}/favorite`)
    setIsFavorite(!isFavorite)
  }
  
  return (
    <div className="playlist-card">
      <button
        onClick={handleFavorite}
        className={`favorite-btn ${isFavorite ? 'active' : ''}`}
      >
        {isFavorite ? '❤️' : '🤍'}
      </button>
      {/* Rest of card */}
    </div>
  )
}
```

---

### 3️⃣ Mood Templates

**Configuration:**
```typescript
// frontend/src/lib/moodTemplates.ts
export interface MoodTemplate {
  id: string
  name: string
  emoji: string
  description: string
  prompt: string
  tags: string[]
  audioFeatures?: {
    energy?: number
    valence?: number
    danceability?: number
  }
}

export const MOOD_TEMPLATES: MoodTemplate[] = [
  {
    id: 'workout',
    name: 'Workout',
    emoji: '💪',
    description: 'High energy tracks to pump you up',
    prompt: 'energetic workout mix with high-tempo bangers',
    tags: ['high-energy', 'motivational', 'fast'],
    audioFeatures: { energy: 0.8, valence: 0.7, danceability: 0.8 },
  },
  {
    id: 'study',
    name: 'Study Focus',
    emoji: '📚',
    description: 'Calm, focused tracks for productivity',
    prompt: 'ambient, instrumental focus music for deep work',
    tags: ['calm', 'focus', 'instrumental'],
    audioFeatures: { energy: 0.3, valence: 0.5 },
  },
  {
    id: 'chill',
    name: 'Chill Vibes',
    emoji: '😎',
    description: 'Relaxed tracks to unwind',
    prompt: 'mellow, laid-back vibe with smooth beats',
    tags: ['relaxed', 'smooth', 'chill'],
    audioFeatures: { energy: 0.4, valence: 0.6 },
  },
  // ... more templates
]
```

**Template Selector Component:**
```typescript
// frontend/src/components/features/create/MoodTemplateSelector.tsx
export function MoodTemplateSelector({ onSelect }: MoodTemplateSelectorProps) {
  return (
    <div className="template-grid">
      {MOOD_TEMPLATES.map(template => (
        <button
          key={template.id}
          onClick={() => onSelect(template)}
          className="template-button"
        >
          <span className="text-3xl">{template.emoji}</span>
          <h3>{template.name}</h3>
          <p>{template.description}</p>
        </button>
      ))}
    </div>
  )
}
```

**Integration with Mood Input:**
```typescript
// frontend/src/components/features/create/MoodInput.tsx
export function MoodInput() {
  const [selectedTemplate, setSelectedTemplate] = useState<MoodTemplate | null>(null)
  const [customMood, setCustomMood] = useState('')
  
  const moodPrompt = selectedTemplate?.prompt || customMood
  
  return (
    <div>
      <MoodTemplateSelector onSelect={setSelectedTemplate} />
      
      {selectedTemplate && (
        <div className="template-selected">
          <span>{selectedTemplate.emoji} {selectedTemplate.name} selected</span>
          <button onClick={() => setSelectedTemplate(null)}>Change</button>
        </div>
      )}
      
      <textarea
        value={customMood}
        placeholder="Or describe your mood..."
        onChange={e => setCustomMood(e.target.value)}
      />
    </div>
  )
}
```

---

### 4️⃣ Audio Preview

**Backend (Spotify URLs already available):**
```python
# backend/app/spotify/client.py - Usually already has preview_url
class SpotifyClient:
    async def search_tracks(self, query: str):
        results = await self.client.search(query, types=["track"])
        tracks = []
        for track in results["tracks"]["items"]:
            tracks.append({
                "id": track["id"],
                "name": track["name"],
                "preview_url": track.get("preview_url"),  # KEY FIELD
                # ... other fields
            })
        return tracks
```

**Frontend Component:**
```typescript
// frontend/src/components/shared/AudioPlayer.tsx
export function AudioPlayer({ trackUri, previewUrl }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  
  const handlePlay = () => {
    if (!previewUrl) return
    setIsPlaying(true)
    audioRef.current?.play()
  }
  
  const handlePause = () => {
    setIsPlaying(false)
    audioRef.current?.pause()
  }
  
  return (
    <div className="audio-player">
      <audio
        ref={audioRef}
        src={previewUrl}
        onEnded={() => setIsPlaying(false)}
      />
      
      <button onClick={isPlaying ? handlePause : handlePlay}>
        {isPlaying ? '⏸️' : '▶️'} Preview
      </button>
      
      {!previewUrl && (
        <span className="text-xs text-gray-500">Preview unavailable</span>
      )}
    </div>
  )
}
```

**Preview Modal:**
```typescript
// frontend/src/components/shared/PreviewModal.tsx
export function PreviewModal({ tracks, isOpen, onClose }: PreviewModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <h2>Preview Tracks</h2>
        <div className="tracks-list">
          {tracks.map(track => (
            <div key={track.id} className="track-item">
              <div>
                <h4>{track.name}</h4>
                <p>{track.artists}</p>
              </div>
              <AudioPlayer previewUrl={track.preview_url} />
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

---

## Development Workflow

### 1. Create Branch
```bash
git checkout -b feature/playlist-descriptions
```

### 2. Set Up Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 3. Run Development Servers
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Database (if local)
# postgres or docker
```

### 4. Test Feature
- Manual testing in browser
- Backend: `pytest tests/` (if available)
- Frontend: Check console for errors

### 5. Create PR with
- Feature description
- Test cases
- Screenshot/demo (if UI change)
- DB migration (if applicable)

---

## Common Patterns

### Adding a New Endpoint
```python
# 1. Create schema in backend/app/schemas/
class MyFeatureSchema(BaseModel):
    id: int
    name: str
    # ...

# 2. Create route in backend/app/playlists/routes.py
@router.post("/endpoint")
async def my_endpoint(
    current_user: User = Depends(require_auth),
    service: Service = Depends(get_service),
):
    result = await service.do_something()
    return {"result": result}

# 3. Call from frontend
const response = await fetch('/api/endpoint', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(data)
})
```

### Adding a Database Migration
```bash
# Create
alembic revision --autogenerate -m "Add new_field to table"

# Review the generated file in alembic/versions/

# Apply
alembic upgrade head

# Rollback (if needed)
alembic downgrade -1
```

### Creating a Service
```python
# backend/app/services/my_service.py
class MyService:
    def __init__(self, repository: MyRepository):
        self.repository = repository
    
    async def get_item(self, item_id: int, user_id: int):
        return await self.repository.get_by_id_for_user(item_id, user_id)
    
    async def create_item(self, data: CreateItemSchema, user_id: int):
        return await self.repository.create(data, user_id)
```

---

## Deployment Checklist

Before merging:
- [ ] Code follows existing style
- [ ] Database migrations created
- [ ] Tests pass locally
- [ ] No console errors/warnings
- [ ] Features documented
- [ ] PR reviewed
- [ ] Merged to main
- [ ] Deployed to staging
- [ ] Final QA testing
- [ ] Deployed to production

---

## Useful Commands

```bash
# Backend database operations
alembic upgrade head              # Apply migrations
alembic downgrade -1              # Rollback
alembic revision --autogenerate   # Create migration

# Frontend utilities
npm run dev                        # Dev server
npm run build                      # Production build
npm run type-check                 # TypeScript check
npm run lint                       # Linting

# Git workflows
git checkout -b feature/name       # Create branch
git push -u origin feature/name    # Push branch
git pull origin main               # Update from main
```

---

## Need Help?

- **Backend Questions**: Check `backend/README.md`
- **Frontend Questions**: Check `frontend/README.md`
- **Architecture**: See `docs/`
- **API Docs**: Visit `http://localhost:8000/docs`

---

Last Updated: December 2024
