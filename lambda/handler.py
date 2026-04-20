"""
BG3 Party Builder -- Lambda Handler
"""
import json, os, re
from typing import Any


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _best_action_text(events: list[dict]) -> str:
    """
    Escolhe a melhor frase para o campo 'why'.
    Prefere frases curtas (< 80 chars), descritivas e sem aspas duplas no meio.
    """
    if not events:
        return ""

    def score(action: str) -> float:
        s = 0.0
        # Prefere frases curtas
        if len(action) <= 60:   s += 3.0
        elif len(action) <= 90: s += 1.5
        # Penaliza frases com muitas aspas (diálogos confusos)
        s -= action.count('"') * 0.5
        # Penaliza frases que começam com pronome (contexto muito específico)
        if action[:3].lower() in ("i b", "i t", "i p", "you", "he ", "she"):
            s -= 1.0
        # Bonus para frases que começam com verbo de ação
        first = action.split()[0].lower() if action.split() else ""
        if first in ("sacrifice", "encourage", "help", "save", "protect",
                     "agree", "support", "allow", "confess", "admit",
                     "defend", "tell", "ask", "say", "refuse", "fight"):
            s += 2.0
        return s

    return max(events, key=lambda e: score(e["action"]))["action"][:100]

PLAYSTYLES = {
    "hero": {
        "label": "The Hero",
        "description": "Protect innocents, fight evil, honor above all",
        "keywords": ["hero", "heroic", "protect", "innocent", "justice", "honor",
                     "good", "kind", "help", "save", "noble", "righteous"],
    },
    "villain": {
        "label": "The Villain",
        "description": "Cruel, manipulative, self-serving — power at any cost",
        "keywords": ["villain", "evil", "cruel", "manipulate", "selfish", "power",
                     "dark", "ruthless", "betray", "kill", "dominate",
                     "vampire", "blood", "ash", "leave", "enemy"],
    },
    "rogue": {
        "label": "The Rogue",
        "description": "Stealth, deception, and personal gain",
        "keywords": ["rogue", "stealth", "sneak", "deceive", "deception", "steal",
                     "cunning", "trick", "pragmatic", "thief", "secret",
                     "vampire", "blood", "feed", "guts", "back", "agree"],
    },
    "scholar": {
        "label": "The Scholar",
        "description": "Knowledge-seeking, magic-loving, thoughtful decisions",
        "keywords": ["magic", "scholar", "knowledge", "learn", "study", "smart",
                     "wizard", "intelligent", "curious", "arcane"],
    },
    "warrior": {
        "label": "The Warrior",
        "description": "Direct, strong, combat-focused",
        "keywords": ["warrior", "fight", "combat", "strong", "direct", "battle",
                     "power", "strength", "aggressive", "brute"],
    },
    "diplomat": {
        "label": "The Diplomat",
        "description": "Peaceful solutions, persuasion, protecting the vulnerable",
        "keywords": ["diplomat", "peaceful", "talk", "persuade", "negotiate",
                     "kind", "gentle", "compassion", "help", "balance"],
    },
}

_COMPANIONS = []
_APPROVAL_EVENTS = []
_DATA_LOADED = False


def _load_data():
    global _COMPANIONS, _APPROVAL_EVENTS, _DATA_LOADED
    if _DATA_LOADED:
        return

    bucket = os.environ.get("DATA_BUCKET", "")

    if bucket:
        # S3 — usado sempre que DATA_BUCKET estiver definido (prod e dev na Lambda)
        import boto3
        s3 = boto3.client("s3")
        def fetch(key):
            return json.loads(s3.get_object(Bucket=bucket, Key=key)["Body"].read())
        _COMPANIONS = fetch("companions.json")
        _APPROVAL_EVENTS = fetch("approval_events.json")
    else:
        # Local — usado apenas ao rodar direto no terminal
        base = os.path.join(os.path.dirname(__file__), "..", "data")
        with open(os.path.join(base, "companions.json"), encoding="utf-8") as f:
            _COMPANIONS = json.load(f)
        with open(os.path.join(base, "approval_events.json"), encoding="utf-8") as f:
            _APPROVAL_EVENTS = json.load(f)

    _DATA_LOADED = True
    print(f"[+] {len(_COMPANIONS)} companions, {len(_APPROVAL_EVENTS)} eventos")


def _detect_playstyle(description: str) -> str:
    desc = description.lower()
    best, best_score = "hero", 0
    for sid, style in PLAYSTYLES.items():
        score = sum(1 for kw in style["keywords"] if kw in desc)
        if score > best_score:
            best_score, best = score, sid
    return best


def _score_companion(companion: dict, style_id: str) -> dict:
    style = PLAYSTYLES[style_id]
    keywords = style["keywords"]
    name = companion["title"]

    comp_events = [e for e in _APPROVAL_EVENTS if e["companion"] == name]
    score = 0
    matching = []

    for e in comp_events:
        if any(kw in e["action"].lower() for kw in keywords):
            score += e["value"]
            matching.append(e)

    # Fallback via likes/dislikes se poucos matches
    if len(matching) < 2:
        likes = " ".join(companion.get("likes", [])).lower()
        dislikes = " ".join(companion.get("dislikes", [])).lower()
        score += sum(5 for kw in keywords if kw in likes)
        score -= sum(5 for kw in keywords if kw in dislikes)

    return {"companion": name, "score": score, "matching": matching}


def build_party(description: str, party_size: int = 3) -> dict:
    _load_data()

    style_id = description.lower() if description.lower() in PLAYSTYLES else _detect_playstyle(description)
    style = PLAYSTYLES[style_id]

    scores = sorted(
        [_score_companion(c, style_id) for c in _COMPANIONS],
        key=lambda x: x["score"], reverse=True
    )

    # Prefere companions com score positivo, completa com os melhores se necessário
    positive = [s for s in scores if s["score"] > 0]
    if len(positive) < party_size:
        positive = scores[:party_size]  # fallback: melhores disponíveis
    
    party = []
    for s in positive[:party_size]:
        comp = next(c for c in _COMPANIONS if c["title"] == s["companion"])
        pos_events = sorted([e for e in s["matching"] if e["value"] > 0],
                            key=lambda x: x["value"], reverse=True)
        reason = _best_action_text(pos_events) if pos_events else f"Approves of: {', '.join(comp.get('likes', [])[:2])}"

        party.append({
            "name": comp["title"],
            "class": f"{comp['class']} ({comp['subclass']})",
            "race": comp["race"],
            "compatibility_score": s["score"],
            "why": reason,
            "top_approved": [
                {"action": e["action"][:100], "value": e["value"]}
                for e in pos_events[:3]
            ],
            "url": comp["url"],
        })

    avoid = [
        {
            "name": next(c for c in _COMPANIONS if c["title"] == s["companion"])["title"],
            "score": s["score"],
            "why": "Dislikes: " + ", ".join(
                next(c for c in _COMPANIONS if c["title"] == s["companion"]).get("dislikes", [])[:2]
            ),
        }
        for s in scores[-2:] if s["score"] < 0
    ]

    return {
        "playstyle": {"id": style_id, "label": style["label"], "description": style["description"]},
        "party": party,
        "avoid": avoid,
    }


def get_companion_detail(name: str) -> dict:
    _load_data()
    comp = next((c for c in _COMPANIONS if c["title"].lower() == name.lower()), None)
    if not comp:
        return {"error": f"Companion '{name}' not found"}

    events = [e for e in _APPROVAL_EVENTS if e["companion"] == comp["title"]]
    return {
        "name": comp["title"],
        "class": comp["class"],
        "subclass": comp["subclass"],
        "race": comp["race"],
        "likes": comp["likes"],
        "dislikes": comp["dislikes"],
        "approval_thresholds": comp["approval_thresholds"],
        "url": comp["url"],
        "top_approved": sorted(
            [{"action": e["action"], "value": e["value"]} for e in events if e["value"] > 0],
            key=lambda x: x["value"], reverse=True
        )[:5],
        "top_disapproved": sorted(
            [{"action": e["action"], "value": e["value"]} for e in events if e["value"] < 0],
            key=lambda x: x["value"]
        )[:5],
        "total_events": len(events),
    }


def lambda_handler(event: dict, context: Any) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    try:
        path   = event.get("path", "/")
        params = event.get("queryStringParameters") or {}

        if path.endswith("/playstyles"):
            return {"statusCode": 200, "headers": headers,
                    "body": json.dumps({sid: {"label": s["label"], "description": s["description"]}
                                        for sid, s in PLAYSTYLES.items()})}

        if path.endswith("/companion"):
            name = params.get("name", "")
            if not name:
                return {"statusCode": 400, "headers": headers,
                        "body": json.dumps({"error": "Parametro 'name' obrigatorio"})}
            result = get_companion_detail(name)
            return {"statusCode": 404 if "error" in result else 200,
                    "headers": headers, "body": json.dumps(result, ensure_ascii=False)}

        style = params.get("style", "hero").strip()
        size  = max(1, min(int(params.get("size", "3")), 9))
        if not style:
            return {"statusCode": 400, "headers": headers,
                    "body": json.dumps({"error": "Parametro 'style' obrigatorio"})}

        return {"statusCode": 200, "headers": headers,
                "body": json.dumps(build_party(style, size), ensure_ascii=False)}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"statusCode": 500, "headers": headers,
                "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    import sys
    style = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "hero"
    result = build_party(style)

    print(f"\n{'='*60}")
    print(f"Playstyle: {result['playstyle']['label']}")
    print(f"{result['playstyle']['description']}")
    print(f"{'='*60}\n")
    print("Your ideal party:\n")
    for i, c in enumerate(result["party"], 1):
        s = c['compatibility_score']
        print(f"  {i}. {c['name']} ({c['class']})")
        print(f"     Score: {'+' if s >= 0 else ''}{s}")
        print(f"     Why: {c['why']}")
        for a in c["top_approved"][:2]:
            print(f"       +{a['value']}: {a['action']}")
        print()
    if result["avoid"]:
        print("Companions to avoid:\n")
        for c in result["avoid"]:
            print(f"  x {c['name']} (score: {c['score']}): {c['why']}")