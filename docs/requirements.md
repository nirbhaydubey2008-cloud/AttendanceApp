# Requirements Documentation

## Dependency Map: Features → Packages

| Functional Module | Required Feature | Package | Role |
|---|---|---|---|
| **Vision — Detection** | Face detection (Haar cascades) | `opencv-python` | Built-in cascade classifiers for face detection |
| **Vision — Tracking** | Multi-face tracking with persistent IDs | `deep-sort-realtime` | DeepSORT algorithm for re-identification |
| **Vision — Landmarks** | Face mesh / landmark detection | `mediapipe` | Google's face mesh solution (468 landmarks) |
| **Vision — Recognition** | Face recognition / verification | `deepface` | Identity verification against enrolled faces |
| **Audio — I/O** | Read/write audio files | `soundfile` | wav/flac/ogg file I/O |
| **Audio — Analysis** | Feature extraction (RMS, MFCC, ZCR) | `librosa` | Audio signal analysis library |
| **Numerical** | Array operations, math | `numpy` | Foundation for all numerical processing |
| **Data** | DataFrames, time-series, export | `pandas` | Structured data manipulation |
| **Backend** | REST API server | `fastapi` | HTTP endpoints for all services |
| **Backend** | ASGI server | `uvicorn` | Runs FastAPI application |
| **Backend** | WebSocket support | `websockets` | Real-time data streaming |
| **Backend** | File uploads | `python-multipart` | Multipart form data parsing |
| **Database** | ORM, SQLite operations | `sqlalchemy` | Object-relational mapping |
| **Config** | Environment variables | `python-dotenv` | Load `.env` configuration |
| **Dashboard** | Interactive UI | `streamlit` | Local web dashboard |
| **Optional** | Cloud LLM insights | `groq` | Groq API client (disabled by default) |

## Version Constraints Rationale

| Package | Constraint | Reason |
|---|---|---|
| `opencv-python` | `>=4.8.0,<5.0.0` | 4.8+ has stable Haar cascades on arm64; stay on v4 |
| `mediapipe` | `>=0.10.9,<0.11.0` | 0.10.x is the latest stable line with Python 3.11 wheels |
| `deepface` | `>=0.0.93` | Recent versions support onnxruntime backend (avoids heavy TF) |
| `deep-sort-realtime` | `>=1.3.2,<2.0.0` | 1.3.2 is stable with Python 3.11 |
| `librosa` | `>=0.10.1,<0.11.0` | 0.10.x has lazy loading, better performance |
| `numpy` | `>=1.24.0,<2.0.0` | NumPy 2.0 has breaking API changes; stay on 1.x |
| `fastapi` | `>=0.104.0,<1.0.0` | Recent stable with Pydantic v2 support |
| `sqlalchemy` | `>=2.0.0,<3.0.0` | Modern SQLAlchemy 2.0 ORM style |
| `streamlit` | `>=1.29.0,<2.0.0` | Stable with chart/table components |

## Platform-Specific Notes

### macOS (Apple Silicon / arm64)
- **MediaPipe**: Native arm64 wheels available from v0.10.x
- **DeepFace with onnxruntime**: `onnxruntime` has native arm64 support. Default backend — no TensorFlow needed.
- **OpenCV**: `opencv-python` provides universal2 wheels for macOS
- **deep-sort-realtime**: Works with numpy/scipy on arm64. Does NOT require PyTorch for our use case (we provide our own embeddings from DeepFace).
- **Librosa**: Requires `libsndfile` (installed via `soundfile` or `brew install libsndfile`)

### Linux (x86_64)
- All packages have standard wheels. No special steps needed.

### Windows
- `soundfile` may require manual install of libsndfile DLL
- MediaPipe requires Visual C++ Redistributable

## Core vs. Optional Dependencies

**Core** (required for all functionality):
- opencv-python, mediapipe, deepface, deep-sort-realtime
- librosa, soundfile
- numpy, pandas
- fastapi, uvicorn, websockets, python-multipart
- sqlalchemy, python-dotenv, streamlit

**Optional** (enhanced features, not required):
- groq (cloud LLM insights — requires API key + internet)

## Security Notes
- No package requires root/admin privileges to install
- No package phones home during normal operation (except `deepface` on first model download)
- The `groq` package is disabled by default and requires explicit API key configuration
