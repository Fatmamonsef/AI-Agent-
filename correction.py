##  Import Libraries
import re
import requests
from spellchecker import SpellChecker
import language_tool_python
from langdetect import detect
from difflib import SequenceMatcher
## Initialize English Tools
spell_en = SpellChecker(language='en')

tool_en = None
tool_ar = None

try:
    tool_en = language_tool_python.LanguageTool('en-US')
except ModuleNotFoundError:
    pass

try:
    tool_ar = language_tool_python.LanguageTool('ar')
except ModuleNotFoundError:
    pass
##  Create Arabic Dictionary
spell_ar = SpellChecker(language=None)

url = "https://raw.githubusercontent.com/linuxscout/arabicwordlists/master/arabic-wordlist-65k.txt"
response = requests.get(url)
arabic_words = response.text.splitlines()
spell_ar.word_frequency.load_words(arabic_words)

common_arabic_corrections = {
    'البرمحه': 'البرمجة',
    'الاصطناعى': 'الاصطناعي',
    'برمحه': 'برمجة',
    'اصطناعى': 'اصطناعي',
    'هاذا': 'هذا',
    'جدا': 'جداً',
    'بحب': 'أحب',
    'بتحب': 'تحب',
    'انا': 'أنا',
    'انت': 'أنت',
    'اللي': 'الذي',
    'ممكن': 'يمكن',
    'كدا': 'كذا',
    'كده': 'كذا',
    'مهمه': 'مهمة',
    'كبيره': 'كبيرة',
    'صغيره': 'صغيرة',
    'يومى': 'يومي',
    'صراحه': 'صراحة',
    'بصراحه': 'بصراحة',
    'ساعه': 'ساعة',
}
##  Detect Language
def detect_language(text):
    if not text or not text.strip():
        return "unknown"

    arabic_count = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_count = len(re.findall(r'[A-Za-z]', text))

    if arabic_count and arabic_count >= latin_count:
        return "ar"

    if latin_count and latin_count > arabic_count:
        return "en"

    try:
        lang = detect(text)
        if lang == "ar":
            return "ar"
        if lang == "en":
            return "en"
        return "unknown"
    except Exception:
        return "unknown"
## Clean Word
def clean_word(word):

    return re.sub(r'[^\w\s]', '', word)
##  Detect Errors
def detect_errors(text):
    """كشف الأخطاء الإملائية في النص"""
    language = detect_language(text)
    tokens = re.findall(r'[\w\u0600-\u06FF]+', text)
    errors = []

    if language == "ar":
        misspelled = spell_ar.unknown(tokens)
        errors = list(misspelled)
    elif language == "en":
        misspelled = spell_en.unknown(tokens)
        errors = list(misspelled)

    return errors
##  Correct English Text
def correct_english(text):
    """تصحيح الأخطاء الإملائية والنحوية في النصوص الإنجليزية"""
    words = text.split()
    corrected_words = []

    for word in words:
        clean = clean_word(word)
        
        # تحقق إذا كانت الكلمة صحيحة
        if clean.lower() in spell_en:
            corrected_words.append(word)
        else:
            # حاول تصحيح الكلمة
            correction = spell_en.correction(clean)
            if correction:
                corrected_words.append(correction)
            else:
                corrected_words.append(word)

    corrected_text = " ".join(corrected_words)

    # تطبيق التصحيح النحوي إذا كان Java متاحاً
    if tool_en is not None:
        try:
            matches = tool_en.check(corrected_text)
            corrected_text = language_tool_python.utils.correct(
                corrected_text,
                matches
            )
        except:
            pass

    return corrected_text
## Correct Arabic Text
def correct_arabic(text):
    """تصحيح الأخطاء الإملائية والنحوية في النصوص العربية بشكل أدق"""

    correction_map = dict(common_arabic_corrections)
    correction_map.update({
        'ما في': 'لا يوجد',
        'مافي': 'لا يوجد',
        'هاذي': 'هذه',
        'هذى': 'هذه',
        'ايضا': 'أيضًا',
        'ايضاً': 'أيضًا',
        'الاطفال': 'الأطفال',
        'يلعب': 'يلعبون',
        'فى': 'في',
        'في': 'في',
        'البرمحه': 'البرمجة',
        'برمحه': 'برمجة',
        'الاصطناعى': 'الاصطناعي',
        'اصطناعى': 'اصطناعي',
    })

    phrase_corrections = {k: v for k, v in correction_map.items() if ' ' in k}
    word_corrections = {k: v for k, v in correction_map.items() if ' ' not in k}

    corrected_text = text.strip()

    for phrase, replacement in sorted(phrase_corrections.items(), key=lambda item: len(item[0]), reverse=True):
        corrected_text = re.sub(rf'\b{re.escape(phrase)}\b', replacement, corrected_text)

    tokens = re.findall(r'\S+', corrected_text)
    corrected_tokens = []

    for token in tokens:
        clean = clean_word(token)
        if not clean:
            corrected_tokens.append(token)
            continue

        if clean in word_corrections:
            corrected_tokens.append(word_corrections[clean])
            continue

        if clean in set(word_corrections.values()):
            corrected_tokens.append(clean)
            continue

        if clean in spell_ar:
            corrected_tokens.append(token)
            continue

        candidates = list(spell_ar.candidates(clean) or [])
        if not candidates:
            corrected_tokens.append(token)
            continue

        best_candidate = None
        best_score = 0.0
        for candidate in candidates:
            score = SequenceMatcher(None, clean, candidate).ratio()
            if candidate in word_corrections.values():
                score += 0.08
            if score > best_score:
                best_candidate = candidate
                best_score = score

        if best_score >= 0.72:
            corrected_tokens.append(best_candidate)
        else:
            corrected_tokens.append(token)

    corrected_text = ' '.join(corrected_tokens)

    for old, new in word_corrections.items():
        corrected_text = re.sub(rf'\b{re.escape(old)}\b', new, corrected_text)

    if tool_ar is not None:
        try:
            matches = tool_ar.check(corrected_text)
            corrected_text = language_tool_python.utils.correct(corrected_text, matches)
        except Exception:
            pass
    corrected_text = corrected_text.replace("ًً", "ً")
    return corrected_text


## Main Correction Function

def correct_text(text):

    language = detect_language(text)

    if language == "ar":
        return correct_arabic(text)
    else:
        return correct_english(text)

## Accuracy Function

def calculate_accuracy(original, corrected):
    """حساب دقة التصحيح بطريقة أوضح من المقارنة الحرفية البحتة"""
    original_norm = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', original.lower())).strip()
    corrected_norm = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', corrected.lower())).strip()

    if not original_norm and not corrected_norm:
        return 100.0

    if not original_norm or not corrected_norm:
        return 0.0

    similarity_ratio = SequenceMatcher(None, original_norm, corrected_norm).ratio()
    return round(similarity_ratio * 100, 2)

