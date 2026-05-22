from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.analysis_service import analyze_dataframe, analyze_file_bytes
from src.loader import load_data


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"
BASE_PATH = "/agri-trust"

REPORTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Agri Data Trust API", version="2.0.0")
app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
app.mount(f"{BASE_PATH}/assets", StaticFiles(directory=WEB_DIR / "assets"), name="prefixed-assets")
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")
app.mount(f"{BASE_PATH}/reports", StaticFiles(directory=REPORTS_DIR), name="prefixed-reports")


def _html(name: str) -> FileResponse:
    return FileResponse(WEB_DIR / name, media_type="text/html; charset=utf-8")


@app.get("/")
@app.get(f"{BASE_PATH}/")
def index() -> FileResponse:
    return _html("index.html")


@app.get("/methodology")
@app.get(f"{BASE_PATH}/methodology")
def methodology() -> FileResponse:
    return _html("methodology.html")


@app.get("/01_methodology")
@app.get(f"{BASE_PATH}/01_methodology")
def old_methodology_redirect() -> RedirectResponse:
    return RedirectResponse(url=f"{BASE_PATH}/methodology", status_code=301)


@app.get("/health")
@app.get(f"{BASE_PATH}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
@app.post(f"{BASE_PATH}/api/analyze")
async def analyze_upload(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="请上传 CSV、XLSX 或 XLS 文件。")
    try:
        content = await file.read()
        return analyze_file_bytes(content, file.filename, REPORTS_DIR, BASE_PATH)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"分析失败：{exc}") from exc


@app.get("/api/sample/{kind}")
@app.get(f"{BASE_PATH}/api/sample/{{kind}}")
def analyze_sample(kind: str) -> dict:
    sample_map = {
        "real": "sample_real.csv",
        "fake": "sample_fake.csv",
    }
    if kind not in sample_map:
        raise HTTPException(status_code=404, detail="未知示例数据。")
    filename = sample_map[kind]
    df = load_data(DATA_DIR / filename)
    return analyze_dataframe(df, filename, REPORTS_DIR, BASE_PATH)

