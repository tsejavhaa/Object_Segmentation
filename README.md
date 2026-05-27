# Object Segmentation

A web-based object segmentation app using multiple state-of-the-art models via HuggingFace `transformers` pipelines. Supports **image**, **video**, and **live webcam** segmentation through a clean browser interface.

![](/test/screen.png)

## Tech Stack

- **Backend:** FastAPI (Python) with Uvicorn
- **Frontend:** Vanilla HTML / CSS / JS (served by FastAPI)
- **Models:** HuggingFace `transformers` pipelines (SAM, SegFormer, Mask2Former, OneFormer)
- **Media:** OpenCV for image/video processing

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Models download automatically from HuggingFace on first use.

## Run

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser. The frontend is served automatically at the root URL.

## Features

- **Source tabs** — switch between Image, Video, and Live Stream modes
- **Drag & drop upload** — supports images and videos
- **File info** — shows file name, size, dimensions (W×H, MP), and video duration after upload
- **Progress indicator** — percentage-based progress bar during segmentation
- **Side-by-side viewer** — compares original and segmented results
- **Model selector** — switch segmentation models at runtime via dropdown
- **Task history** — collapsible panel stores previous tasks with thumbnails, metadata, and click-to-restore
- **Live webcam stream** — real-time segmentation via WebSocket

## Project Structure

```
├── backend/
│   ├── config.py              # Paths and constants
│   ├── main.py                # FastAPI app, lifespan, routing
│   ├── schemas.py             # Pydantic request/response models
│   ├── task_history.py        # In-memory task history store
│   ├── models/
│   │   ├── base.py            # Abstract base model + overlay logic
│   │   ├── registry.py        # Model registry (register, load, switch)
│   │   ├── sam_model.py       # SAM (ViT-base, ViT-huge)
│   │   ├── segformer_model.py # SegFormer
│   │   ├── mask2former_model.py
│   │   └── oneformer_model.py
│   └── routers/
│       └── api.py             # All REST + WebSocket endpoints
├── frontend/
│   ├── index.html             # Main UI
│   ├── css/style.css          # Styling
│   └── js/app.js              # Client-side logic
├── uploads/                   # Uploaded media + segmentation results
├── logs/
│   └── backend.log            # Rotating debug logs (10 MB, 5 backups)
└── requirements.txt
```

## Models

Models are registered in a registry and loaded on demand. Only one model is active at a time.

| Key | HuggingFace Model | Pipeline | Description |
|-----|-------------------|----------|-------------|
| `sam3` | `facebook/sam-vit-base` | mask-generation | Default model, fast general-purpose segmentation |
| `sam2` | `facebook/sam-vit-huge` | mask-generation | Larger SAM, higher accuracy |
| `segformer` | `nvidia/segformer-b0-finetuned-ade-512-512` | image-segmentation | Lightweight semantic segmentation, fast |
| `mask2former` | `facebook/mask2former-swin-small-coco-instance` | image-segmentation | Universal panoptic/instance segmentation |
| `oneformer` | `shi-labs/oneformer_ade20k_swin_tiny` | image-segmentation | Single model for all segmentation tasks |

Default model (`sam3`) loads at startup. Switch models at runtime via the API or frontend dropdown.

## API

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload an image or video file |
| POST | `/api/segment` | Segment an uploaded image |
| POST | `/api/segment/video` | Segment a video (frame-by-frame) |
| GET | `/api/models` | List registered models |
| POST | `/api/models/switch` | Switch the active model |
| GET | `/api/status` | Server and model status |
| GET | `/api/history` | List task history (max 100 entries) |
| GET | `/api/history/{task_id}` | Get specific task details |
| WebSocket | `/api/stream` | Real-time webcam segmentation stream |

### Image Segmentation

```
POST /api/segment
Body: form-data
  file_path: <path from /api/upload response>
  model_name: sam3 (default)
```

Response:
```json
{
  "overlay_url": "/uploads/results/<id>_overlay.png",
  "mask_url": "/uploads/results/<id>_mask.png",
  "num_masks": 5,
  "original_url": "/uploads/images/<file>",
  "model_name": "sam3",
  "computation_time": 1.234
}
```

### Video Segmentation

```
POST /api/segment/video
Body: form-data
  file_path: <path from /api/upload response>
  frame_skip: 5 (process every 6th frame)
```

Response:
```json
{
  "video_url": "/uploads/results/<id>_segmented.mp4",
  "frames_processed": 120
}
```

### WebSocket Stream

Connect to `ws://localhost:8000/api/stream`. Send frames as JSON:

```json
{
  "action": "segment",
  "image": "data:image/jpeg;base64,..."
}
```

Receives overlay frames as base64 JPEG:

```json
{
  "overlay": "/9j/4AAQ..."
}
```

### Task History

Tasks are recorded automatically with metadata:

```json
GET /api/history
{
  "tasks": [
    {
      "task_id": "abc123",
      "timestamp": "2026-05-27T12:34:56",
      "model_name": "mask2former",
      "file_name": "photo.jpg",
      "mask_count": 8,
      "computation_time": 2.345,
      "status": "success",
      "overlay_url": "/uploads/results/<id>_overlay.png",
      "mask_url": "/uploads/results/<id>_mask.png",
      "original_url": "/uploads/images/<file>",
      "metadata": {
        "width": 1920,
        "height": 1080,
        "file_size": 245760
      }
    }
  ]
}
```

## Logs

Debug logs are written to `logs/backend.log` with rotation (10 MB max per file, 5 backups).

## Supported Formats

- **Images:** PNG, JPG, JPEG, BMP, WebP
- **Videos:** MP4, AVI, MOV, MKV
