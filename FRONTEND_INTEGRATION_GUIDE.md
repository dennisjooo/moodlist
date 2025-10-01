# Frontend Integration Guide: Agentic Mood-Based Playlist System

## 🎵 Overview

This guide provides a concise integration path for connecting your Next.js frontend to the Agentic backend system. The system uses LangGraph for sophisticated mood-based playlist generation with human-in-the-loop editing capabilities.

## 🏗️ Architecture

```
Next.js Frontend ↔ FastAPI Backend ↔ LangGraph Agents ↔ Spotify + RecoBeat APIs
```

## 🚀 Core API Endpoints

### 1. Start Workflow
```typescript
POST /api/agents/recommendations/start
// Request: { mood_prompt, user_id, access_token }
// Response: { session_id, status: "started" }
```

### 2. Poll Status
```typescript
GET /api/agents/recommendations/{session_id}/status
// Returns: { status, current_step, recommendation_count, awaiting_input, error? }
```

### 3. Get Results
```typescript
GET /api/agents/recommendations/{session_id}/results
// Returns: { recommendations[], playlist?, mood_analysis }
```

### 4. Apply Edits
```typescript
POST /api/agents/recommendations/{session_id}/edit
// Request: { edit_type: "reorder"|"remove", track_id, new_position?, reasoning? }
```

## 🎨 Implementation Strategy

### Workflow State Management
```typescript
// Use the existing workflowContext.tsx and workflowApi.ts
import { useWorkflow } from '@/lib/workflowContext';
import { startRecommendation, pollWorkflowStatus } from '@/lib/workflowApi';

const { workflowState, startWorkflow, applyEdit } = useWorkflow();
```

### Progressive UI Updates
```typescript
// Use existing WorkflowProgress.tsx component
<WorkflowProgress sessionId={sessionId} />
```

### Human-in-the-Loop Editing
```typescript
// Use existing PlaylistResults.tsx for editing interface
<PlaylistResults
  sessionId={sessionId}
  recommendations={recommendations}
  onEdit={handleEdit}
/>
```

## 🔄 Real-Time Updates

### Polling Strategy
```typescript
// Use existing pollingManager.ts
import { usePollingManager } from '@/lib/pollingManager';

const pollingManager = usePollingManager();
pollingManager.startPolling(sessionId, handleStatusUpdate);
```

## 🎯 User Experience Flow

1. **Input**: User enters mood prompt
2. **Processing**: 🤔 Analyzing → 🎵 Gathering → 🎼 Generating
3. **Editing**: ✏️ User refines playlist (reorder/remove tracks)
4. **Creation**: ✅ Finalize → 🎼 Create Spotify playlist

## 🔧 Key Components

### Existing Files to Use:
- `frontend/src/lib/workflowContext.tsx` - State management
- `frontend/src/lib/workflowApi.ts` - API calls
- `frontend/src/lib/pollingManager.ts` - Real-time updates
- `frontend/src/components/WorkflowProgress.tsx` - Progress UI
- `frontend/src/components/PlaylistResults.tsx` - Editing interface

### Integration Steps:
1. Import and use existing workflow hooks
2. Connect mood input to `startWorkflow()`
3. Display progress with `WorkflowProgress`
4. Enable editing with `PlaylistResults`
5. Handle completion and show final playlist

## 📱 Mobile Optimization

- Touch-friendly drag handles (44px minimum)
- Optimistic UI updates for smooth interactions
- Lazy loading for heavy components

## 🔒 Security

- Secure token storage in localStorage
- Client-side request validation
- Error handling with retry logic

## 🚀 Performance

- Intelligent polling (2s active, 5s waiting)
- Optimistic updates for instant feedback
- Caching for repeated requests

## 🎊 Ready to Integrate!

The frontend components are already built and ready to use. Simply connect your mood input to the workflow system and enjoy sophisticated AI-powered playlist generation with human-in-the-loop editing! 🎵✨