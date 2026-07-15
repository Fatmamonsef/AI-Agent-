# Imports

import os
import re
import unicodedata
import requests

from difflib import SequenceMatcher

from dotenv import load_dotenv
from groq import Groq

from spellchecker import SpellChecker
import language_tool_python

from langdetect import detect


# Load Environment Variables

load_dotenv()


# Groq Client

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = None

if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)



# English NLP Tools

spell_en = SpellChecker(language="en")

tool_en = None

try:
    tool_en = language_tool_python.LanguageTool("en-US")
except Exception:
    pass


# Arabic NLP Tools

tool_ar = None

try:
    tool_ar = language_tool_python.LanguageTool("ar")
except Exception:
    pass


spell_ar = SpellChecker(language=None)


# Load Arabic Dictionary

ARABIC_DICTIONARY_URL = (
    "https://raw.githubusercontent.com/"
    "linuxscout/arabicwordlists/master/"
    "arabic-wordlist-65k.txt"
)

response = requests.get(ARABIC_DICTIONARY_URL)

arabic_words = response.text.splitlines()

spell_ar.word_frequency.load_words(arabic_words)

arabic_dictionary = set(arabic_words)

# Common Arabic Corrections

common_arabic_corrections = {

    "ذالك": "ذلك",
    "استتيع": "أستطيع",
    "البرمجه": "البرمجة",
    "هاذا": "هذا",
    "هاذي": "هذه",
    "هذى": "هذه",

    "انا": "أنا",
    "انت": "أنت",

  "اريد": "أريد",
    "ان": "أن",
    "اتعلم": "أتعلم",
    "ايضا": "أيضًا",
    "ايضاً": "أيضًا",

    "فى": "في",

    "الاطفال": "الأطفال",

    "البرمحه": "البرمجة",
    "برمحه": "برمجة",

    "الاصطناعى": "الاصطناعي",
    "اصطناعى": "اصطناعي",

    "صراحه": "صراحة",
    "بصراحه": "بصراحة",

    "كبيره": "كبيرة",
    "صغيره": "صغيرة",

    "ساعه": "ساعة",

    "بحب": "أحب",
    "بتحب": "تحب",

    "ما في": "لا يوجد",
    "مافي": "لا يوجد",

}
# ==========================================
# Helper Functions
# ==========================================

def clean_word(word):
    """
    Remove punctuation from a word.
    """
    return re.sub(r"[^\w\s]", "", word)


def normalize_arabic(text):
    """
    Normalize Arabic text before spell checking.
    """

    text = unicodedata.normalize("NFKC", text)

    # Remove Arabic diacritics
    text = re.sub(r'[\u064B-\u065F]', '', text)

    # Normalize Alef
    text = re.sub(r"[إأآٱ]", "ا", text)

    # Normalize Ya
    text = text.replace("ى", "ي")

    # Remove Tatweel
    text = text.replace("ـ", "")

    return text.strip()
# ==========================================
# Similarity Search
# ==========================================

def find_best_arabic_match(word):
    """
    Search the Arabic dictionary using similarity matching.
    """

    normalized_word = normalize_arabic(word)

    best_word = None
    best_score = 0

    for candidate in arabic_dictionary:

        if abs(len(candidate) - len(word)) > 2:
            continue

        score = SequenceMatcher(
            None,
            normalized_word,
            normalize_arabic(candidate)
        ).ratio()

        if score > best_score:
            best_score = score
            best_word = candidate

    if best_score >= 0.80:
        return best_word

    return None
    # ==========================================
# Language Detection
# ==========================================

def detect_language(text):
    """
    Detect Arabic or English language.
    """

    if not text or not text.strip():
        return "unknown"

    arabic_count = len(re.findall(r"[\u0600-\u06FF]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))

    if arabic_count > latin_count:
        return "ar"

    if latin_count > arabic_count:
        return "en"

    try:

        language = detect(text)

        if language in ["ar", "en"]:
            return language

    except Exception:
        pass

    return "unknown"
# ==========================================
# Error Detection
# ==========================================

def detect_errors(text):
    """
    Detect spelling errors.
    """

    language = detect_language(text)

    tokens = re.findall(r"[\w\u0600-\u06FF]+", text)

    if language == "ar":

        return list(spell_ar.unknown(tokens))

    elif language == "en":

        return list(spell_en.unknown(tokens))

    return []
# ==========================================
# English Correction
# ==========================================

def correct_english(text):
    """
    Correct English spelling and grammar.
    """

    words = text.split()

    corrected_words = []

    for word in words:

        clean = clean_word(word)

        if clean.lower() in spell_en:
            corrected_words.append(word)
            continue

        correction = spell_en.correction(clean)

        if correction:
            corrected_words.append(correction)
        else:
            corrected_words.append(word)

    corrected_text = " ".join(corrected_words)

    if tool_en is not None:

        try:

            matches = tool_en.check(corrected_text)

            corrected_text = language_tool_python.utils.correct(
                corrected_text,
                matches
            )

        except Exception:
            pass

    return corrected_text
# ==========================================
# Arabic Correction
# ==========================================
def correct_arabic(text):
    """
    Correct Arabic spelling and grammar.
    """

    correction_map = dict(common_arabic_corrections)

    phrase_corrections = {
        k: v
        for k, v in correction_map.items()
        if " " in k
    }

    word_corrections = {
        k: v
        for k, v in correction_map.items()
        if " " not in k
    }

    normalized_rules = {
        normalize_arabic(k): v
        for k, v in word_corrections.items()
    }

    corrected_text = text.strip()

    # Phrase Correction
    for phrase, replacement in sorted(
        phrase_corrections.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        corrected_text = re.sub(
            rf"\b{re.escape(phrase)}\b",
            replacement,
            corrected_text
        )

    tokens = re.findall(r"\S+", corrected_text)

    corrected_tokens = []

    # Rule-Based Correction
    for token in tokens:

        clean = normalize_arabic(clean_word(token))

        if not clean:
            corrected_tokens.append(token)
            continue

        # Rule-Based Dictionary
        if clean in normalized_rules:
            corrected_tokens.append(normalized_rules[clean])
            continue

        # Already Correct
        if clean in arabic_dictionary:
            corrected_tokens.append(token)
            continue

        # Candidate Generation
        candidates = list(spell_ar.candidates(clean) or [])

        if not candidates:

            fallback = find_best_arabic_match(clean)

            if fallback:
                corrected_tokens.append(fallback)
            else:
                corrected_tokens.append(token)

            continue

        # Candidate Ranking
        best_candidate = None
        best_score = 0

        for candidate in candidates:

            score = SequenceMatcher(
                None,
                clean,
                normalize_arabic(candidate)
            ).ratio()

            if candidate in arabic_dictionary:
               score += 0.05

            if score > best_score:
                best_score = score
                best_candidate = candidate

        # Final Decision
        if best_candidate and best_score >= 0.72:
            corrected_tokens.append(best_candidate)
        else:

            fallback = find_best_arabic_match(clean)

            if fallback:
                corrected_tokens.append(fallback)
            else:
                corrected_tokens.append(token)

    corrected_text = " ".join(corrected_tokens)

    # Final Rule-Based Replacement
    for wrong, correct in word_corrections.items():

        corrected_text = re.sub(
            rf"\b{re.escape(wrong)}\b",
            correct,
            corrected_text
        )

    # Grammar Checking
    if tool_ar is not None:

        try:

            matches = tool_ar.check(corrected_text)

            corrected_text = language_tool_python.utils.correct(
                corrected_text,
                matches
            )

        except Exception:
            pass

    corrected_text = corrected_text.replace("ًً", "ً")

    return corrected_text
# ==========================================
# Groq AI Refinement
# ==========================================

def groq_refine(text, language):
    """
    Use Groq LLM to refine spelling and grammar.
    """

    if client is None:
        return text

    if language == "ar":

        prompt = f"""
أنت مدقق لغوي عربي.

صحح الأخطاء الإملائية والنحوية فقط.

لا تعيد صياغة الجملة.
لا تغير المعنى.
أعد النص المصحح فقط.

النص:
{text}
"""

    else:

        prompt = f"""
You are an English proofreader.

Correct spelling and grammar only.

Do not rewrite the sentence.
Do not change the meaning.
Return ONLY the corrected text.

Text:
{text}
"""

    try:

        response = client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            temperature=0,

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]

        )

        return response.choices[0].message.content.strip()

    except Exception:

        return text
# ==========================================
# Main Correction Function
# ==========================================

def correct_text(text):
    """
    Hybrid AI Text Correction
    """

    language = detect_language(text)

    # Local NLP
    if language == "ar":

        corrected = correct_arabic(text)

    elif language == "en":

        corrected = correct_english(text)

    else:

        return text

    # استخدم Groq فقط لو التصحيح المحلى لم يغيّر النص
    if corrected.strip() == text.strip():

        corrected = groq_refine(text, language)

    return corrected               
# ==========================================
# Accuracy
# ==========================================

def calculate_accuracy(original, corrected):

    original_norm = re.sub(
        r"\s+",
        " ",
        re.sub(r"[^\w\s]", "", original.lower())
    ).strip()

    corrected_norm = re.sub(
        r"\s+",
        " ",
        re.sub(r"[^\w\s]", "", corrected.lower())
    ).strip()

    if not original_norm and not corrected_norm:
        return 100.0

    if not original_norm or not corrected_norm:
        return 0.0

    similarity = SequenceMatcher(
        None,
        original_norm,
        corrected_norm
    ).ratio()

    return round(similarity * 100, 2)