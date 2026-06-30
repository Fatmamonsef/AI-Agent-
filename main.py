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
    return {
        "message": "AI Text Correction API is running"
    }


class CorrectTextRequest(BaseModel):
    transcript: str


def process_text(text: str):
    """
    Process text and return correction results.
    """

    text = text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Transcript is empty."
        )

    corrected = correct_text(text)

    language = detect_language(text)

    errors = detect_errors(text)

    accuracy = calculate_accuracy(text, corrected)

    return {
        "success": True,
        "language": language,
        "errors": errors,
        "errors_count": len(errors),
        "word_count": len(text.split()),
        "corrected_text": corrected,
        "accuracy": accuracy,
    }
@app.post("/correct")
async def correct_file(file: UploadFile = File(...)):

    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .txt transcript file."
        )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        transcript = None

        encodings = [
            "utf-8",
            "utf-8-sig",
            "cp1256",
            "cp1252",
            "utf-16"
        ]

        for encoding in encodings:
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

        transcript = transcript.strip()

        if not transcript:
            raise HTTPException(
                status_code=400,
                detail="Transcript is empty."
            )

        result = process_text(transcript)
        result["filename"] = file.filename

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@app.post("/correct-text")
async def correct_text_endpoint(request: CorrectTextRequest):

    try:
        return process_text(request.transcript)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )