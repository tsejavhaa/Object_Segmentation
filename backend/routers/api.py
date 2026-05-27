import os
import uuid
import json
import base64
import time
import logging
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from backend.config import IMAGE_DIR, VIDEO_DIR, RESULT_DIR, SUPPORTED_FORMATS
from backend.schemas import ModelInfo, ModelsList, StatusResponse, SegmentResponse
from backend.models.registry import get_registry
from backend.task_history import TaskRecord, get_history_store

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _save_upload(file: UploadFile, dest_dir: str) -> str:
    ext = _get_ext(file.filename or ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(dest_dir, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def _rel_path(path: str) -> str:
    return path.split("uploads/")[-1] if "uploads/" in path else path


@router.post("/upload")
async def upload_file(file: UploadFile):
    ext = _get_ext(file.filename or "")
    logger.info("Upload: file=%s ext=%s", file.filename, ext)
    if ext not in SUPPORTED_FORMATS:
        logger.warning("Unsupported format: %s", ext)
        return {"error": f"Unsupported format: {ext}"}

    if ext in {".mp4", ".avi", ".mov", ".mkv"}:
        path = _save_upload(file, VIDEO_DIR)
        source_type = "video"
    else:
        path = _save_upload(file, IMAGE_DIR)
        source_type = "image"

    logger.info("Saved upload: path=%s type=%s", path, source_type)
    return {"file_path": path, "source_type": source_type, "filename": file.filename}


@router.post("/segment")
async def segment_image(file_path: str = Form(...), model_name: str = Form("sam3")):
    logger.info("Segment request: file=%s model=%s", file_path, model_name)
    task_id = uuid.uuid4().hex
    file_name = os.path.basename(file_path)
    history = get_history_store()

    if not os.path.exists(file_path):
        logger.error("File not found: %s", file_path)
        history.add(TaskRecord(task_id, model_name, file_name, 0, 0, "error",
                               error_message="File not found"))
        return {"error": "File not found"}

    registry = get_registry()
    if model_name != registry.get_active_name():
        logger.info("Switching to model: %s", model_name)
        await registry.load_model(model_name)

    model = await registry.get_active()
    image = cv2.imread(file_path)
    if image is None:
        logger.error("Failed to read image: %s", file_path)
        history.add(TaskRecord(task_id, model_name, file_name, 0, 0, "error",
                               error_message="Failed to read image"))
        return {"error": "Failed to read image"}

    logger.debug("Image loaded: shape=%s", image.shape)

    t0 = time.perf_counter()
    masks, overlay = await model.segment_with_overlay(image)
    elapsed = time.perf_counter() - t0

    result_id = uuid.uuid4().hex
    overlay_path = os.path.join(RESULT_DIR, f"{result_id}_overlay.png")
    mask_path = os.path.join(RESULT_DIR, f"{result_id}_mask.png")

    cv2.imwrite(overlay_path, overlay)

    combined_mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
    for m in masks:
        combined_mask[m] = 255
    cv2.imwrite(mask_path, combined_mask)

    overlay_url = f"/uploads/results/{os.path.basename(overlay_path)}"
    mask_url = f"/uploads/results/{os.path.basename(mask_path)}"

    height, width = image.shape[:2]
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    history.add(TaskRecord(
        task_id=task_id,
        model_name=model_name,
        file_name=file_name,
        mask_count=len(masks),
        computation_time=round(elapsed, 3),
        status="success",
        overlay_url=overlay_url,
        mask_url=mask_url,
        original_url=f"/uploads/{_rel_path(file_path)}",
        metadata={"width": width, "height": height, "file_size": file_size},
    ))

    logger.info("Segment done: %d masks in %.3fs", len(masks), elapsed)

    return SegmentResponse(
        overlay_url=overlay_url,
        mask_url=mask_url,
        num_masks=len(masks),
        original_url=f"/uploads/{_rel_path(file_path)}",
        model_name=model_name,
        computation_time=round(elapsed, 3),
    )


@router.post("/segment/video")
async def segment_video(file_path: str = Form(...), frame_skip: int = Form(5)):
    logger.info("Video segment request: file=%s frame_skip=%d", file_path, frame_skip)
    if not os.path.exists(file_path):
        logger.error("Video file not found: %s", file_path)
        return {"error": "File not found"}

    registry = get_registry()
    model = await registry.get_active()
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.debug("Video info: fps=%.2f size=%dx%d", fps, width, height)

    result_id = uuid.uuid4().hex
    out_path = os.path.join(RESULT_DIR, f"{result_id}_segmented.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_fps = max(1, fps // (frame_skip + 1))
    out = cv2.VideoWriter(
        out_path, fourcc, out_fps, (width, height)
    )

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    processed = 0
    frame_idx = 0
    log_interval = max(1, total_frames // 20 // (frame_skip + 1))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % (frame_skip + 1) == 0:
            _, overlay = await model.segment_with_overlay(frame)
            out.write(overlay)
            processed += 1
            if processed % log_interval == 0:
                pct = processed * (frame_skip + 1) / total_frames * 100
                logger.info("Video progress: %d/%d frames (%.0f%%)", processed, (total_frames + frame_skip) // (frame_skip + 1), min(pct, 100))
        frame_idx += 1

    cap.release()
    out.release()
    logger.info("Video segment done: frames_processed=%d/%d out=%s", processed, total_frames, out_path)

    return {
        "video_url": f"/uploads/results/{os.path.basename(out_path)}",
        "frames_processed": frame_idx,
    }


@router.websocket("/stream")
async def stream_segment(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    registry = get_registry()
    model = await registry.get_active()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("action") == "segment":
                img_data = msg.get("image")
                if img_data:
                    img_bytes = base64.b64decode(img_data.split(",")[1])
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    logger.debug("WebSocket segment: shape=%s", image.shape)

                    _, overlay = await model.segment_with_overlay(image)
                    _, buffer = cv2.imencode(".jpg", overlay)
                    overlay_b64 = base64.b64encode(buffer).decode("utf-8")

                    await websocket.send_json({"overlay": overlay_b64})
                    logger.debug("WebSocket overlay sent")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


@router.get("/models", response_model=ModelsList)
async def list_models():
    registry = get_registry()
    models = registry.list_models()
    return ModelsList(models=[ModelInfo(**m) for m in models])


@router.post("/models/switch")
async def switch_model(model_name: str = Form(...)):
    logger.info("Switch model request: %s", model_name)
    registry = get_registry()
    await registry.load_model(model_name)
    logger.info("Switched to model: %s", model_name)
    return {"status": "ok", "active_model": model_name}


@router.get("/status", response_model=StatusResponse)
async def get_status():
    registry = get_registry()
    try:
        await registry.get_active()
        loaded = True
    except RuntimeError:
        loaded = False
    return StatusResponse(
        status="running",
        model_loaded=loaded,
        active_model=registry.get_active_name(),
    )


@router.get("/history")
async def list_history():
    history = get_history_store()
    return {"tasks": history.get_all()}


@router.get("/history/{task_id}")
async def get_task(task_id: str):
    history = get_history_store()
    task = history.get(task_id)
    if task is None:
        return {"error": "Task not found"}
    return task