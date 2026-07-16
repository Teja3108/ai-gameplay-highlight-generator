# AI Gameplay Shorts Generator

Professional AI-powered gameplay shorts creation for Senpai Plays. This local-first application turns gameplay recordings into vertical highlight clips. The React web app uploads a recording to the FastAPI service; the service runs the existing local AI engine, persists project state, and exposes completed clips for in-browser preview and saving.

This is a single-user local application. Do not expose the API or its storage directory to an untrusted network.

## Installation

Prerequisites:

- Node.js 20.18+ and npm 10.8+
- Python 3.9+
- [uv](https://docs.astral.sh/uv)
- The local AI engine repository and its Python environment
- FFmpeg and the dependencies required by the engine

Install the web and API dependencies:

```bash
git clone <repository-url>
cd ai-gameplay-highlight-generator
cp .env.example .env
npm install
uv sync --project apps/api --extra dev
```

## Desktop release (macOS Apple Silicon)

For a double-clickable macOS application, build the release on an Apple Silicon Mac with the existing local AI engine available:

```bash
RELEASE_ENGINE_ROOT=/absolute/path/to/AI-Youtube-Shorts-Generator make release
```

The resulting DMG is written to `Release/`. The release build bundles the frontend, local API runtime, and configured AI engine; the installed application starts and stops its local services automatically. See [Release/INSTALLATION.md](Release/INSTALLATION.md) and [Release/QUICK_START.md](Release/QUICK_START.md).

## Configuration

Edit `.env` before starting the API. These values are required for processing:

```dotenv
GAMEPLAY_ENGINE_ROOT=/absolute/path/to/AI-Youtube-Shorts-Generator
GAMEPLAY_ENGINE_PYTHON=/absolute/path/to/AI-Youtube-Shorts-Generator/.venv/bin/python
GAMEPLAY_ENGINE_OUTPUT_DIR=/absolute/path/to/AI-Youtube-Shorts-Generator/output
```

Useful local settings:

| Variable              | Purpose                                          | Default                     |
| --------------------- | ------------------------------------------------ | --------------------------- |
| `VITE_API_BASE_URL`   | Web app API address                              | `http://localhost:8000/api` |
| `GAMEPLAY_DATA_DIR`   | Persistent uploads, results, and project history | `.data` in this repository  |
| `MAX_UPLOAD_BYTES`    | Maximum accepted upload size                     | 100 GB                      |
| `MAX_CONCURRENT_JOBS` | Number of simultaneous local engine processes    | `1`                         |
| `CORS_ALLOW_ORIGINS`  | Allowed local web origins                        | Vite localhost origins      |
| `ALLOWED_HOSTS`       | Accepted Host headers                            | `localhost,127.0.0.1`       |

Keep `.env` private. It may contain local paths and provider credentials used by the engine.

## Running locally

Start the API in one terminal:

```bash
uv run --project apps/api uvicorn app.main:app --reload
```

Start the web app in another:

```bash
npm run dev:web
```

Open the Vite address shown in the terminal (normally `http://localhost:5173`). A working session follows this path:

1. Upload an MP4, MOV, MKV, or WebM gameplay file.
2. Choose clip count, game profile, layout, and whether to review candidates before rendering.
3. Monitor processing; failed or cancelled projects can be resumed when their original upload is still available.
4. In review mode, select candidates and render them. Otherwise the engine renders the requested top clips directly.
5. Open the completed project in **Review** to preview and save rendered clips.
6. Use **Projects** or **History** to reopen a completed project or resume an interrupted one.

The settings page stores default game profile and layout in the current browser. It does not store secrets or modify the engine environment.

## Quality checks

```bash
npm run lint
npm run typecheck
npm run build
cd apps/api && uv run --extra dev ruff check . && uv run --extra dev black --check . && uv run --extra dev pytest
```

`make lint`, `make test`, and `make format-check` provide the same common checks. Run `docker compose config` to validate the optional local API container configuration.

## Troubleshooting

**The web app reports that the local service is offline**

Start the API, ensure it is listening on port 8000, and confirm `VITE_API_BASE_URL` points to its `/api` path.

**A job fails immediately with an engine configuration error**

Verify `GAMEPLAY_ENGINE_ROOT` contains `main.py` and `GAMEPLAY_ENGINE_PYTHON` points to the engine’s executable Python environment. Restart the API after changing `.env`.

**Rendering fails after candidates are selected**

Confirm the engine environment has FFmpeg and all local rendering dependencies installed. The project log records the engine output; correct the dependency issue and use **Resume project**.

**A project cannot be resumed**

Resume requires the original upload to remain below `GAMEPLAY_DATA_DIR/uploads`. Start a new project if that file has been deleted or moved.

**The upload is rejected**

Use an MP4, MOV, MKV, or WebM file and keep it below `MAX_UPLOAD_BYTES`.

## Architecture

```text
Browser (React/Vite)
  └─ FastAPI /api
       ├─ streams uploads into .data/uploads
       ├─ keeps durable job state in .data/jobs.json
       ├─ starts the existing local AI engine as a subprocess
       └─ serves completed local clip files after path validation
```

The API intentionally orchestrates the engine rather than duplicating transcription, scoring, or rendering logic. Job polling occurs only while one or more jobs are queued or processing. Jobs interrupted by an API restart are retained and marked recoverable.

## Folder structure

```text
apps/
  api/                   FastAPI API, orchestration, and tests
  web/                   React + TypeScript interface
docs/                    Product and architecture records
scripts/                 Setup, API, migration, lint, and test helpers
```

## Developer guide

- Keep browser controls tied to API data or browser-persisted preferences; do not add simulated controls or metrics.
- Preserve the engine boundary in `apps/api/app/api.py`. New UI behavior should use the existing job, resume, render, and file endpoints where possible.
- The API only accepts source paths created by its upload endpoint and only serves files under approved local roots.
- Add API tests under `apps/api/tests` for validation and state transitions. Run the quality checks before committing.
- Persistent local job state is intentionally separate from the earlier SQLAlchemy support layer; do not rely on a browser path or expose internal source paths in API responses.

## Author

Developed by **Teja Goud**

GitHub: [github.com/Teja3108](https://github.com/Teja3108)

Built for Senpai Plays.

## Credits

The application is built with React, TypeScript, Vite, TanStack Query, Lucide, FastAPI, and FFmpeg, alongside the existing local AI engine. Their maintainers and open-source communities make this project possible.

## License

Distributed under the [MIT License](LICENSE).
