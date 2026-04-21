"""
BG3 Lore Search -- Scraper
Coleta dados da bg3.wiki via API MediaWiki e salva como JSON estruturado.

Paginas coletadas:
  - Companions (Shadowheart, Astarion, Gale, Karlach, Wyll, Lae'zel, Halsin, Jaheira, Minsc)
  - Aprovacao por ato (Act One/Approval, Act Two/Approval, Act Three/Approval)
  - Paginas de classes, racas, spells (expansivel)

Saida: data/pages.json e data/companions.json
"""

import requests
import json
import time
import re
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup

# --------------------------------------------------
# Configuracao
# --------------------------------------------------

API_URL    = "https://bg3.wiki/w/api.php"
BASE_URL   = "https://bg3.wiki/wiki"
OUTPUT_DIR = Path(__file__).parent / "data"

# Rate limit 
REQUEST_DELAY = 1.0  # segundos entre requests

HEADERS = {
    "User-Agent": "BG3LoreSearch/1.0 (projeto de portfolio DevOps; contato via GitHub)"
}

# Paginas a coletar, organizadas por categoria
PAGES_TO_SCRAPE = {
    "companions": [
        "Shadowheart",
        "Astarion",
        "Gale",
        "Karlach",
        "Wyll",
        "Lae'zel",
        "Halsin",
        "Jaheira",
        "Minsc",
        "Minthara",
    ],
    "approval": [
        "Approval",
        "Act_One/Approval",
        "Act_Two/Approval",
        "Act_Three/Approval",
    ],
    "mechanics": [
        "Companions",
        "Long_rest",
        "Camp",
    ],
    "classes": [
        "Barbarian",
        "Bard",
        "Cleric",
        "Druid",
        "Fighter",
        "Monk",
        "Paladin",
        "Ranger",
        "Rogue",
        "Sorcerer",
        "Warlock",
        "Wizard",
    ],
    "lore": [
        "Mind Flayer",
        "Illithid",
        "Githyanki",
        "Githzerai",
        "Absolute",
        "Netherbrain",
        "Tadpole",
        "Ceremorphosis"
    ],
}

# Companions e dados estaticos conhecidos 
COMPANION_METADATA = {
    "Shadowheart": {
        "class": "Cleric",
        "subclass": "Trickery Domain",
        "race": "High Half-Elf",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["Stealth", "pragmatism", "helping injured", "Shar worship"],
        "dislikes": ["unnecessary cruelty", "hurting innocents", "disrespecting gods"],
    },
    "Astarion": {
        "class": "Rogue",
        "subclass": "Arcane Trickster",
        "race": "High Elf",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["manipulation", "self-interest", "cruelty to enemies", "freedom"],
        "dislikes": ["selfless acts", "helping strangers for free", "weakness"],
    },
    "Gale": {
        "class": "Wizard",
        "subclass": "Evocation",
        "race": "Human",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["kindness", "magic", "knowledge", "helping others"],
        "dislikes": ["cruelty", "destroying magic items", "ignorance"],
    },
    "Karlach": {
        "class": "Barbarian",
        "subclass": "Berserker",
        "race": "Asmodeus Tiefling",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["justice", "fighting evil", "loyalty", "directness"],
        "dislikes": ["devils", "cruelty", "betrayal", "cowardice"],
    },
    "Wyll": {
        "class": "Warlock",
        "subclass": "The Fiend",
        "race": "Human",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["heroism", "protecting innocents", "justice", "honor"],
        "dislikes": ["cruelty", "deals with devils", "cowardice", "harming innocents"],
    },
    "Lae'zel": {
        "class": "Fighter",
        "subclass": "Battle Master",
        "race": "Githyanki",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["strength", "directness", "combat prowess", "githyanki culture"],
        "dislikes": ["weakness", "diplomacy over combat", "mindflayers", "timidity"],
    },
    "Halsin": {
        "class": "Druid",
        "subclass": "Circle of the Moon",
        "race": "Wood Elf",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["nature", "protecting innocents", "animals", "balance"],
        "dislikes": ["shadow curse", "hurting nature", "cruelty"],
    },
    "Jaheira": {
        "class": "Druid",
        "subclass": "Circle of the Land",
        "race": "Half-Elf",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["pragmatism", "protecting innocents", "experience", "Harper values"],
        "dislikes": ["recklessness", "cruelty", "undermining authority"],
    },
    "Minsc": {
        "class": "Ranger",
        "subclass": "Beast Master",
        "race": "Human",
        "approval_thresholds": {
            "hostile": -50,
            "disapproves": -1,
            "neutral": 0,
            "approves": 25,
            "strongly_approves": 60,
            "romance_unlock": 40,
        },
        "likes": ["heroism", "protecting innocents", "Boo", "butt-kicking for goodness"],
        "dislikes": ["evil", "cruelty", "harming innocents", "betrayal"],
    },
}


# --------------------------------------------------
# Estruturas de dados
# --------------------------------------------------

@dataclass
class Page:
    title: str
    category: str
    url: str
    content: str          # texto limpo
    sections: dict        # {titulo_secao: texto}
    companion_name: str = ""  # se for pagina de companion


@dataclass
class ApprovalEvent:
    companion: str
    action: str
    value: int            # +10, -5, etc
    act: int              # 1, 2 ou 3
    context: str = ""


# --------------------------------------------------
# Cliente da API MediaWiki
# --------------------------------------------------

class WikiClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_page_text(self, title: str) -> str | None:
        """Busca o texto wikitext de uma pagina."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        }
        try:
            r = self.session.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            pages = data.get("query", {}).get("pages", [])
            if not pages:
                return None
            page = pages[0]
            if "missing" in page:
                print(f"  [!] Pagina nao encontrada: {title}")
                return None
            return page["revisions"][0]["slots"]["main"]["content"]
        except Exception as e:
            print(f"  [!] Erro ao buscar {title}: {e}")
            return None

    def get_page_html(self, title: str) -> str | None:
        """Busca o HTML renderizado de uma pagina."""
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "formatversion": "2",
        }
        try:
            r = self.session.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                print(f"  [!] Erro API para {title}: {data['error']}")
                return None
            return data.get("parse", {}).get("text", "")
        except Exception as e:
            print(f"  [!] Erro ao buscar HTML {title}: {e}")
            return None

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Busca paginas pela query."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        try:
            r = self.session.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            return data.get("query", {}).get("search", [])
        except Exception as e:
            print(f"  [!] Erro na busca '{query}': {e}")
            return []


def resolve_redirect(wikitext: str, client: 'WikiClient') -> tuple[str, str]:
    """
    Check if wikitext is a redirect and resolve it.
    Returns (final_title, final_wikitext)
    """
    lines = wikitext.strip().split('\n')
    if lines and lines[0].strip().upper().startswith('#REDIRECT'):
        # Extract target from #REDIRECT [[target]]
        match = re.search(r'#REDIRECT\s*\[\[([^\]]+)\]\]', lines[0], re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            print(f"  -> Redirect to: {target}")
            # Fetch the target page
            target_wikitext = client.get_page_text(target)
            if target_wikitext:
                return target, target_wikitext
    return "", wikitext


# --------------------------------------------------
# Parser de conteudo
# --------------------------------------------------

def clean_wikitext(text: str) -> str:
    """Remove markup wikitext, deixa texto limpo."""
    # Remove templates {{...}}
    depth = 0
    result = []
    i = 0
    while i < len(text):
        if text[i:i+2] == "{{":
            depth += 1
            i += 2
        elif text[i:i+2] == "}}":
            depth = max(0, depth - 1)
            i += 2
        elif depth == 0:
            result.append(text[i])
            i += 1
        else:
            i += 1
    text = "".join(result)

    # Remove [[File:...]] e [[Image:...]]
    text = re.sub(r'\[\[(?:File|Image):[^\]]+\]\]', '', text, flags=re.IGNORECASE)

    # Converte [[link|texto]] -> texto, [[link]] -> link
    text = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', text)

    # Remove tags HTML
    text = re.sub(r'<[^>]+>', ' ', text)

    # Remove cabecalhos wikitext (== Titulo ==)
    text = re.sub(r'={2,}([^=]+)={2,}', r'\1', text)

    # Remove formatacao (bold, italic)
    text = re.sub(r"'{2,}", '', text)

    # Remove linhas de tabela
    text = re.sub(r'^\s*[|!].*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\|-.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\{[|].*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[|}].*$', '', text, flags=re.MULTILINE)

    # Limpa espacos multiplos e linhas em branco
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()


def extract_sections(wikitext: str) -> dict[str, str]:
    """Divide o wikitext em secoes pelo cabecalho."""
    sections = {}
    current_title = "intro"
    current_lines = []

    for line in wikitext.split("\n"):
        match = re.match(r'^(={2,})\s*(.+?)\s*\1$', line)
        if match:
            # Salva secao atual
            if current_lines:
                sections[current_title] = clean_wikitext("\n".join(current_lines))
            current_title = match.group(2).lower().strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_title] = clean_wikitext("\n".join(current_lines))

    return sections


def clean_action(action: str) -> str:
    """
    Cleans approval action text for readability.
    - Removes skill tags like [WISDOM], [PERSUASION]
    - Removes dice rolls like (DC 18)
    - Removes metadata like [verify]
    - Splits on ' OR ' and keeps first option
    - Cleans extra whitespace and quotes
    - Returns short, readable sentence
    """
    # Remove skill tags 
    action = re.sub(r'\[.*?\]', '', action)
    
    # Remove dice rolls (DC XX) or similar
    action = re.sub(r'\(DC \d+\)', '', action)
    
    # Remove [verify] or similar metadata
    action = re.sub(r'\[verify.*?\]', '', action, flags=re.IGNORECASE)
    
    # Split on ' OR ' and keep first part
    if ' OR ' in action:
        action = action.split(' OR ')[0]
    
    # Clean extra whitespace
    action = re.sub(r'\s+', ' ', action).strip()
    
    # Remove surrounding quotes
    action = action.strip('"\'')
    
    # Capitalize first letter
    if action:
        action = action[0].upper() + action[1:]
    
    return action

def extract_approval_from_html(html: str, act: int) -> list[ApprovalEvent]:
    """
    Extracts approval events from the HTML of an approval page.
    Parses only within div.mw-parser-output to avoid nav/sidebar.
    Uses section headers (h2/h3) to detect current companion.
    Extracts all approval values from each <li>, creates events for each.
    Cleans action text by removing values, filters short/generic actions.
    Deduplicates based on (companion, action, value, act).
    Filters out low-value events (|value| < 2).
    """
    soup = BeautifulSoup(html, "html.parser")
    parser_output = soup.find('div', class_='mw-parser-output')
    if not parser_output:
        return []

    events = []
    current_companion = None

    # Traverse elements in order
    for element in parser_output.find_all(['h2', 'h3', 'li'], recursive=True):
        if element.name in ['h2', 'h3']:
            # Check if header is a companion name
            header_text = element.get_text().strip()
            for comp in COMPANION_METADATA.keys():
                if comp.lower() in header_text.lower():
                    current_companion = comp
                    break
            else:
                current_companion = None
        elif element.name == 'li' and current_companion:
            text = element.get_text(" ", strip=True)
            # Find all approval values in the text
            value_matches = re.findall(r'([+-]\d+)', text)
            if not value_matches:
                continue

            # Clean action: remove all approval values and extra whitespace
            action = re.sub(r'[+-]\d+', '', text).strip()
            action = re.sub(r'\s+', ' ', action)
            # Remove trailing punctuation like *, :, etc.
            action = re.sub(r'[*:;.,\s]+$', '', action).strip()
            
            # Apply advanced cleaning
            action = clean_action(action)
            
            # Skip if action is too short, generic, or contains meta info
            if (len(action) < 15 or 
                action.lower() in ['attack.', 'help.', 'talk.', 'interact.', 'use item.', 'fight.', 'kill.'] or
                'roll' in action.lower() or 'check' in action.lower()):
                continue

            # Create event for each value found
            for val_str in value_matches:
                value = int(val_str)
                # Filter low-value noise
                if abs(value) < 2:
                    continue
                events.append(ApprovalEvent(
                    companion=current_companion,
                    action=action,
                    value=value,
                    act=act
                ))

    # Deduplicate using normalized action text
    seen = set()
    deduped_events = []
    for event in events:
        # Normalize for dedup: lowercase, strip, remove punctuation
        normalized = re.sub(r'[^\w\s]', '', event.action.lower()).strip()
        key = (event.companion, normalized, event.value, event.act)
        if key not in seen:
            seen.add(key)
            deduped_events.append(event)

    return deduped_events


# --------------------------------------------------
# Scraper principal
# --------------------------------------------------

def scrape_all(dry_run: bool = False) -> tuple[list[dict], list[dict]]:
    """
    Coleta todas as paginas configuradas.
    dry_run=True: apenas simula sem fazer requests reais.
    Retorna (pages, approval_events).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = WikiClient()
    pages = []
    approval_events = []

    total = sum(len(v) for v in PAGES_TO_SCRAPE.values())
    done = 0

    for category, titles in PAGES_TO_SCRAPE.items():
        print(f"\n[+] Categoria: {category} ({len(titles)} paginas)")

        for title in titles:
            done += 1
            print(f"  [{done}/{total}] {title}...", end=" ", flush=True)

            if dry_run:
                print("(dry run)")
                continue

            wikitext = client.get_page_text(title)
            if not wikitext:
                print("FALHOU")
                time.sleep(REQUEST_DELAY)
                continue

            # Resolve redirects
            redirect_title, wikitext = resolve_redirect(wikitext, client)
            if redirect_title:
                title = redirect_title  # Update title to the target

            sections = extract_sections(wikitext)
            full_text = clean_wikitext(wikitext)

            # Companion name
            companion_name = ""
            if category == "companions":
                companion_name = title

            # Extrai eventos de aprovacao das paginas de approval
            if category == "approval" and "/" in title:
                act_num = int(re.search(r'Act_(\w+)', title).group(1)
                               .replace("One", "1").replace("Two", "2").replace("Three", "3"))
                html = client.get_page_html(title)
                events = extract_approval_from_html(html, act_num)
                approval_events.extend(events)
                if events:
                    print(f"\n    -> {len(events)} eventos", end="")

            page = Page(
                title=title,
                category=category,
                url=f"{BASE_URL}/{title.replace(' ', '_')}",
                content=full_text[:5000],   # limita a 5k chars por pagina
                sections={k: v[:1000] for k, v in sections.items()},
                companion_name=companion_name,
            )
            pages.append(asdict(page))
            print("OK")

            time.sleep(REQUEST_DELAY)

    return pages, approval_events


def build_companion_documents() -> list[dict]:
    """
    Cria documentos estruturados por companion
    combinando metadata estatica + dados da wiki.
    Esses documentos vao para o OpenSearch.
    """
    docs = []
    for name, meta in COMPANION_METADATA.items():
        doc = {
            "id": f"companion_{name.lower().replace(' ', '_').replace(chr(39), '')}",
            "type": "companion",
            "title": name,
            "url": f"{BASE_URL}/{name.replace(' ', '_')}",
            "class": meta["class"],
            "subclass": meta["subclass"],
            "race": meta["race"],
            "likes": meta["likes"],
            "dislikes": meta["dislikes"],
            "approval_thresholds": meta["approval_thresholds"],
            "searchable_text": (
                f"{name} is a {meta['race']} {meta['class']} ({meta['subclass']}). "
                f"They like: {', '.join(meta['likes'])}. "
                f"They dislike: {', '.join(meta['dislikes'])}. "
                f"They leave the party permanently if approval drops below "
                f"{meta['approval_thresholds']['hostile']}."
            ),
        }
        docs.append(doc)
    return docs


def save_data(pages: list[dict], approval_events: list[dict], companions: list[dict]):
    """Salva todos os dados coletados em JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pages_path = OUTPUT_DIR / "pages.json"
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, indent=2, ensure_ascii=False)
    print(f"\n[+] {len(pages)} paginas salvas em {pages_path}")

    events_path = OUTPUT_DIR / "approval_events.json"
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(approval_events, f, indent=2, ensure_ascii=False)
    print(f"[+] {len(approval_events)} eventos de aprovacao salvos em {events_path}")

    companions_path = OUTPUT_DIR / "companions.json"
    with open(companions_path, "w", encoding="utf-8") as f:
        json.dump(companions, f, indent=2, ensure_ascii=False)
    print(f"[+] {len(companions)} companions salvos em {companions_path}")


def generate_sample_data():
    """
    Gera dados de amostra sem precisar de internet.
    Util para testar o pipeline localmente.
    """
    print("[+] Gerando dados de amostra (sem internet)...")

    companions = build_companion_documents()

    # Paginas de amostra
    pages = []
    for comp_name, meta in COMPANION_METADATA.items():
        page = {
            "title": comp_name,
            "category": "companions",
            "url": f"{BASE_URL}/{comp_name.replace(' ', '_')}",
            "content": (
                f"{comp_name} is a {meta['race']} {meta['class']} "
                f"({meta['subclass']}) companion in Baldur's Gate 3. "
                f"They approve of: {', '.join(meta['likes'])}. "
                f"They disapprove of: {', '.join(meta['dislikes'])}."
            ),
            "sections": {
                "overview": f"{comp_name} joins the party during Act 1.",
                "approval": (
                    f"{comp_name} approves of actions that align with their values. "
                    f"They like {', '.join(meta['likes'][:2])} and dislike "
                    f"{', '.join(meta['dislikes'][:2])}."
                ),
            },
            "companion_name": comp_name,
        }
        pages.append(page)

    # Add sample lore pages
    lore_pages = [
        {
            "title": "Mind Flayer",
            "category": "lore",
            "url": f"{BASE_URL}/Mind_Flayer",
            "content": (
                "Mind flayers are aberrations known as illithids. They are psionic creatures that consume brains and are central to the main plot of Baldur's Gate 3. "
                "Mind flayers reproduce by implanting tadpoles into the brains of other creatures, transforming them into mind flayers over time. "
                "They possess powerful psionic abilities and are highly intelligent."
            ),
            "sections": {
                "biology": "Mind flayers have octopus-like heads with four tentacles. They feed on brains to sustain themselves.",
                "society": "Mind flayers live in underground cities and form colonies ruled by elder brains.",
            },
        },
        {
            "title": "Illithid",
            "category": "lore",
            "url": f"{BASE_URL}/Illithid",
            "content": "Illithid is another name for mind flayer. These creatures are central to the plot of Baldur's Gate 3, infecting characters with tadpoles.",
            "sections": {"biology": "Illithids have tentacled heads and psionic powers."},
        },
        {
            "title": "Githyanki",
            "category": "lore",
            "url": f"{BASE_URL}/Githyanki",
            "content": "Githyanki are a race of humanoids who escaped illithid slavery. They are known for their silver swords and hatred of mind flayers.",
            "sections": {"history": "Githyanki history involves rebellion against illithids."},
        },
        {
            "title": "Tadpole",
            "category": "lore",
            "url": f"{BASE_URL}/Tadpole",
            "content": "Tadpoles are larval illithids implanted in brains. They grant psionic powers but lead to ceremorphosis if not removed.",
            "sections": {"effects": "Tadpoles cause parasitic infection."},
        },
        {
            "title": "Ceremorphosis",
            "category": "lore",
            "url": f"{BASE_URL}/Ceremorphosis",
            "content": "Ceremorphosis is the transformation into a mind flayer caused by illithid tadpoles. It can be prevented by removing the tadpole.",
            "sections": {"process": "The transformation takes time and is irreversible without intervention."},
        },
        {
            "title": "Absolute",
            "category": "lore",
            "url": f"{BASE_URL}/Absolute",
            "content": "The Absolute is a false god created by mind flayers to control the Sword Coast. It is worshipped by various cults.",
            "sections": {"worship": "Followers of the Absolute include goblins and other creatures."},
        },
        {
            "title": "Netherbrain",
            "category": "lore",
            "url": f"{BASE_URL}/Netherbrain",
            "content": "The Netherbrain is a massive mind flayer brain that serves as the final boss in Baldur's Gate 3. It controls the Absolute.",
            "sections": {"battle": "Fighting the Netherbrain is the climax of the game."},
        },
        {
            "title": "Githzerai",
            "category": "lore",
            "url": f"{BASE_URL}/Githzerai",
            "content": "Githzerai are monk-like gith who live in Limbo. They are more peaceful than githyanki but still hate illithids.",
            "sections": {"lifestyle": "Githzerai practice meditation and psionic disciplines."},
        },
    ]
    pages.extend(lore_pages)

    # Eventos de aprovacao de amostra
    sample_events = [
        {"companion": "Shadowheart", "action": "Help an injured stranger", "value": 5, "act": 1, "context": ""},
        {"companion": "Shadowheart", "action": "Disrespect Shar", "value": -10, "act": 1, "context": ""},
        {"companion": "Astarion", "action": "Show cruelty to an enemy", "value": 5, "act": 1, "context": ""},
        {"companion": "Astarion", "action": "Give away gold for free", "value": -5, "act": 1, "context": ""},
        {"companion": "Karlach", "action": "Defeat a devil", "value": 10, "act": 1, "context": ""},
        {"companion": "Karlach", "action": "Show cowardice", "value": -10, "act": 1, "context": ""},
        {"companion": "Gale", "action": "Share knowledge or discuss magic", "value": 5, "act": 1, "context": ""},
        {"companion": "Gale", "action": "Destroy a magic item", "value": -10, "act": 1, "context": ""},
        {"companion": "Wyll", "action": "Protect an innocent", "value": 10, "act": 1, "context": ""},
        {"companion": "Wyll", "action": "Make a deal with a devil", "value": -15, "act": 1, "context": ""},
    ]

    save_data(pages, sample_events, companions)
    return pages, sample_events, companions


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    import sys

    sample_mode = "--sample" in sys.argv
    dry_run     = "--dry-run" in sys.argv

    if sample_mode:
        generate_sample_data()
    else:
        print("[+] Iniciando scraping da bg3.wiki...")
        print("    Use --sample para gerar dados de teste sem internet")
        print("    Use --dry-run para listar paginas sem fazer requests")
        print()

        pages, events = scrape_all(dry_run=dry_run)
        companions    = build_companion_documents()

        if not dry_run:
            save_data(pages, [asdict(e) for e in events], companions)

    print("\n[+] Concluido.")