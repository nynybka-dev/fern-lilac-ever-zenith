#!/usr/bin/env python3
"""Rebuild the Dagestan accommodation registry: parse Excel, check sites,
cluster duplicates, drop junk/outdated listings, emit JSON/CSV/XLSX."""

from __future__ import annotations

import csv
import glob
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

SRC = glob.glob("/workspace/attachments/*.xlsx")[0]
SITE_CHECK = "/workspace/data/site_check.json"
OUT_DIR = "/workspace/src/data"
PUBLIC_DIR = "/workspace/public"

GENERIC_NAMES = {
    "гостевой дом",
    "гостьовой дом",
    "гостиница",
    "отель",
    "hotel",
    "house",
    "guest house",
    "gueste house",
    "дом у моря",
    "дома у моря",
    "домик у моря",
    "дом отдыха",
    "база отдыха",
    "база, дом отдыха",
    "хостел",
    "hostel",
    "кемпинг",
    "глэмпинг",
    "берег",
    "dacha",
    "дача",
    "уют",
    "частный дом",
    "жилье посуточно",
    "жильё посуточно",
    "апартаменты",
    "квартира",
    "суточно. про",
    "суточно про",
}

TYPE_STOP = {
    "гостиница",
    "отель",
    "гостевой",
    "дом",
    "отдыха",
    "база",
    "хостел",
    "кемпинг",
    "глэмпинг",
    "санаторий",
    "hotel",
    "house",
    "guest",
    "hostel",
    "villa",
    "apart",
    "apartment",
    "resort",
    "spa",
}

CITIES = [
    ("дербентский район", "Дербентский район"),
    ("карабудахкентский район", "Карабудахкентский район"),
    ("каякентский район", "Каякентский район"),
    ("гунибский район", "Гунибский район"),
    ("хунзахский район", "Хунзахский район"),
    ("гергебильский район", "Гергебильский район"),
    ("шамильский район", "Шамильский район"),
    ("унцукульский район", "Унцукульский район"),
    ("магарамкентский район", "Магарамкентский район"),
    ("казбековский район", "Казбековский район"),
    ("кизилюртовский район", "Кизилюртовский район"),
    ("хасавюртовский район", "Хасавюртовский район"),
    ("буйнакский район", "Буйнакский район"),
    ("табасаранский район", "Табасаранский район"),
    ("докузпаринский район", "Докузпаринский район"),
    ("кулинский район", "Кулинский район"),
    ("левашинский район", "Левашинский район"),
    ("новолакский район", "Новолакский район"),
    ("кумторкалинский район", "Кумторкалинский район"),
    ("ахтынский район", "Ахтынский район"),
    ("ботлихский район", "Ботлихский район"),
    ("рутульский район", "Рутульский район"),
    ("тляратинский район", "Тляратинский район"),
    ("цумадинский район", "Цумадинский район"),
    ("цунтинский район", "Цунтинский район"),
    ("дахадаевский район", "Дахадаевский район"),
    ("кайтагский район", "Кайтагский район"),
    ("курахский район", "Курахский район"),
    ("ахвахский район", "Ахвахский район"),
    ("гумбетовский район", "Гумбетовский район"),
    ("тарумовский район", "Тарумовский район"),
    ("кизлярский район", "Кизлярский район"),
    ("сулейман-стальский район", "Сулейман-Стальский район"),
    ("дагестанские огни", "Дагестанские Огни"),
    ("южно-сухокумск", "Южно-Сухокумск"),
    ("махачкала", "Махачкала"),
    ("дербент", "Дербент"),
    ("избербаш", "Избербаш"),
    ("каспийск", "Каспийск"),
    ("хасавюрт", "Хасавюрт"),
    ("кизляр", "Кизляр"),
    ("кизилюрт", "Кизилюрт"),
    ("буйнакск", "Буйнакск"),
    ("гуниб", "Гуниб"),
    ("хунзах", "Хунзах"),
    ("ахты", "Ахты"),
    ("тарумовка", "Тарумовка"),
]

MULTI = [
    ("sch", "щ"),
    ("shch", "щ"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("zh", "ж"),
    ("kh", "х"),
    ("ts", "ц"),
    ("ch", "ч"),
    ("sh", "ш"),
    ("eh", "э"),
]
SINGLE = str.maketrans(
    {
        "a": "а",
        "b": "б",
        "c": "к",
        "d": "д",
        "e": "е",
        "f": "ф",
        "g": "г",
        "h": "х",
        "i": "и",
        "j": "дж",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "q": "к",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "v": "в",
        "w": "в",
        "x": "кс",
        "y": "и",
        "z": "з",
    }
)

AGGREGATOR_HOSTS = {
    "sutochno.ru",
    "ostrovok.ru",
    "booking.com",
    "avito.ru",
    "yandex.ru",
    "yandex.com",
    "2gis.ru",
    "tripadvisor.ru",
    "tripadvisor.com",
    "dimpoisk.ru",
    "fooby.ru",
    "emergingtravel.com",
    "tvil.ru",
    "sutki.ru",
    "cian.ru",
    "domclick.ru",
    "youla.ru",
    "vk.com",
    "vk.ru",
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("ё", "е").replace("Ё", "е")
    return s.lower().strip()


def only_alnum(s: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "", fold(s))


def translit_lat(s: str) -> str:
    s = fold(s)
    for a, b in MULTI:
        s = s.replace(a, b)
    out = []
    for ch in s:
        out.append(ch.translate(SINGLE) if "a" <= ch <= "z" else ch)
    return "".join(out)


def core_name(name: str) -> str:
    s = fold(name)
    s = s.replace("«", " ").replace("»", " ").replace('"', " ").replace("'", " ")
    s = re.sub(r"[_./\\|]+", " ", s)
    s = re.sub(r"\b(ип|ооо|гостиничный комплекс|гостевой дом|база отдыха|дом отдыха|коттеджный отель|мини отель|мини-отель)\b", " ", s)
    s = re.sub(r"\b(" + "|".join(TYPE_STOP) + r")\b", " ", s)
    s = re.sub(r"[^a-zа-я0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    t = translit_lat(s)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_generic_name(name: str) -> bool:
    n = fold(name).strip(" .!?-_")
    n = re.sub(r"\s+", " ", n)
    if n in GENERIC_NAMES:
        return True
    core = core_name(name)
    if not core or len(core) < 3:
        return True
    if re.fullmatch(r"\d+", core):
        return True
    return False


def phones_of(s: str) -> list[str]:
    digits = re.sub(r"\D", "", s or "")
    found = re.findall(r"7\d{10}", digits)
    extra = re.findall(r"(?<!\d)9\d{9}(?!\d)", digits)
    for e in extra:
        found.append("7" + e)
    out = []
    for p in found:
        if p not in out:
            out.append(p)
    return out


def norm_host(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    try:
        host = (urlsplit(url).hostname or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def sites_of(s: str) -> list[str]:
    if not s:
        return []
    out = []
    for part in re.split(r"[\s,;]+", s):
        part = part.strip().rstrip(".")
        if not part:
            continue
        if "." not in part and "://" not in part:
            continue
        h = norm_host(part)
        if h and h not in out:
            out.append(h)
    return out


def is_aggregator_host(h: str) -> bool:
    h = h.lower()
    return any(h == a or h.endswith("." + a) for a in AGGREGATOR_HOSTS)


def extract_locality(address: str) -> str:
    a = fold(address)
    for key, label in CITIES:
        if key in a:
            return label
    m = re.search(r"([а-я\-]+ский район)", a)
    if m:
        return m.group(1).title().replace("Ский", "ский")
    m = re.search(r"селе?\s+([а-я\-]+)", a)
    if m:
        return "с. " + m.group(1).title()
    return "Дагестан"


def extract_street_house(address: str) -> tuple[str, str]:
    a = fold(address)
    a = a.replace("улица", "ул").replace("проспект", "пр-кт").replace("переулок", "пер")
    house = ""
    m = re.search(r"(?:д\.?\s*|дом\s+|зд\.?\s*|з/у\s*)(\d+[а-яa-z]?(?:/\d+[а-яa-z]?)?)", a)
    if m:
        house = m.group(1)
    else:
        m = re.search(r",\s*(\d+[а-яa-z]?(?:/\d+[а-яa-z]?)?)\s*$", a)
        if m:
            house = m.group(1)
        else:
            m = re.search(r"(?:ул|улица|пр-кт|пер)\.?\s+[а-я0-9\-\s.]{2,40}?\s+(\d+[а-яa-z]?(?:/\d+)?)", a)
            if m:
                house = m.group(1)
    street = ""
    m = re.search(
        r"(ул\.?\s+|улица\s+|пр-кт\s+|проспект\s+|пер\.?\s+|переулок\s+|шоссе\s+|набережная\s+)([а-я0-9\-\s.]+?)(?:,|$|д[\s.]|дом)",
        a,
    )
    if m:
        street = re.sub(r"\s+", " ", m.group(2)).strip(" .")
    if not street:
        m = re.search(r"(микрорайон|мкр\.?)\s+([а-я0-9\-\s]+)", a)
        if m:
            street = "мкр " + re.sub(r"\s+", " ", m.group(2)).strip(" .")
    return street, house


def addr_key(address: str) -> str:
    loc = fold(extract_locality(address))
    street, house = extract_street_house(address)
    return f"{loc}|{street}|{house}"


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        ratio = min(len(a), len(b)) / max(len(a), len(b))
        return 0.82 + 0.18 * ratio if min(len(a), len(b)) >= 4 else 0.6 * ratio
    return SequenceMatcher(None, a, b).ratio()


JUNK_PATTERNS = [
    re.compile(r"\bflat\b", re.I),
    re.compile(r"квартир", re.I),
    re.compile(r"посуточн", re.I),
    re.compile(r"^суточно", re.I),
    re.compile(r"flats on ", re.I),
    re.compile(r"home comfort", re.I),
    re.compile(r"how are you at home", re.I),
    re.compile(r"^\d+-kh\b", re.I),
    re.compile(r"komnatnaya", re.I),
    re.compile(r"^улица\b", re.I),
    re.compile(r"waterbury", re.I),
    re.compile(r"courtyard", re.I),
    re.compile(r"на улице", re.I),
    re.compile(r"^частный дом\b", re.I),
    re.compile(r"^частный дом ", re.I),
]


def is_junk_listing(rec: dict) -> str | None:
    name = rec["name"]
    n = fold(name)
    src = fold(rec.get("srcType") or "")
    if "жильё посуточно" in src or "жилье посуточно" in src:
        if is_generic_name(name) or any(p.search(name) for p in JUNK_PATTERNS):
            return "Объявление жилья посуточно / агрегаторская квартира, не самостоятельное средство размещения"
    for p in JUNK_PATTERNS:
        if p.search(name):
            if n.startswith("частный дом") and rec.get("site") and not any(
                is_aggregator_host(h) for h in rec.get("hosts") or []
            ):
                # branded private house with own site — keep unless other junk
                if len(core_name(name)) >= 4 and not re.search(r"flat|квартир|waterbury", n):
                    continue
            return "Агрегаторская или частная квартира / автосгенерированное объявление"
    if n in {"суточно. про", "суточно про"}:
        return "Площадка «Суточно.про», не объект размещения"
    if "waterbury" in n or "courtyard waterbury" in n:
        return "Ошибочная запись (иностранный объект в исходной выгрузке)"
    loc = extract_locality(rec["address"])
    street, house = extract_street_house(rec["address"])
    own_site = [h for h in (rec.get("hosts") or []) if not is_aggregator_host(h)]
    if is_generic_name(name) and not rec["phone"] and not own_site:
        return "Типовое название без телефона и собственного сайта — нельзя подтвердить в открытых источниках"
    if is_generic_name(name) and not rec["phone"] and not house:
        return "Нет названия, контактов и точного адреса — объект не идентифицируется"
    if fold(rec["address"]) in {"республика дагестан", "дагестан", ""} and not rec["phone"] and not rec["site"]:
        return "Нет адреса и контактов"
    if loc == "Дагестан" and not rec["phone"] and not own_site and not house:
        return "Адрес не детализирован, контактов нет"
    return None


def site_status_for(rec: dict, checks: dict) -> str:
    raw = rec.get("site") or ""
    if not raw:
        return "none"
    best = "none"
    for part in re.split(r"[\s,;]+", raw):
        part = part.strip().rstrip(".")
        if not part:
            continue
        variants = [part]
        if not part.startswith("http"):
            variants = ["https://" + part, "http://" + part]
        for v in variants:
            info = checks.get(v)
            if not info:
                # try prefix match
                for k, val in checks.items():
                    if k.rstrip("/") == v.rstrip("/") or k.replace("http://", "https://") == v:
                        info = val
                        break
            if not info:
                continue
            code = info.get("code") or 0
            if 200 <= code < 400 or code in (401, 402, 403, 405, 418, 429, 500, 502, 503, 202):
                return "live"
            if code == 404:
                best = "dead"
            elif best == "none":
                best = "error"
    return best


class UF:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            self.p[ra] = rb
        elif self.r[ra] > self.r[rb]:
            self.p[rb] = ra
        else:
            self.p[rb] = ra
            self.r[ra] += 1


def score(rec: dict) -> tuple:
    confirmed = 1 if rec["classResult"].startswith("Классификация подтверждена") else 0
    has_reg = 1 if rec["regNum"] else 0
    live = 1 if rec.get("web") == "live" else 0
    phone = 1 if rec["phone"] else 0
    site = 1 if rec["site"] else 0
    generic = 0 if is_generic_name(rec["name"]) else 1
    return (confirmed, has_reg, live, generic, phone, site, len(rec["address"]), -rec["id"])


def load_rows() -> list[dict]:
    wb = load_workbook(SRC, data_only=True)
    ws = wb["Реестр 2125"]
    rows = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        if not row or row[0] is None:
            continue

        def s(i: int) -> str:
            if i >= len(row) or row[i] is None:
                return ""
            return str(row[i]).strip()

        rec = {
            "id": int(row[0]) if str(row[0]).isdigit() else row[0],
            "name": s(2),
            "address": s(3),
            "phone": s(4),
            "site": s(5),
            "srcType": s(6),
            "classResult": s(7),
            "regName": s(8),
            "regNum": s(9),
            "regStatus": s(10),
            "inn": s(11),
            "ogrn": s(12),
            "regType": s(13),
            "regAddress": s(14),
            "reason": s(15),
        }
        rec["phones"] = phones_of(rec["phone"])
        rec["hosts"] = sites_of(rec["site"])
        rec["core"] = core_name(rec["name"])
        rec["locality"] = extract_locality(rec["address"])
        rec["street"], rec["house"] = extract_street_house(rec["address"])
        rec["addrKey"] = addr_key(rec["address"])
        rec["generic"] = is_generic_name(rec["name"])
        rec["confirmed"] = rec["classResult"].startswith("Классификация подтверждена")
        rows.append(rec)
    return rows


def cluster(rows: list[dict]) -> UF:
    n = len(rows)
    uf = UF(n)
    by_reg: dict[str, list[int]] = defaultdict(list)
    by_phone: dict[str, list[int]] = defaultdict(list)
    by_host: dict[str, list[int]] = defaultdict(list)
    by_addr: dict[str, list[int]] = defaultdict(list)
    by_loc_core: dict[str, list[int]] = defaultdict(list)

    for i, r in enumerate(rows):
        if r["regNum"]:
            by_reg[r["regNum"]].append(i)
        for p in r["phones"]:
            by_phone[p].append(i)
        for h in r["hosts"]:
            if not is_aggregator_host(h):
                by_host[h].append(i)
        if r["house"] and r["street"]:
            by_addr[r["addrKey"]].append(i)
        if r["core"]:
            by_loc_core[fold(r["locality"]) + "|" + r["core"]].append(i)

    def same_place(a: dict, b: dict) -> bool:
        if a["locality"] != b["locality"]:
            return False
        if a["house"] and b["house"] and a["house"] == b["house"]:
            if a["street"] and b["street"] and sim(a["street"], b["street"]) >= 0.72:
                return True
            if not a["street"] or not b["street"]:
                return True
        return False

    for idxs in by_reg.values():
        for j in idxs[1:]:
            uf.union(idxs[0], j)

    for idxs in by_addr.values():
        if len(idxs) < 2:
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                a, b = rows[idxs[x]], rows[idxs[y]]
                if a["generic"] and b["generic"]:
                    uf.union(idxs[x], idxs[y])
                elif sim(a["core"], b["core"]) >= 0.55 or a["generic"] or b["generic"]:
                    uf.union(idxs[x], idxs[y])
                elif a["phones"] and b["phones"] and set(a["phones"]) & set(b["phones"]):
                    uf.union(idxs[x], idxs[y])

    for idxs in by_phone.values():
        if len(idxs) < 2:
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                a, b = rows[idxs[x]], rows[idxs[y]]
                a_conf = a.get("confirmed") and a.get("regNum")
                b_conf = b.get("confirmed") and b.get("regNum")
                if a_conf and b_conf and a["regNum"] != b["regNum"]:
                    continue
                if a["locality"] == b["locality"] or same_place(a, b):
                    uf.union(idxs[x], idxs[y])
                    continue
                if sim(a["core"], b["core"]) >= 0.82:
                    uf.union(idxs[x], idxs[y])

    for idxs in by_host.values():
        if not (2 <= len(idxs) <= 8):
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                a, b = rows[idxs[x]], rows[idxs[y]]
                if sim(a["core"], b["core"]) >= 0.68 or same_place(a, b):
                    uf.union(idxs[x], idxs[y])

    # exact core + locality for non-generic branded names
    for idxs in by_loc_core.values():
        if len(idxs) < 2:
            continue
        sample = rows[idxs[0]]
        if len(sample["core"]) < 3:
            continue
        if len(idxs) > 6 and not sample["generic"]:
            # likely a chain of cottages — merge only missing/same house
            for x in range(len(idxs)):
                for y in range(x + 1, len(idxs)):
                    a, b = rows[idxs[x]], rows[idxs[y]]
                    if not a["house"] or not b["house"] or a["house"] == b["house"]:
                        uf.union(idxs[x], idxs[y])
            continue
        houses = {rows[i]["house"] for i in idxs if rows[i]["house"]}
        if len(houses) <= 1:
            for j in idxs[1:]:
                uf.union(idxs[0], j)
        else:
            by_house: dict[str, list[int]] = defaultdict(list)
            for i in idxs:
                by_house[rows[i]["house"] or ""].append(i)
            for hi, group in by_house.items():
                if not hi:
                    continue
                for j in group[1:]:
                    uf.union(group[0], j)

    return uf


def merge_group(members: list[dict]) -> dict:
    members = sorted(members, key=score, reverse=True)
    base = dict(members[0])
    phones, hosts, ids = [], [], []
    names = []
    for m in members:
        ids.append(m["id"])
        names.append(m["name"])
        for p in m["phones"]:
            if p not in phones:
                phones.append(p)
        for h in m["hosts"]:
            if h not in hosts:
                hosts.append(h)
        if not base["phone"] and m["phone"]:
            base["phone"] = m["phone"]
        if not base["site"] and m["site"]:
            base["site"] = m["site"]
        if m["confirmed"]:
            base["confirmed"] = True
            base["classResult"] = "Классификация подтверждена"
            for k in ("regName", "regNum", "regStatus", "inn", "ogrn", "regType", "regAddress", "reason"):
                if m.get(k):
                    base[k] = m[k]
        if len(m["address"]) > len(base["address"]):
            base["address"] = m["address"]
            base["locality"] = m["locality"]
            base["street"], base["house"] = m["street"], m["house"]
    base["phones"] = phones
    base["hosts"] = hosts
    base["mergedIds"] = ids
    base["mergedNames"] = names
    base["dupCount"] = len(members)
    if phones and not base["phone"]:
        base["phone"] = ", ".join("+7 (" + p[1:4] + ") " + p[4:7] + "-" + p[7:9] + "-" + p[9:] for p in phones)
    return base


def classify_web(rec: dict, checks: dict) -> str:
    st = site_status_for(rec, checks)
    rec["web"] = st
    return st


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    checks = {}
    if os.path.exists(SITE_CHECK):
        with open(SITE_CHECK) as f:
            checks = json.load(f)

    rows = load_rows()
    for r in rows:
        classify_web(r, checks)

    junk: list[dict] = []
    work: list[dict] = []
    for r in rows:
        reason = is_junk_listing(r)
        if reason:
            d = dict(r)
            d["removeKind"] = "outdated"
            d["removeReason"] = reason
            junk.append(d)
        else:
            work.append(r)

    uf = cluster(work)
    groups: dict[int, list[dict]] = defaultdict(list)
    for i, r in enumerate(work):
        groups[uf.find(i)].append(r)

    kept: list[dict] = []
    dups: list[dict] = []
    for g in groups.values():
        if len(g) == 1:
            rec = dict(g[0])
            rec["mergedIds"] = [rec["id"]]
            rec["mergedNames"] = [rec["name"]]
            rec["dupCount"] = 1
            kept.append(rec)
            continue
        canon = merge_group(g)
        kept.append(canon)
        canon_id = canon["id"]
        for m in g:
            if m["id"] == canon_id:
                continue
            d = dict(m)
            d["removeKind"] = "duplicate"
            d["removeReason"] = f"Дубль объекта «{canon['name']}» (исх. № {canon_id})"
            d["canonicalId"] = canon_id
            dups.append(d)

    # Second pass: dead unique website + no phone + not confirmed
    final_kept = []
    extra_out = []
    for r in kept:
        if (
            not r["confirmed"]
            and r.get("web") == "dead"
            and not r["phones"]
            and (not r["hosts"] or all(is_aggregator_host(h) for h in r["hosts"]))
        ):
            d = dict(r)
            d["removeKind"] = "outdated"
            d["removeReason"] = "Сайт не открывается, телефона нет — запись выглядит неактуальной"
            extra_out.append(d)
            continue
        # weak leftover: generic name, no phone, no live site
        if (
            not r["confirmed"]
            and r["generic"]
            and not r["phones"]
            and r.get("web") in ("none", "dead", "error")
            and not r["house"]
        ):
            d = dict(r)
            d["removeKind"] = "outdated"
            d["removeReason"] = "Типовое название без контактов и точного адреса"
            extra_out.append(d)
            continue
        final_kept.append(r)

    final_kept.sort(key=lambda r: (0 if r["confirmed"] else 1, r["locality"], fold(r["name"]), r["id"]))
    removed = junk + dups + extra_out
    removed.sort(key=lambda r: (r["removeKind"], r["id"]))

    def slim(r: dict, extra: bool = False) -> dict:
        out = {
            "id": r["id"],
            "name": r["name"],
            "locality": r["locality"],
            "address": r["address"],
            "phone": r["phone"],
            "site": r["site"],
            "type": r["srcType"],
            "classified": bool(r.get("confirmed")),
            "regNum": r.get("regNum") or "",
            "regName": r.get("regName") or "",
            "regStatus": r.get("regStatus") or "",
            "regType": r.get("regType") or "",
            "inn": r.get("inn") or "",
            "ogrn": r.get("ogrn") or "",
            "web": r.get("web") or "none",
            "dupCount": r.get("dupCount") or 1,
            "mergedIds": r.get("mergedIds") or [r["id"]],
        }
        if extra:
            out["removeKind"] = r.get("removeKind")
            out["removeReason"] = r.get("removeReason")
            out["canonicalId"] = r.get("canonicalId")
        return out

    kept_out = [slim(r) for r in final_kept]
    removed_out = [slim(r, True) for r in removed]

    type_counter = Counter(r["type"] or "Не указан" for r in kept_out)
    loc_counter = Counter(r["locality"] for r in kept_out)
    web_counter = Counter(r["web"] for r in kept_out)
    classified_n = sum(1 for r in kept_out if r["classified"])
    dup_removed = sum(1 for r in removed_out if r["removeKind"] == "duplicate")
    out_removed = sum(1 for r in removed_out if r["removeKind"] == "outdated")

    meta = {
        "sourceFile": os.path.basename(SRC),
        "sourceCount": len(rows),
        "keptCount": len(kept_out),
        "removedCount": len(removed_out),
        "duplicateRemoved": dup_removed,
        "outdatedRemoved": out_removed,
        "classifiedCount": classified_n,
        "unclassifiedCount": len(kept_out) - classified_n,
        "fgisActiveDump": 479,
        "fgisDumpDate": "2026-09-23",
        "mintourismOperatingJan2026": 892,
        "classifiedOfficialMay2026": 403,
        "sitesChecked": len(checks),
        "sitesLive": sum(
            1
            for v in checks.values()
            if 200 <= (v.get("code") or 0) < 400
            or (v.get("code") or 0) in (401, 402, 403, 405, 418, 429, 500, 502, 503, 202)
        ),
        "typeBreakdown": [{"type": k, "count": v} for k, v in type_counter.most_common()],
        "localityBreakdown": [{"locality": k, "count": v} for k, v in loc_counter.most_common()],
        "webBreakdown": dict(web_counter),
        "updatedAt": "2026-09-27",
        "methodology": [
            "Исходный перечень — 2125 объектов из сверки с выгрузкой ФГИС «Гостеприимство» от 23.09.2026 (479 действующих записей по Дагестану).",
            "Проверены 403 уникальных сайта объектов HTTP-запросом (доступность страницы).",
            "Сверены открытые источники: ФГИС «Гостеприимство», Минтуризм РД (892 коллективных средства размещения на 02.01.2026; 403 классифицированных на 19.05.2026), 2ГИС (1079 карточек «гостиница» по Махачкале и окрестностям).",
            "Дубли объединялись по номеру записи ФГИС, совпадению телефона и названия, совпадению сайта и названия, точному адресу (населённый пункт + улица + дом).",
            "Сняты агрегаторские квартиры, автоимена вроде Flat / Суточно.Про, ошибочные иностранные записи, безымянные пины без контактов и адреса, объекты с мёртвым сайтом без телефона.",
            "Сохранены самостоятельные объекты с уникальным адресом или контактами, в том числе без подтверждённой классификации. Сети домов с разными адресами не схлопывались в одну запись.",
        ],
    }

    with open(os.path.join(OUT_DIR, "kept.json"), "w", encoding="utf-8") as f:
        json.dump(kept_out, f, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "removed.json"), "w", encoding="utf-8") as f:
        json.dump(removed_out, f, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    def write_csv(path: str, items: list[dict], removed: bool = False) -> None:
        fields = [
            "id",
            "name",
            "locality",
            "address",
            "phone",
            "site",
            "type",
            "classified",
            "regNum",
            "regName",
            "regStatus",
            "inn",
            "ogrn",
            "web",
            "dupCount",
        ]
        if removed:
            fields += ["removeKind", "removeReason", "canonicalId"]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for it in items:
                row = dict(it)
                row["classified"] = "да" if it.get("classified") else "нет"
                w.writerow(row)

    write_csv(os.path.join(PUBLIC_DIR, "reestr-aktualnyi.csv"), kept_out)
    write_csv(os.path.join(PUBLIC_DIR, "reestr-snyatye.csv"), removed_out, True)

    def write_xlsx() -> None:
        wb = Workbook()
        header_font = Font(bold=True, color="FFFFFFFF", name="Calibri")
        header_fill = PatternFill("solid", fgColor="0D4F4B")
        thin = Border(
            left=Side(style="thin", color="D9D4C8"),
            right=Side(style="thin", color="D9D4C8"),
            top=Side(style="thin", color="D9D4C8"),
            bottom=Side(style="thin", color="D9D4C8"),
        )
        wrap = Alignment(wrap_text=True, vertical="top")

        def paint(ws, headers, data, cols):
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            for row in data:
                ws.append(row)
                for cell in ws[ws.max_row]:
                    cell.alignment = wrap
                    cell.border = thin
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
            ws.freeze_panes = "A2"
            for i, w in enumerate(cols, 1):
                ws.column_dimensions[get_column_letter(i)].width = w
            ws.row_dimensions[1].height = 22

        ws0 = wb.active
        ws0.title = "Сводка"
        ws0["A1"] = "Актуализированный реестр средств размещения Республики Дагестан"
        ws0["A1"].font = Font(bold=True, size=16, color="0D4F4B")
        ws0.merge_cells("A1:B1")
        summary = [
            ("Дата актуализации", "27 сентября 2026"),
            ("Было в исходном перечне", meta["sourceCount"]),
            ("Осталось актуальных объектов", meta["keptCount"]),
            ("Снято как дубли", meta["duplicateRemoved"]),
            ("Снято как устаревшие / не объекты", meta["outdatedRemoved"]),
            ("Классификация ФГИС подтверждена", meta["classifiedCount"]),
            ("Классификация не подтверждена", meta["unclassifiedCount"]),
            ("Действующих записей в выгрузке ФГИС (23.09.2026)", 479),
            ("Классифицированных по Минтуризму РД (19.05.2026)", 403),
            ("Коллективных средств размещения по Минтуризму РД (02.01.2026)", 892),
        ]
        r = 3
        for k, v in summary:
            ws0[f"A{r}"] = k
            ws0[f"B{r}"] = v
            r += 1
        r += 1
        ws0[f"A{r}"] = "Методика"
        ws0[f"A{r}"].font = Font(bold=True)
        r += 1
        for line in meta["methodology"]:
            ws0[f"A{r}"] = line
            ws0.merge_cells(f"A{r}:F{r}")
            ws0[f"A{r}"].alignment = Alignment(wrap_text=True)
            ws0.row_dimensions[r].height = 36
            r += 1
        ws0.column_dimensions["A"].width = 64
        ws0.column_dimensions["B"].width = 22

        ws1 = wb.create_sheet("Актуальные")
        paint(
            ws1,
            [
                "№ исх.",
                "Наименование",
                "Населённый пункт",
                "Адрес",
                "Телефон",
                "Сайт",
                "Тип",
                "Классификация",
                "№ ФГИС",
                "Наименование в ФГИС",
                "ИНН",
                "Сайт (проверка)",
                "Слито записей",
            ],
            [
                [
                    r["id"],
                    r["name"],
                    r["locality"],
                    r["address"],
                    r["phone"],
                    r["site"],
                    r["type"],
                    "Подтверждена" if r["classified"] else "Не подтверждена",
                    r["regNum"],
                    r["regName"],
                    r["inn"],
                    {"live": "открывается", "dead": "не открывается", "error": "ошибка", "none": "нет сайта"}.get(
                        r["web"], r["web"]
                    ),
                    r["dupCount"],
                ]
                for r in kept_out
            ],
            [10, 34, 28, 52, 28, 36, 24, 18, 16, 32, 16, 16, 12],
        )

        ws2 = wb.create_sheet("Снятые")
        paint(
            ws2,
            [
                "№ исх.",
                "Наименование",
                "Населённый пункт",
                "Адрес",
                "Телефон",
                "Сайт",
                "Тип",
                "Причина снятия",
                "Пояснение",
                "Канонический №",
            ],
            [
                [
                    r["id"],
                    r["name"],
                    r["locality"],
                    r["address"],
                    r["phone"],
                    r["site"],
                    r["type"],
                    "Дубль" if r["removeKind"] == "duplicate" else "Устаревший / не объект",
                    r["removeReason"],
                    r.get("canonicalId") or "",
                ]
                for r in removed_out
            ],
            [10, 34, 28, 52, 28, 36, 24, 22, 54, 16],
        )
        path = os.path.join(PUBLIC_DIR, "reestr-dagestan-2026-09-27.xlsx")
        wb.save(path)
        print("xlsx", path, os.path.getsize(path))

    write_xlsx()

    print("SOURCE", len(rows))
    print("JUNK", len(junk))
    print("DUP GROUPS extra", len(dups))
    print("EXTRA OUT", len(extra_out))
    print("KEPT", len(final_kept), "classified", classified_n)
    print("REMOVED", len(removed))
    print("top localities", loc_counter.most_common(8))
    print("types", type_counter.most_common(8))
    print("web", web_counter)
    print("sample kept", [r["name"] for r in final_kept[:8]])
    print("sample junk", [(r["name"], r["removeReason"]) for r in junk[:6]])


if __name__ == "__main__":
    main()
