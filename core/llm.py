"""Legacy explanation validation retained for compatibility with existing callers."""
import re


# Conservative fail-closed guard: these subjects remain in server-rendered notes.
# Rejecting even a cautious mention is preferable to publishing an invented fact.
_UNSUPPORTED = re.compile(
    r"wi[ -]?fi|вай[ -]?фай|розет|socket|outlet|бесплат|free\b|цен[аыуе]|стоим|тенге|₸|\$|"
    r"ticket|price|открыт|закрыт|работает|open\b|closed\b|hours|расписан|круглосуточ|"
    r"т[её]пл[оыа]|отаплив|heated|warm\b|безопас|safe\b|гарант|guarantee|доступн.*коляс|"
    r"wheelchair|accessible|концерт|фестивал|event|событи|рейтинг|rating|звезд|звёзд|"
    r"проверен|verified|airside|landside|терминал|gate|посадоч|шлюз|охраняем|"
    r"[0-9]|https?://",
    re.IGNORECASE,
)


def validate_explanations(raw: object, allowed_ids: set[str]) -> dict[str, dict] | None:
    if not isinstance(raw, dict) or set(raw) != {"recommendations"}:
        return None
    records = raw["recommendations"]
    if not isinstance(records, list) or not 1 <= len(records) <= 3:
        return None
    result = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"poi_id", "reason", "action", "warnings"}:
            return None
        poi_id = record["poi_id"]
        if not isinstance(poi_id, str) or poi_id not in allowed_ids or poi_id in result:
            return None
        if not isinstance(record["warnings"], list) or len(record["warnings"]) > 3:
            return None
        texts = [record["reason"], record["action"], *record["warnings"]]
        if any(not isinstance(text, str) or not 1 <= len(text.strip()) <= 320 or _UNSUPPORTED.search(text) for text in texts):
            return None
        result[poi_id] = {"reason": record["reason"].strip(), "action": record["action"].strip(),
                          "warnings": [text.strip() for text in record["warnings"]]}
    return result if set(result) == allowed_ids else None

