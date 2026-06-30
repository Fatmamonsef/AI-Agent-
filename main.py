from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from correction import (
    detect_language,
    detect_errors,
    correct_text,
    calculate_accuracy,
)

app = FastAPI(title="AI Text Correction API", version="1.0.0")

@app.get("/")
def home():
    return {"message": "AI Text Correction API is running"}

@app.post("/correct")
async def correct_endpoint(
    file: UploadFile | None = File(None), 
    text: str | None = Form(None)  # Form عشان يشتغل مع multipart
):
    transcript = None
    
    # 1. لو جاي File ليه الاولوية
    if file:
        if not file.filename.endswith(".txt"):
            raise HTTPException(status_code=400, detail="Please upload a .txt file.")
        try:
            content = await file.read()
            for encoding in ["utf-8", "utf-8-sig", "cp1256", "cp1252", "utf-16"]:
                try:
                    transcript = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if transcript is None:
                raise HTTPException(status_code=400, detail="Unsupported file encoding.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # 2. لو مش File يبقى لازم يبقى Text
    elif text and text.strip():
        transcript = text
    
    # 3. لو مفيش الاتنين
    else:
        raise HTTPException(status_code=400, detail="Send 'file' or 'text'.")

    # 4. هنا الكود بتاعك هيشتغل مرة واحدة على الـ transcript
    try:
        language = detect_language(transcript)
        errors = detect_errors(transcript)
        corrected = correct_text(transcript)
        accuracy = calculate_accuracy(transcript, corrected)
        return {
            "input_type": "file" if file else "text",
            "language": language,
            "errors": errors,
            "corrected_text": corrected,
            "accuracy": accuracy,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
