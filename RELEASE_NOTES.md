# AI Gameplay Shorts Generator 1.0.2

AI Gameplay Shorts Generator 1.0.2 fixes the packaged local LLM provider configuration for Apple Silicon Macs.

## Highlights

- Launch the application directly from macOS—no browser or terminal session is required for daily use.
- Review detected moments in AI Review Studio, approve or reject candidates, fine-tune in/out points, and batch render the selected clips.
- Projects, review decisions, settings, and rendered clips are retained in the app's local application data folder.
- Raised the supported upload limit to 100 GB with streamed writes and storage validation.
- Added Gemini retry/backoff, model fallback, safe API-key rotation, and recoverable paused projects.
- Improved navigation recovery, safe resume behavior, and local clip streaming.
- Gemini is now the default local highlight-ranking provider; OpenAI is used only when explicitly selected.

## System requirements

- macOS 13 Ventura or later
- Apple Silicon (M1 or newer)
- At least 8 GB RAM; 16 GB is recommended for local AI processing
- Free disk space for source recordings, local models, and rendered clips

## Known release limitation

The supplied DMG is unsigned while Apple Developer signing and notarization credentials are unavailable. macOS may require an explicit **Open** action from Finder on first launch. The application runs entirely locally and starts no network-facing service.
