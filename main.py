from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from correction import (
    detect_language,
    detect_errors,
    correct_text,
    calculate_accuracy,
)

app = FastAPI(
    title="AI Text Correction API",
    version="1.0.0"
)


@app.get("/")
def home():
    return {"message": "AI Text Correction API is running"}


@app.post("/correct")
async def correct_file(file: UploadFile = File(...)):

    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .txt transcript file."
        )

    try:
        content = await file.read()

        transcript = None

        for encoding in ["utf-8", "utf-8-sig", "cp1256", "cp1252", "utf-16"]:
            try:
                transcript = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if transcript is None:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file encoding."
            )

        language = detect_language(transcript)

        errors = detect_errors(transcript)

        corrected = correct_text(transcript)

        accuracy = calculate_accuracy(transcript, corrected)

        return {
            "filename": file.filename,
            "language": language,
            "errors": errors,
            "corrected_text": corrected,
            "accuracy": accuracy,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


class CorrectTextRequest(BaseModel):
    transcript: str


@app.post("/correct-text")
async def correct_text_endpoint(request: CorrectTextRequest):

    if not request.transcript or not request.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="Transcript is empty."
        )

    try:
        language = detect_language(request.transcript)

        errors = detect_errors(request.transcript)

        corrected = correct_text(request.transcript)

        accuracy = calculate_accuracy(request.transcript, corrected)

        return {
            "language": language,
            "errors": errors,
            "corrected_text": corrected,
            "accuracy": accuracy,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )