# Remix API Examples & Integration Guide
## Complete cURL and JavaScript Examples

**Document**: API Reference for Playlist Remixes  
**Last Updated**: December 2024

---

## 📡 API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/playlists/{id}/remix-options` | Get available remix types |
| POST | `/playlists/{id}/create-remix` | Create a remix |
| GET | `/playlists/{id}/remix-chain` | Get version history |
| GET | `/playlists/{id}/remixes` | Get remixes of this playlist |
| GET | `/remix-statistics` | Get user's remix stats |

---

## 🔍 1. Get Remix Options

### Purpose
Retrieve available remix types and parameters for a playlist.

### cURL

```bash
curl -X GET \
  http://localhost:8000/api/playlists/42/remix-options \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript

```typescript
async function getRemixOptions(playlistId: number) {
  const response = await fetch(`/api/playlists/${playlistId}/remix-options`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  })
  return response.json()
}

// Usage
const options = await getRemixOptions(42)
console.log(options.remix_types)
// Output:
// [
//   {
//     type: "energy",
//     name: "Energy Remix",
//     description: "Adjust the energy level of the playlist",
//     parameters: { energy_adjustment: { type: "slider", min: -50, max: 50, default: 20 } }
//   },
//   ...
// ]
```

### Response Example

```json
{
  "original_playlist_id": 42,
  "original_mood": "energetic workout mix with high-tempo bangers",
  "remix_types": [
    {
      "type": "energy",
      "name": "Energy Remix",
      "description": "Adjust the energy level of the playlist",
      "parameters": {
        "energy_adjustment": {
          "type": "slider",
          "min": -50,
          "max": 50,
          "default": 20,
          "step": 10,
          "unit": "% adjustment"
        }
      }
    },
    {
      "type": "mood",
      "name": "Mood Remix",
      "description": "Shift to a different emotional tone",
      "parameters": {
        "mood_shift": {
          "type": "select",
          "options": ["happier", "sadder", "more_intense", "more_chill", "more_upbeat"],
          "default": "happier"
        }
      }
    },
    {
      "type": "tempo",
      "name": "Tempo Remix",
      "description": "Change the speed of the tracks",
      "parameters": {
        "tempo_adjustment": {
          "type": "slider",
          "min": -30,
          "max": 30,
          "default": 15,
          "step": 5,
          "unit": "% adjustment"
        }
      }
    },
    {
      "type": "genre",
      "name": "Genre Remix",
      "description": "Explore a different genre while keeping the mood",
      "parameters": {
        "genre_shift": {
          "type": "select",
          "options": ["electronic", "acoustic", "indie", "hip_hop", "pop", "rock", "jazz"],
          "default": "electronic"
        }
      }
    },
    {
      "type": "danceability",
      "name": "Danceability Remix",
      "description": "Make it more or less dancefloor-friendly",
      "parameters": {
        "danceability_adjustment": {
          "type": "slider",
          "min": -40,
          "max": 40,
          "default": 20,
          "step": 10,
          "unit": "% adjustment"
        }
      }
    }
  ],
  "current_analysis": {
    "primary_emotion": "energetic",
    "energy_level": 0.85,
    "tempo_bpm": 140
  }
}
```

---

## ✨ 2. Create Remix

### Purpose
Create a remix with specified parameters. This returns metadata to start a new workflow.

### cURL

```bash
curl -X POST \
  http://localhost:8000/api/playlists/42/create-remix \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remix_type": "energy",
    "remix_parameters": {
      "energy_adjustment": 30
    }
  }'
```

### With Custom Mood

```bash
curl -X POST \
  http://localhost:8000/api/playlists/42/create-remix \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remix_type": "mood",
    "remix_parameters": {
      "mood_shift": "happier"
    },
    "custom_mood": "super happy and euphoric workout"
  }'
```

### JavaScript

```typescript
async function createRemix(
  playlistId: number,
  remixType: string,
  remixParameters: Record<string, any>,
  customMood?: string
) {
  const response = await fetch(`/api/playlists/${playlistId}/create-remix`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    },
    body: JSON.stringify({
      remix_type: remixType,
      remix_parameters: remixParameters,
      custom_mood: customMood
    })
  })
  
  if (!response.ok) {
    throw new Error(`Failed to create remix: ${response.statusText}`)
  }
  
  return response.json()
}

// Usage
const remixData = await createRemix(
  42,
  'energy',
  { energy_adjustment: 30 }
)

// Then start workflow with:
// const workflow = await startPlaylistWorkflow(remixData.mood_prompt, {
//   parent_playlist_id: remixData.parent_playlist_id,
//   remix_type: remixData.remix_type,
//   remix_parameters: remixData.remix_parameters
// })
```

### Response Example

```json
{
  "remix_type": "energy",
  "mood_prompt": "energetic workout mix with high-tempo bangers, but more energetic and intense",
  "original_mood_prompt": "energetic workout mix with high-tempo bangers",
  "parent_playlist_id": 42,
  "remix_generation": 1,
  "message": "Remix created. Start workflow to generate new playlist."
}
```

---

## 🔗 3. Get Remix Chain (Version History)

### Purpose
Get the complete lineage of a playlist - from original through all remixes.

### cURL

```bash
curl -X GET \
  http://localhost:8000/api/playlists/45/remix-chain \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript

```typescript
async function getRemixChain(playlistId: number) {
  const response = await fetch(`/api/playlists/${playlistId}/remix-chain`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  })
  return response.json()
}

// Usage
const { remix_chain } = await getRemixChain(45)
console.log(remix_chain)
// Shows full lineage from original to current
```

### Response Example

```json
{
  "remix_chain": [
    {
      "id": 42,
      "name": "Workout Mix",
      "mood_prompt": "energetic workout mix with high-tempo bangers",
      "is_remix": false,
      "remix_type": null,
      "remix_generation": 0,
      "created_at": "2024-12-10T08:00:00"
    },
    {
      "id": 45,
      "name": "High Energy Workout",
      "mood_prompt": "energetic workout mix with high-tempo bangers, but more energetic and intense",
      "is_remix": true,
      "remix_type": "energy",
      "remix_generation": 1,
      "created_at": "2024-12-15T10:30:00"
    },
    {
      "id": 48,
      "name": "Electronic High Energy Workout",
      "mood_prompt": "energetic workout mix with high-tempo bangers, but more energetic, reimagined in electronic style",
      "is_remix": true,
      "remix_type": "genre",
      "remix_generation": 2,
      "created_at": "2024-12-16T14:20:00"
    }
  ]
}
```

---

## 📚 4. Get Playlist Remixes

### Purpose
Get all remixes that were created FROM a specific playlist.

### cURL

```bash
curl -X GET \
  http://localhost:8000/api/playlists/42/remixes \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript

```typescript
async function getPlaylistRemixes(playlistId: number) {
  const response = await fetch(`/api/playlists/${playlistId}/remixes`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  })
  return response.json()
}

// Usage
const { remixes } = await getPlaylistRemixes(42)
console.log(`Found ${remixes.length} remixes of this playlist`)
remixes.forEach(remix => {
  console.log(`- ${remix.name} (${remix.remix_type} remix)`)
})
```

### Response Example

```json
{
  "remixes": [
    {
      "id": 45,
      "name": "High Energy Workout",
      "remix_type": "energy",
      "remix_generation": 1,
      "created_at": "2024-12-15T10:30:00",
      "track_count": 25
    },
    {
      "id": 50,
      "name": "Chill Workout",
      "remix_type": "mood",
      "remix_generation": 1,
      "created_at": "2024-12-17T09:15:00",
      "track_count": 25
    },
    {
      "id": 55,
      "name": "Electronic Workout",
      "remix_type": "genre",
      "remix_generation": 1,
      "created_at": "2024-12-18T16:45:00",
      "track_count": 25
    }
  ]
}
```

---

## 📊 5. Get Remix Statistics

### Purpose
Get remix creation metrics for the current user.

### cURL

```bash
curl -X GET \
  http://localhost:8000/api/remix-statistics \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### JavaScript

```typescript
async function getRemixStatistics() {
  const response = await fetch('/api/remix-statistics', {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  })
  return response.json()
}

// Usage
const stats = await getRemixStatistics()
console.log(`Total remixes created: ${stats.total_remixes_created}`)
console.log(`Remix chains: ${stats.number_of_remix_chains}`)
console.log(`Average remixes per original: ${stats.average_remixes_per_original.toFixed(2)}`)
```

### Response Example

```json
{
  "total_remixes_created": 12,
  "number_of_remix_chains": 5,
  "max_remix_generation": 3,
  "average_remixes_per_original": 2.4
}
```

---

## 🔌 Complete Workflow Integration

### Full Example: Create Remix and Start Generation

```typescript
// Step 1: Get remix options
const options = await getRemixOptions(42)

// Step 2: User selects remix type and parameters
const selectedRemixType = 'energy'
const remixParams = { energy_adjustment: 25 }

// Step 3: Create remix
const remixData = await createRemix(42, selectedRemixType, remixParams)

// Step 4: Start workflow with remix mood
const workflow = await fetch('/api/workflow/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    mood_prompt: remixData.mood_prompt,
    parent_playlist_id: remixData.parent_playlist_id,
    is_remix: true,
    remix_type: remixData.remix_type,
    remix_parameters: remixData.remix_parameters,
    remix_generation: remixData.remix_generation
  })
})

const { session_id } = await workflow.json()

// Step 5: Show workflow progress with session_id
startProgressTracking(session_id)

// Step 6: On completion, new playlist is created with:
// - parent_playlist_id = 42
// - is_remix = true
// - remix_type = 'energy'
// - remix_generation = 1
```

---

## 🧪 Testing Remixes

### Test Scenario 1: Simple Remix

```bash
# Get a user's playlists
curl http://localhost:8000/api/playlists -H "Authorization: Bearer TOKEN"

# Pick a playlist ID (e.g., 42)

# Get remix options
curl http://localhost:8000/api/playlists/42/remix-options \
  -H "Authorization: Bearer TOKEN"

# Create an energy remix
curl -X POST http://localhost:8000/api/playlists/42/create-remix \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remix_type": "energy",
    "remix_parameters": {"energy_adjustment": 25}
  }'

# Note the returned mood_prompt for workflow

# Get remix chain (should show original and new remix)
curl http://localhost:8000/api/playlists/45/remix-chain \
  -H "Authorization: Bearer TOKEN"
```

### Test Scenario 2: Remix Chain

```bash
# Create first remix (ID: 45)
# Then create remix of that remix

curl -X POST http://localhost:8000/api/playlists/45/create-remix \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "remix_type": "genre",
    "remix_parameters": {"genre_shift": "electronic"}
  }'

# Get chain (should show 3 items: original → remix 1 → remix 2)
curl http://localhost:8000/api/playlists/48/remix-chain \
  -H "Authorization: Bearer TOKEN"

# Check generation numbers
# Original: remix_generation = 0
# First remix: remix_generation = 1
# Second remix: remix_generation = 2
```

### Test Scenario 3: Statistics

```bash
# Create multiple remixes
# Then check statistics

curl http://localhost:8000/api/remix-statistics \
  -H "Authorization: Bearer TOKEN"

# Should show:
# - total_remixes_created: N
# - number_of_remix_chains: M
# - max_remix_generation: X
# - average_remixes_per_original: Y
```

---

## 🐛 Common Issues & Solutions

### Issue: 404 Not Found on remix endpoint

**Cause**: Endpoint not registered or backend not restarted

**Solution**: 
```bash
# Restart backend
uvicorn app.main:app --reload

# Or if using Docker:
docker-compose restart backend
```

### Issue: Foreign key constraint error on create

**Cause**: parent_playlist_id references non-existent playlist

**Solution**:
- Verify playlist exists and belongs to user
- Check migration ran successfully

### Issue: Remix chain returns only current playlist

**Cause**: Migration didn't create self-referential relationship properly

**Solution**:
```bash
# Check database schema
psql -d moodlist -c "\d playlists"

# Should show:
# - parent_playlist_id column (int, nullable)
# - is_remix column (boolean)
# - remix_parameters column (json)
# - remix_generation column (int)

# If missing, re-run migration or manually alter:
ALTER TABLE playlists ADD COLUMN parent_playlist_id INTEGER;
```

### Issue: RemixModal not showing

**Cause**: Component import missing or props incorrect

**Solution**:
```typescript
// Verify import
import { RemixModal } from '@/components/features/playlist/RemixModal'

// Verify props passed correctly
<RemixModal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  playlistId={playlist.id}
  playlistName={playlist.name}
  onRemixCreated={(data) => handleRemixCreated(data)}
/>
```

---

## 📈 Performance Tips

### Optimizing Remix Queries

```typescript
// GOOD: Use pagination for large remix lists
const getPlaylistRemixes = async (playlistId: number, limit = 50, offset = 0) => {
  const response = await fetch(
    `/api/playlists/${playlistId}/remixes?limit=${limit}&offset=${offset}`
  )
  return response.json()
}

// CAUTION: Getting very deep chains (10+ levels) could be slow
// Consider adding depth limit in frontend

// Cache remix options since they don't change per playlist
const remixOptionsCache = new Map()
const getCachedRemixOptions = async (playlistId: number) => {
  if (remixOptionsCache.has(playlistId)) {
    return remixOptionsCache.get(playlistId)
  }
  const options = await getRemixOptions(playlistId)
  remixOptionsCache.set(playlistId, options)
  return options
}
```

### Database Indexes

The model includes these indexes automatically:
- `ix_playlist_parent_remix` on (parent_playlist_id, is_remix)
- Foreign key index on parent_playlist_id

These make remix queries fast even with thousands of playlists.

---

## 📚 Additional Resources

- **REMIX_IMPLEMENTATION.md** - Architecture and implementation details
- **RemixModal.tsx** - Frontend component code
- **remix_service.py** - Backend service code
- **routes.py** - API endpoint code

---

**Ready to integrate? Start with the workflow integration example above!**

