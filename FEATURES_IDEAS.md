# MoodList Feature Ideas & Roadmap

> A comprehensive collection of potential features to enhance MoodList with prioritization, effort estimates, and implementation notes.

## 📋 Currently Implemented Features

✅ **AI-Powered Mood Analysis** - Multi-agent system analyzing natural language mood descriptions  
✅ **Playlist Generation** - 4-strategy recommendation engine with iterative improvement  
✅ **Spotify Integration** - OAuth 2.0 with PKCE, direct playlist creation  
✅ **Playlist Editing** - Reorder, remove, add tracks with live sync  
✅ **User Authentication** - JWT with refresh tokens, session tracking  
✅ **Dashboard Analytics** - User stats, recent activity, mood distribution  
✅ **Real-time Progress** - SSE/WebSocket updates during generation  
✅ **Rate Limiting** - Daily quota system with per-user limits  
✅ **AI-Generated Visuals** - Custom cover art & color schemes per playlist  

---

## 🎯 Tier 1: Quick Wins (1-3 hours each)

### 1. 🎙️ AI Playlist Descriptions
**Value**: Medium | **Effort**: Low | **Priority**: ⭐⭐⭐⭐

Generate witty, poetic, or descriptive text for each playlist using existing LLM infrastructure.

**Changes Required:**
- Backend: New LLM prompt in agents system to generate descriptions
- Database: Add `description` field to Playlist model
- Frontend: Display descriptions on playlist cards and detail views
- No schema changes needed beyond the new field

**Implementation Path:**
1. Add description to playlist schema
2. Create description generation agent
3. Trigger on playlist completion
4. Display in UI

**Files to Modify:**
- `backend/app/models/playlist.py` - Add description field
- `backend/app/agents/` - Create descriptor agent
- `frontend/src/components/features/playlist/` - Display description

---

### 2. ❤️ Favorites & Collections
**Value**: Medium | **Effort**: Low | **Priority**: ⭐⭐⭐⭐

Allow users to star/favorite playlists and organize them into custom collections/folders.

**Changes Required:**
- Backend: Add `is_favorite` flag to Playlist, create Collection model
- Frontend: Toggle buttons, filter UI, collection manager
- Simple DB relationships

**Schema Changes:**
```sql
ALTER TABLE playlist ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE;

CREATE TABLE collection (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE collection_playlist (
    collection_id INTEGER,
    playlist_id INTEGER,
    position INTEGER,
    PRIMARY KEY (collection_id, playlist_id),
    FOREIGN KEY (collection_id) REFERENCES collection(id),
    FOREIGN KEY (playlist_id) REFERENCES playlist(id)
);
```

**Files to Modify:**
- `backend/app/models/playlist.py` - Add is_favorite field
- `backend/app/models/` - Create collection.py
- `backend/app/playlists/routes.py` - Add favorite/collection endpoints
- `frontend/src/components/features/playlist/` - Add favorite button
- `frontend/src/app/playlists/page.tsx` - Add collection filtering

---

### 3. 🎯 Mood Templates & Presets
**Value**: High | **Effort**: Low | **Priority**: ⭐⭐⭐⭐⭐

Provide quick-start mood templates for common scenarios (Workout, Study, Date Night, etc.).

**Changes Required:**
- Minimal backend - just template data
- Frontend: Quick-select mood buttons with descriptions
- Optional: Community template voting

**Implementation Path:**
1. Define template structure
2. Create frontend components
3. Store in frontend config or backend
4. Pre-fill mood input with template

**Template Structure:**
```typescript
interface MoodTemplate {
  id: string;
  name: string;
  description: string;
  emoji: string;
  prompt: string;
  audioFeatures: {
    energy?: number;
    valence?: number;
    tempo?: number;
  };
  tags: string[];
  popularity?: number; // for trending
}
```

**Files to Create:**
- `frontend/src/lib/moodTemplates.ts` - Template definitions
- `frontend/src/components/features/create/MoodTemplateSelector.tsx` - UI component

---

### 4. 🎚️ Advanced Mood Sliders
**Value**: Medium | **Effort**: Low | **Priority**: ⭐⭐⭐

Fine-grained controls for mood using sliders instead of just text input.

**Sliders to Implement:**
- Energy (0-100)
- Positivity/Valence (0-100)
- Tempo (60-200 BPM)
- Acousticness (0-100)
- Danceability (0-100)
- Instrumentalness (0-100)

**Backend Impact:**
- New endpoint to accept structured mood parameters
- Convert sliders to audio features or natural language

**Files to Modify:**
- `frontend/src/components/features/create/MoodInput.tsx` - Add slider UI
- `backend/app/agents/` - Add handler for structured mood input

---

### 5. 🎨 Playlist Theme Customization
**Value**: Medium | **Effort**: Low | **Priority**: ⭐⭐⭐

Let users customize playlist appearance (colors, name styling, emojis, description formatting).

**Changes Required:**
- Database: Add `theme_settings` JSON field to Playlist
- Frontend: Theme editor UI with color picker
- Display: Apply custom theme in playlist detail/card

**Theme Schema:**
```json
{
  "primaryColor": "#FF6B6B",
  "secondaryColor": "#4ECDC4",
  "emoji": "🎵",
  "layout": "compact" | "detailed",
  "fontStyle": "bold" | "italic" | "normal"
}
```

---

## ⭐ Tier 2: Medium Impact (3-6 hours each)

### 6. 📊 Playlist Analytics & Insights
**Value**: High | **Effort**: Medium | **Priority**: ⭐⭐⭐⭐⭐

Deep analytics showing mood trends, favorite genres/artists, audio feature distribution over time.

**New Endpoints Needed:**
```
GET /analytics/mood-trends - Mood over time
GET /analytics/genre-distribution - Top genres
GET /analytics/artist-insights - Top artists
GET /analytics/audio-features - Feature trends
GET /analytics/creation-patterns - When/how often creating
```

**Frontend Components:**
- Line charts for mood trends
- Pie charts for genre distribution
- Heatmaps for creation patterns
- Word clouds for common moods

**Libraries:**
- Recharts or Chart.js
- D3.js for advanced visualizations

**Files to Create/Modify:**
- `backend/app/playlists/analytics.py` - Analytics queries
- `backend/app/playlists/routes.py` - Analytics endpoints
- `frontend/src/components/features/analytics/` - Analytics dashboards
- `frontend/src/app/analytics/page.tsx` - Analytics page

---

### 7. 🔊 Audio Preview & In-App Player
**Value**: High | **Effort**: Medium | **Priority**: ⭐⭐⭐⭐⭐

Preview tracks before adding, in-app playback without leaving MoodList.

**Changes Required:**
- Backend: Expose Spotify preview URLs (already available in API response)
- Frontend: Audio player component, preview modal

**Implementation Options:**
1. **HTML5 Audio** - Simple, lightweight
2. **Spotify Web Playback SDK** - Full playback, requires premium
3. **Hybrid** - Preview with HTML5, full playback with Spotify SDK

**Files to Create:**
- `frontend/src/components/shared/AudioPlayer.tsx` - Reusable player
- `frontend/src/components/shared/PreviewModal.tsx` - Preview UI
- `frontend/src/hooks/useAudioPreview.ts` - Player state management

---

### 8. 🌍 Social Sharing & Discovery
**Value**: High | **Effort**: Medium | **Priority**: ⭐⭐⭐⭐

Share playlists with public links, discover trending/popular playlists from community.

**New Endpoints:**
```
POST /playlists/{id}/share - Generate share token
GET /playlists/public - List public playlists
GET /playlists/trending - Trending playlists
GET /playlists/shared/{token} - Get shared playlist
POST /playlists/{id}/make-public - Toggle public status
```

**Schema Changes:**
```sql
ALTER TABLE playlist ADD COLUMN is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE playlist ADD COLUMN view_count INTEGER DEFAULT 0;
ALTER TABLE playlist ADD COLUMN like_count INTEGER DEFAULT 0;

CREATE TABLE playlist_share (
    id UUID PRIMARY KEY,
    playlist_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlist(id)
);

CREATE TABLE playlist_like (
    user_id INTEGER,
    playlist_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, playlist_id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (playlist_id) REFERENCES playlist(id)
);
```

**Frontend Pages:**
- `/discover` - Browse trending playlists
- `/shared/{token}` - View shared playlists
- Share modal with link copy

---

### 9. 🔄 Playlist Variations & Remixes
**Value**: High | **Effort**: Medium | **Priority**: ⭐⭐⭐⭐

Generate variations of existing playlists with different moods, tempos, or energy levels.

**New Endpoint:**
```
POST /playlists/{id}/remix - Generate remix with new mood
```

**Changes Required:**
- Create remix workflow that reuses recommendation engine
- Store remix relationships (parent-child)
- Show remix options in UI

**Schema Changes:**
```sql
ALTER TABLE playlist ADD COLUMN parent_playlist_id INTEGER;
ALTER TABLE playlist ADD COLUMN remix_parameters JSON;
CREATE INDEX idx_parent_playlist ON playlist(parent_playlist_id);
```

**Remix Types:**
- **Energy Remix** - Higher/lower energy version
- **Mood Remix** - Different emotional tone
- **Tempo Remix** - Different speed
- **Genre Remix** - Explore different genres

**Files to Create:**
- `backend/app/playlists/remix_service.py` - Remix logic
- `frontend/src/components/features/playlist/RemixModal.tsx` - UI

---

### 10. 📅 Scheduled Playlist Generation
**Value**: Medium | **Effort**: Medium | **Priority**: ⭐⭐⭐

Let users schedule playlists to be generated at specific times.

**Task Queue Options:**
- Celery + Redis
- APScheduler
- Native async tasks

**Changes Required:**
- Database: Add scheduled_playlist table
- Backend: Task scheduler
- Frontend: Scheduling UI

**Schema:**
```sql
CREATE TABLE scheduled_playlist (
    id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,
    mood_prompt TEXT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    frequency VARCHAR(50), -- 'once', 'daily', 'weekly', 'monthly'
    is_active BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

**New Endpoints:**
```
POST /schedules - Create scheduled playlist
GET /schedules - List user's schedules
PUT /schedules/{id} - Update schedule
DELETE /schedules/{id} - Delete schedule
```

---

## 🏆 Tier 3: High Impact (6+ hours)

### 11. 👥 Collaborative Playlists
**Value**: High | **Effort**: High | **Priority**: ⭐⭐⭐⭐

Allow users to collaborate on playlists, invite friends, vote on tracks.

**Features:**
- Invite collaborators via email/link
- Real-time track additions
- Voting system (thumbs up/down)
- Role-based permissions (editor, viewer, voter)

**Schema:**
```sql
CREATE TABLE playlist_collaborator (
    id UUID PRIMARY KEY,
    playlist_id INTEGER,
    user_id INTEGER,
    role VARCHAR(50), -- 'owner', 'editor', 'viewer', 'voter'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlist(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE track_vote (
    id UUID PRIMARY KEY,
    playlist_id INTEGER,
    track_id VARCHAR(255),
    user_id INTEGER,
    vote INTEGER, -- -1, 0, 1 (down, none, up)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlist(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

**Real-time Features:**
- WebSocket for live updates
- Track addition notifications
- Vote count updates

---

### 12. 🏅 Achievements & Gamification
**Value**: Medium | **Effort**: High | **Priority**: ⭐⭐⭐

Unlock badges for various milestones and actions.

**Achievement Types:**
- **Creator**: Create 1, 5, 10, 25 playlists
- **Explorer**: Create playlists in 5, 10, 20 different moods
- **Genre Master**: Create playlists with 10+ different genres
- **Social Butterfly**: Share 5, 20 playlists
- **Remixer**: Create 5 remixes
- **Collaborator**: Collaborate on 5 playlists
- **Collector**: Save 10, 25, 50 playlists

**Schema:**
```sql
CREATE TABLE achievement (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    icon_url VARCHAR(255),
    tier INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_achievement (
    user_id INTEGER,
    achievement_id UUID,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_id),
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (achievement_id) REFERENCES achievement(id)
);
```

---

### 13. 🔔 Smart Notifications
**Value**: Medium | **Effort**: High | **Priority**: ⭐⭐⭐

Email/push notifications for quotas, trending playlists, collaborative updates.

**Notification Types:**
- Quota reset notifications
- Trending playlist alerts
- Collaborative updates
- Playlist completion confirmations
- Recommendation: Friend created playlist

**Infrastructure:**
- Notification service (SendGrid for email, FCM for push)
- In-app notification center
- Preference management

---

## 📱 Tier 4: Major Features (High Effort, High Value)

### 14. 📱 Mobile App
**Value**: High | **Effort**: Very High | **Priority**: ⭐⭐⭐

Native mobile experience via React Native or Flutter.

**Considerations:**
- Spotify SDK integration for mobile
- Offline playlist access
- Push notifications
- Share to Stories (Instagram, TikTok)

---

## 🔧 Implementation Priority Matrix

```
High Value + Low Effort (DO FIRST):
- Playlist Descriptions
- Favorites & Collections
- Mood Templates
- Audio Preview

High Value + Medium Effort (DO NEXT):
- Analytics & Insights
- Social Sharing & Discovery
- Playlist Remixes
- Collaborative Playlists

Medium Value + Low Effort (FILLER):
- Advanced Sliders
- Theme Customization
- Playlist Versioning

Medium Value + Medium Effort (LATER):
- Scheduled Playlists
- Achievements
- Notifications
```

---

## 📝 Technical Considerations

### Database Schema Evolution
Use Alembic migrations for all schema changes:
```bash
alembic revision --autogenerate -m "Add feature_name table"
alembic upgrade head
```

### API Versioning
Consider versioning new endpoints if breaking changes:
```
/api/v1/playlists - Current
/api/v2/playlists - With new fields
```

### Frontend Performance
- Lazy load analytics components
- Paginate discovery page
- Cache trending playlists
- Use React Query for data fetching

### Backend Optimization
- Add database indexes for new tables
- Cache frequently accessed data (Redis)
- Use bulk operations where possible
- Monitor query performance

---

## 🎯 Recommended Phased Rollout

### Phase 1 (Week 1-2): Quick Wins
1. Playlist Descriptions
2. Favorites & Collections
3. Mood Templates

### Phase 2 (Week 3-4): Discovery
4. Audio Preview
5. Social Sharing
6. Analytics Dashboard

### Phase 3 (Week 5-6): Collaboration & Engagement
7. Collaborative Playlists
8. Playlist Remixes
9. Achievements

### Phase 4 (Week 7+): Polish & Scale
10. Mobile App (or Web Push)
11. Scheduled Playlists
12. Notifications

---

## 📊 Success Metrics

For each feature, track:
- **Adoption Rate** - % of users using feature
- **Engagement** - Time spent, actions per session
- **Retention** - Return rate after first use
- **Satisfaction** - User feedback/ratings

---

## 🤝 Community Features Prioritization

Features that build community momentum:
1. Social Sharing (organic growth)
2. Collaborative Playlists (friend engagement)
3. Achievements (bragging rights)
4. Trending/Discovery (FOMO effect)

---

## 💡 Future Considerations

- **AI Improvements**: Mood recognition from images, voice analysis
- **Integrations**: Apple Music, YouTube Music, Amazon Music
- **Export**: Download as MP3, export to other services
- **Analytics Sharing**: Share stats with friends
- **Podcast Support**: Mix in podcasts with playlists
- **Lyric Integration**: Display lyrics, mood-based lyrics search
- **Concert Discovery**: Show concerts for artists in playlist

---

Last Updated: December 2024
