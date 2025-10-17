# RecoBeat API Documentation

## Base URL
```
https://api.reccobeats.com
```

## Authentication
No API keys required, but implement rate limiting for production use.

---

## 1. Track Recommendations
**GET** `/v1/track/recommendation`

### Query Parameters
- `size` (integer, required): Total return tracks (1-100)
- `seeds` (string[], required): List of Track's ReccoBeats ID or Spotify ID (1-5)
- `negativeSeeds` (string[], optional): Tracks to avoid/dislike (1-5)
- `acousticness` (float, 0-1): Confidence measure of acoustic elements
- `danceability` (float, 0-1): Suitability for dancing
- `energy` (float, 0-1): Intensity and liveliness
- `instrumentalness` (float, 0-1): Likelihood of no vocal content
- `key` (integer, -1-11): Musical key (0=C, 1=C#/Db, 2=D, etc.)
- `liveness` (float, 0-1): Probability of live performance
- `loudness` (float, -60-2): Overall loudness in decibels
- `mode` (integer, 0-1): Major (1) or minor (0) modality
- `speechiness` (float, 0-1): Presence of spoken words
- `tempo` (float, 0-250): Estimated tempo in BPM
- `valence` (float, 0-1): Musical positiveness (0=negative/sad, 1=positive/happy)
- `popularity` (integer, 0-100): Track popularity
- `featureWeight` (float, 1-5): Influence scaling of audio features

---

## 2. Get Multiple Tracks
**GET** `/v1/track`

### Query Parameters
- `ids` (string[], required): List of Track's ReccoBeats ID or Spotify ID (1-40)

### Response Schema
```json
{
  "content": [
    {
      "id": "string",
      "trackTitle": "string",
      "artists": "object[]",
      "durationMs": "integer",
      "isrc": "string",
      "ean": "string",
      "upc": "string",
      "href": "string",
      "availableCountries": "string",
      "popularity": "integer"
    }
  ]
}
```

---

## 3. Get Track Audio Features
**GET** `/v1/track/{id}/audio-features`

### Path Parameters
- `id` (string, required): ReccoBeats's Track ID

### Response Schema
```json
{
  "id": "string",
  "href": "string",
  "acousticness": "float",
  "danceability": "float",
  "energy": "float",
  "instrumentalness": "float",
  "key": "integer",
  "liveness": "float",
  "loudness": "float",
  "mode": "integer",
  "speechiness": "float",
  "tempo": "float",
  "valence": "float"
}
```

---

## 4. Search Artist
**GET** `/v1/artist/search`

### Query Parameters
- `page` (integer, 0-1000): Page number (default: 0)
- `size` (integer, 1-50): Elements per page (default: 25)
- `searchText` (string, required): Artist name to search (≤1000 chars)

### Response Schema
```json
{
  "content": [
    {
      "id": "string",
      "name": "string",
      "href": "string"
    }
  ],
  "page": "integer",
  "size": "integer",
  "totalElements": "integer",
  "totalPages": "integer"
}
```

---

## 5. Get Multiple Artists
**GET** `/v1/artist`

### Query Parameters
- `ids` (string[], required): List of Artist's ReccoBeats ID or Spotify ID (1-40)

### Response Schema
```json
{
  "content": [
    {
      "id": "string",
      "name": "string",
      "href": "string"
    }
  ]
}
```

---

## Integration Notes

### Rate Limiting
- Implement proper rate limiting to avoid API restrictions
- Consider caching frequently accessed data
- Handle rate limit errors gracefully

### Audio Features Mapping
- Use audio features for sophisticated mood analysis
- Map mood prompts to appropriate feature ranges
- Combine multiple features for better recommendations

### Seed Strategy
- Use user's top tracks/artists as seeds
- Extract audio features from seeds for better recommendations
- Balance between user's taste and mood requirements