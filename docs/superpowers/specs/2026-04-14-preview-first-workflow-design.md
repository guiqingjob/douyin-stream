# Preview-First Workflow Design Spec

## 1. Problem Statement
The current "1-Click Pipeline" MVP executes downloads blindly. When a user pastes a URL, the system automatically downloads the latest N videos and transcribes them. This "black box" approach causes anxiety:
- Users cannot preview what videos are available before downloading.
- Users cannot selectively choose which videos they actually want to transcribe.
- Users feel a lack of control over their local storage and processing pipeline.
- The system lacks the feel of a "Management Webpage" where data is presented first for decision-making.

## 2. Core Workflow Design: "Preview & Select"

To resolve the "blind download" issue, we will decouple the metadata fetching from the actual media downloading. The new workflow consists of three distinct phases:

### Step 1: Meta-Analysis (The "Fetch" Phase)
- The user inputs a Douyin Creator URL.
- The backend queries the platform API (via `f2`) to fetch **metadata only**.
- No `.mp4` files are downloaded. The system only retrieves:
  - Creator Profile (Avatar, Nickname, Bio).
  - A paginated list of their recent videos (Cover Image URL, Title, Duration, Publish Date, Likes).

### Step 2: Visual Selection (The "Choose" Phase)
- The React UI presents a "Creator Profile Header" and a "Video Grid/Table".
- Each video item acts as a selectable card.
- Users can visually browse the video titles, covers, and dates.
- Users check the boxes for the specific videos they are interested in analyzing/transcribing.

### Step 3: Execution (The "Pipeline" Phase)
- A floating action bar appears at the bottom: `[ Process Selected (3) Videos ]`.
- Upon clicking, the frontend sends only the selected video URLs/IDs to the backend.
- The backend task queue picks up these specific videos, downloads them, and runs the Qwen transcription pipeline.
- The UI polls the task status exactly as it does now, showing progress for the selected batch.

## 3. Backend Architecture Changes

We need to introduce two new API concepts to replace the monolithic pipeline trigger:

1. **Metadata Endpoint (`GET /api/v1/douyin/metadata`)**:
   - Accepts a URL.
   - Returns a JSON payload containing creator details and a list of video objects (up to a specified limit, e.g., 20).
   - This endpoint must be fast and lightweight, strictly avoiding heavy file I/O.

2. **Batch Pipeline Endpoint (`POST /api/v1/tasks/pipeline/batch`)**:
   - Accepts a payload containing a list of video URLs or specific Aweme IDs.
   - Enqueues background tasks specifically for those items.
   - Reuses the existing `task_queue` and SQLite tracking mechanisms.

## 4. Frontend Architecture Changes

1. **Discovery Page Redesign**:
   - **State 1 (Idle)**: The large search bar (as it is now).
   - **State 2 (Loading Meta)**: Skeleton loaders while fetching creator info.
   - **State 3 (Selection Mode)**: 
     - Top: Creator info card.
     - Middle: Grid of video thumbnails with titles and checkboxes.
     - Bottom: Sticky action bar with "Transcribe Selected" and "Cancel" buttons.
2. **Inbox Page Enhancement**:
   - When clicking on a subscribed creator in the Sidebar, show a similar grid.
   - Videos already transcribed will show a "Read Transcript" button.
   - Videos not yet downloaded will show a "Download & Transcribe" button, allowing historical backfilling.

## 5. Implementation Roadmap
1. Implement the `douyin/metadata` API endpoint in FastAPI, extracting logic from the existing `DouyinDownloader` to only fetch post metadata.
2. Build the React Video Grid component with multi-selection state.
3. Implement the `tasks/pipeline/batch` API endpoint to accept specific videos.
4. Wire the Frontend Selection Grid to the new Batch API.
