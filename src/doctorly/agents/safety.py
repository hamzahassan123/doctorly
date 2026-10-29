import re

_EMERGENCY_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bchest\s+(?:pain|pressure|tightness)\b",
        r"\b(?:severe\s+)?(?:difficulty|trouble)\s+breathing\b",
        r"\b(?:can'?t|cannot|unable\s+to)\s+breathe\b",
        r"\bshortness\s+of\s+breath\b",
        r"\bnot\s+breathing\b",
        r"\b(?:unconscious|unresponsive|passed\s+out|fainted)\b",
        r"\bsevere\s+bleeding\b",
        r"\bbleeding\s+(?:heavily|won'?t\s+stop)\b",
        r"\b(?:signs?\s+of\s+)?stroke\b",
        r"\bface\s+droop(?:ing)?\b",
        r"\bslurred\s+speech\b",
        r"\bseizure(?:s)?\b",
        r"\bsevere\s+allergic\s+reaction\b",
        r"\b(?:severe|crushing)\s+(?:abdominal|stomach)\s+pain\b",
        r"\b(?:pregnancy|pregnant).{0,30}\b(?:bleeding|severe\s+pain)\b",
        r"\b(?:saans|sans)\s+(?:nahi|nahin|na)\s+aa?\s+r(?:ahi|ahi)\b",
        r"\bsaans\s+(?:nahi|nahin)\s+aa\s+rahi\b",
        r"\bsaans\s+ruk\s+r(?:ahi|ahi)\s+(?:hai|hy)\b",
        r"\bseene?\s+mein\s+(?:bohat\s+)?dard\b",
        r"\b(?:seena|seenay)\s+(?:mein\s+)?dard\b",
        r"\bbehosh\s+(?:ho\s+gaya|ho\s+gayi|hai|hun)\b",
        r"\b(?:bohat|shadeed)\s+kh(?:oon|un)\s+beh\b",
        r"\bkh(?:oon|un)\s+band\s+nahi\s+ho\s+raha\b",
        r"سینے\s*میں\s*درد",
        r"(?:سانس|نَفَس)\s*(?:نہیں|نہيں)\s*آ\s*رہی",
        r"سانس\s*رک\s*رہی",
        r"(?:بے\s*ہوش|غشی)",
        r"(?:شدید\s*)?(?:خون\s*(?:بہہ?\s*رہا|بہنا)|خون\s*بند\s*نہیں\s*ہو\s*رہا)",
        r"(?:فالج|لقوہ)",
        r"(?:دورہ\s*پڑنا|مرگی\s*کا\s*دورہ)",
        r"شدید\s*(?:الرجی|پیٹ\s*درد)",
    )
)

_SYMPTOM_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:pain|ache|headache|fever|bleeding|breath(?:ing)?|dizz(?:y|iness)|"
        r"nausea|vomit(?:ing)?|weakness|numb(?:ness)?|symptom|injur(?:y|ed))\b",
        r"\b(?:dard|takleef|bukhar|chakkar|ulti|kamzori|saans|kh(?:oon|un))\b",
        r"(?:درد|تکلیف|بخار|چکر|قے|الٹی|کمزوری|سانس|خون)",
    )
)


def is_emergency(text: str) -> bool:
    return any(pattern.search(text) for pattern in _EMERGENCY_PATTERNS)


def mentions_symptom_or_pain(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SYMPTOM_PATTERNS)
