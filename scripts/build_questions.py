#!/usr/bin/env python3
"""從 RTFD 試卷提取題目，去重後輸出 questions.json"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT.parent
OUTPUT = ROOT / "questions.json"

# 依題幹關鍵字對應正確答案（a/b/c/d/e/f 或複選如 "b,d"）
ANSWER_HINTS: list[tuple[str, str]] = [
    ("複合索引鍵", "b"),
    ("District的新資料行", "b"),
    ("Furniture類別的所有產品", "b"),
    ("預存程序來刪除資料", "b"),  # O、X、O
    ("除了加州(CA)以外", "b"),
    ("函式與預存程序之間", "b"),
    ("訂單數目少於50的國家", "d"),
    ("Prefix的資料行", "a"),
    ("叢集索引可提升以下查詢", "a"),
    ("移除所有資料列，但不記錄", "c"),
    ("資料表中欄位的每個值都必須是唯一的", "c"),
    ("NorthAmercanMammals", "b"),
    ("結合成單一結果，而且包含這兩個查詢中的所有資料列", "b"),
    ("資料操語言(DML)", "b"),
    ("FirstName 資料行具有NULL值", "d"),
    ("笛卡兒乘積會包含多少個資料列", "d"),
    ("enrollment_date", "a"),
    ("SalesPerson資料表中保存有效的", "b"),
    ("students INNER JOIN courses ON", "b"),
    ("確保輸入資料行中的資料正確", "c"),
    ("Greetings", "b"),
    ("傳回Employee資料表中的資料列數", "b"),
    ("CustomerID為12345", "d"),
    ("根據收費金額執行財務函式", "b"),
    ("僅傳回兩個結果集都有出現的資料列", "b"),
    ("REVOKE", "c"),
    ("FROM Employee, Department", "d"),
    ("正規化為第一正規形式", "b,d"),
    ("Phone IS NULL", "a"),
    ("僅刪除40個資料列之後，交易便失敗", "d"),
    ("ship_state不含德州", "a"),
    ("CustomerID是主索引鍵", "c"),
    ("手動呼叫程式碼", "b"),
    ("CREATE TABLE陳述式", "c,d"),
    ("DROP COLUMN SSN", "b"),
    ("inner join(內部聯結)", "a"),
    ("DROP VIEW EmployeeView", "c"),
    ("EmployeeCopy的資料表", "b"),
    ("差異備份只會複製", "c"),
    ("按照字母順序排列的遊戲名稱", "c"),
    ("刪除某個資料庫資料表", "c"),
    ("WHERE\n子句中使用哪一個關鍵字", "d"),
    ("ProductDescription = 'spoon'", "c"),
    ("員工只能被指派到一個現有的部門", "b"),
    ("建立預存程序的其中一個原因", "a"),
    ("移除外部索引鍵", "d"),
    ("Category =", "c"),
    ("建立索引", "b"),
    ("Flight的資料表", "d"),  # B、B、A、A
    ("PlayerStat的資料表", "b"),
    ("ProductCategory", "a"),  # 資料行
    ("LoanedBooks", "c"),
    ("Volunteer的資料庫資料表", "b"),
    ("Building的資料表", "c"),
    ("ProductID 資料行是主索引鍵", "c"),
    ("ProductID與ProductCategory之間的關聯性", "a"),
    ("Chapter和Language", "b"),  # 單選題，非 ChapterLanguage 複選
    ("寵物比賽獲勝者", "b"),
    ("名為Cars的資料庫資料表", "c"),
    ("CREATE TABLE Road", "c"),
    ("Cars與Colors", "b"),
    ("第三正規形式", "c"),
    ("Origin <> 'USA'", "c"),
    ("ChapterLanguage", "b,d"),
    # 以下為先前因特殊空白字元未能匹配的題目
    ("DELETE FROM Student 請問", "b"),
    ("部分資料列的FirstName", "b"),
    ("OUTER  JOIN  courses", "b"),
    ("此查詢會傳回錯誤", "b"),
    ("資料表中的資料列數目", "b"),
    ("停用User1檢視", "c"),
    ("FROM Employee, Department", "d"),
    ("VALUES (3296, 'Table', 4444)", "e"),
    ("未輸入員工電話號碼", "a"),
    ("REMOVE SSN", "b"),
    ("沒有任何訂單的客戶", "b"),
    ("移除名為EmployeeView", "c"),
    ("Sample Movie是否只在Movie", "c"),
    ("Category = 'Science Books'", "c"),
    ("INSERT INTO Road VALUES (1234, 36)", "a"),
    ("分機為有效號碼", "d"),
    ("StudentName必須包含字元字串", "a"),
    ("名稱包含特定字元", "d"),
]


def parse_text_questions(rtf_path: Path) -> list[dict]:
    """解析含表格、拖放排序等非標準選項格式的題目"""
    text = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(rtf_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    html = subprocess.run(
        ["textutil", "-convert", "html", "-stdout", str(rtf_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # 找出含圖片的題號
    image_qnums: set[int] = set()
    for row in re.findall(r"<tr>\s*(.*?)\s*</tr>", html, re.DOTALL):
        if "配分" not in row:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(tds) < 3:
            continue
        if re.search(r"\.(jpg|jpeg|png|gif)", tds[2], re.I):
            pre = re.sub(r"<[^>]+>", " ", tds[2][:200])
            m = re.search(r"(\d+)\.", pre)
            if m:
                image_qnums.add(int(m.group(1)))

    skip_line = re.compile(
        r"^(欄位|資料類型|允許Null|FALSE|TRUE|"
        r"INT|VARCHAR|CHAR\(|DATETIME|DECIMAL|"
        r"ProductID|ProductName|CategoryID|ItemNumber|ItemName|"
        r"ID\s*$|Name\s*$|Age\s*$|City\s*$|Books\s*$|Year\s*$|"
        r"StreetAddress|State|PostalCode|Extension|"
        r"GivenName|DateOfBirth|PhoneNumber|LineItemTotal|"
        r"BuildingID|Address|InspectionDate|"
        r"PlayerID|TeamID|GameDate|FlightNumber|OriginAirport|"
        r"DestinationAirport|DepartureTime|ArrivalTime)$",
        re.I,
    )

    def is_option_line(line: str) -> bool:
        if skip_line.match(line.strip()):
            return False
        return bool(
            re.match(r"^[A-G]、", line)
            or re.match(r"^\([A-G]\)", line)
            or line.startswith("CREATE ")
            or line.startswith("SELECT ")
            or line.startswith("ALTER ")
            or line.startswith("INSERT ")
            or line.startswith("UPDATE ")
            or line.startswith("DELETE ")
            or line.startswith("DROP ")
            or line.startswith("TRUNCATE ")
            or line.startswith("MODIFY ")
            or "Delete)" in line
            or (len(line) < 80 and re.match(r"^[OX、]+$", line.replace(" ", "")))
            or (
                len(line) < 120
                and line.endswith("。")
                and any(k in line for k in ["刪除", "保持", "清空", "封存", "被刪除"])
            )
            or (
                len(line) < 60
                and "、" in line
                and re.match(r"^[A-Za-z、OX\d\s]+$", line)
            )
        )

    table_data = re.compile(
        r"^(\d{1,6}|books|movies|Spoon|Chair|Table|Chicago|Illinois|"
        r"Japan|USA|Red|Silver|Sedan|Truck|Minivan|Hatchback|Compact|"
        r"New York|San Francisco|Dallas|Texas|NULL|null)$",
        re.I,
    )

    def is_short_option(line: str) -> bool:
        line = line.strip()
        if not line or len(line) > 50 or skip_line.match(line):
            return False
        if table_data.match(line):
            return False
        if re.match(r"^\d+\.\s", line):
            return False
        if is_option_line(line):
            return True
        # 短中文選項（如：語法錯誤、功能相依）
        if 2 <= len(line) <= 40 and re.search(r"[\u4e00-\u9fff]", line):
            if any(
                k in line
                for k in [
                    "錯誤", "違規", "相依", "新資料列", "語法", "索引", "主鍵",
                    "外部", "功能", "關聯", "決定", "世代", "複合", "允許",
                    "刪除", "保持", "清空", "封存", "傳回", "效能", "程序",
                    "函式", "觸發", "檢視", "交易", "正確", "唯一", "Null",
                ]
            ):
                return True
        return False

    def is_column_option(line: str) -> bool:
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9]*$", line.strip()) and len(line) <= 25)

    def is_numeric_option(line: str) -> bool:
        return bool(re.match(r"^\d+$", line.strip()) and len(line) <= 4)

    def is_sql_option_line(line: str) -> bool:
        s = line.strip()
        if re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|USE)\b", s, re.I):
            return True
        if re.match(r"^SET .+FROM ", s.replace(" ", ""), re.I):
            return True
        return False

    def split_q_and_options(content_lines: list[str]) -> tuple[str, list[str]]:
        lines = [l for l in content_lines if l and not l.startswith("配分") and not l.startswith("[2.")]
        if not lines:
            return "", []

        # 優先：以 SQL 陳述式切分題幹與選項（表格題）
        sql_idxs = [i for i, l in enumerate(lines) if is_sql_option_line(l)]
        if sql_idxs:
            first_sql = sql_idxs[0]
            qtext = "\n".join(lines[:first_sql]).strip()
            options = [l.strip() for l in lines[first_sql:] if is_sql_option_line(l)]
            if len(options) >= 2:
                return qtext, options

        # 末尾純數字選項（如 4、5、6、7 或 0、2、3、6）
        num_end = len(lines)
        num_start = num_end
        while num_start > 0 and is_numeric_option(lines[num_start - 1]):
            num_start -= 1
        if num_end - num_start >= 2:
            return "\n".join(lines[:num_start]).strip(), lines[num_start:num_end]

        # 末尾文字/欄位名稱/中文選項
        opt_end = len(lines)
        opt_start = opt_end
        while opt_start > 0:
            prev = lines[opt_start - 1]
            if is_short_option(prev) or is_column_option(prev):
                opt_start -= 1
            else:
                break
        tail_opts = lines[opt_start:opt_end]
        if len(tail_opts) >= 2:
            return "\n".join(lines[:opt_start]).strip(), tail_opts

        # 串流解析（SQL 語句等）
        qtext_parts: list[str] = []
        options: list[str] = []
        for line in lines:
            if is_option_line(line) or is_column_option(line) or (options and is_short_option(line)):
                options.append(line)
            elif not options:
                qtext_parts.append(line)
            elif is_short_option(line):
                options.append(line)
        return "\n".join(qtext_parts).strip(), options

    questions = []
    for part in re.split(r"(?=得分：)", text):
        score_m = re.search(r"得分：([\d.]+)", part)
        if not score_m:
            continue
        lines = [
            l.strip()
            for l in part[score_m.end() :].split("\n")
            if l.strip() and l.strip() != "¬"
        ]
        if not lines:
            continue
        qm = re.match(r"^(\d+)\.\s*(.*)", lines[0])
        if not qm:
            continue

        qnum = int(qm.group(1))
        first = qm.group(2)
        rest = lines[1:]
        qtext, options = split_q_and_options([first] + rest if first else rest)

        if len(qtext) <= 10 or len(options) < 2:
            continue

        questions.append(
            {
                "text": qtext,
                "options": [
                    {"id": chr(ord("a") + i), "text": o} for i, o in enumerate(options)
                ],
                "hasImage": qnum in image_qnums or "附圖" in qtext,
            }
        )

    return questions


def parse_html_questions(rtf_path: Path) -> list[dict]:
    html = subprocess.run(
        ["textutil", "-convert", "html", "-stdout", str(rtf_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    questions = []
    rows = re.findall(r"<tr>\s*(.*?)\s*</tr>", html, re.DOTALL)

    for row in rows:
        if "配分" not in row:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(tds) < 3:
            continue

        qcol = tds[2]
        has_image = bool(re.search(r"\.(jpg|jpeg|png|gif)", qcol, re.I))

        ol_match = re.search(r"<ol[^>]*>(.*?)</ol>", qcol, re.DOTALL)
        pre_ol = qcol[: ol_match.start()] if ol_match else qcol
        pre_text = re.sub(r"<[^>]+>", "\n", pre_ol)
        pre_text = re.sub(r"\n+", "\n", pre_text).strip()

        qm = re.match(r"(\d+)\.\s*(.*)", pre_text, re.DOTALL)
        if not qm:
            continue

        qtext = qm.group(2).strip()
        options: list[dict] = []

        if ol_match:
            items = re.findall(r"<li[^>]*>(.*?)</li>", ol_match.group(1), re.DOTALL)
            for idx, item in enumerate(items):
                text = re.sub(r"<[^>]+>", " ", item)
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    options.append({"id": chr(ord("a") + idx), "text": text})

        if len(qtext) <= 10 or len(options) < 2:
            continue

        questions.append(
            {
                "text": qtext,
                "options": options,
                "hasImage": has_image,
            }
        )

    return questions


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_match(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def normalize_match(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def post_process_question(q: dict) -> dict:
    """修正解析錯誤：題幹截斷、選項混入題目文字等"""
    text = q["text"]
    options = list(q["options"])
    old_answer = q.get("answer")
    old_by_id = {o["id"]: o["text"] for o in options}

    # 選項中的「請問」移回題幹
    kept: list[dict] = []
    for o in options:
        if o["text"].startswith("請問"):
            text = text.rstrip() + "\n" + o["text"]
        else:
            kept.append(o)
    options = kept

    # 若混有 SQL 選項，只保留 SQL 陳述式（排除表格欄位名稱）
    has_sql = any(
        re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|USE)\b", o["text"].strip(), re.I)
        for o in options
    )
    if has_sql:
        sql_opts = [
            o
            for o in options
            if re.match(
                r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|USE|SET)\b",
                o["text"].strip(),
                re.I,
            )
        ]
        if len(sql_opts) >= 2:
            options = sql_opts

    # 若混有 CREATE TABLE 選項，只保留 CREATE 開頭的
    has_create = any(o["text"].strip().upper().startswith("CREATE") for o in options)
    if has_create and not has_sql:
        create_opts = [o for o in options if o["text"].strip().upper().startswith("CREATE")]
        if len(create_opts) >= 2:
            options = create_opts

    # 重新編號選項
    new_options = [{"id": chr(ord("a") + i), "text": o["text"]} for i, o in enumerate(options)]
    q["text"] = text.strip()
    q["options"] = new_options

    # 依選項文字重對答案字母
    if old_answer:
        new_ids: list[str] = []
        for aid in old_answer.split(","):
            aid = aid.strip()
            old_text = old_by_id.get(aid)
            if not old_text:
                continue
            for o in new_options:
                if o["text"] == old_text or normalize_match(o["text"]) == normalize_match(old_text):
                    new_ids.append(o["id"])
                    break
        if new_ids:
            q["answer"] = ",".join(new_ids)

    norm = normalize_match(q["text"])
    if "請選擇2個答案" in norm or "請選擇 2 個答案" in norm:
        q["multi"] = True

    return q


def derive_answer(q: dict) -> str | None:
    text = normalize_match(q["text"])
    opts = {o["id"]: normalize_match(o["text"]) for o in q["options"]}
    all_text = text + " " + " ".join(opts.values())

    # 依選項文字比對（避免選項順序不同導致答案字母錯誤）
    for oid, ot in opts.items():
        if "Cascade Delete" in ot or "串聯刪除" in ot:
            if "自動刪除" in text:
                return oid
        if ot.startswith("INSERT INTO AddressInfo ([StreetAddress]"):
            if "請選擇2" in text:
                pass  # 下方複選處理
            else:
                return oid
        if "CREATE TABLE Student ( ID INT" in ot:
            return oid
        if "LIKE '%Chocolate%'" in ot:
            return oid
        if "SELECT COUNT(ID), AVG(LineItemTotal)" in ot and "GROUP BY" not in ot.upper() and "HAVING" not in ot.upper():
            if "ItemsOnOrder" in text:
                return oid
        if ot == "O、X、X、O":
            return oid
        if "SELECT COUNT(*) FROM Employee" in ot and "資料列數目" in all_text:
            return oid

    if "請選擇2" in text and any("AddressInfo" in ot for ot in opts.values()):
        ids = []
        for oid, ot in opts.items():
            if ot.startswith("INSERT INTO AddressInfo ([StreetAddress]"):
                ids.append(oid)
            if ot.startswith("INSERT INTO AddressInfo VALUES ('1234 Main Street'"):
                ids.append(oid)
        if len(ids) == 2:
            return ",".join(sorted(ids))

    if "ChapterLanguage" in text and "請選擇2" in text:
        ids = [oid for oid, ot in opts.items() if ot in ("LanguageId", "ChapterId")]
        if len(ids) == 2:
            return ",".join(sorted(ids))

    if "填入正確或錯誤符號" in text:
        for oid, ot in opts.items():
            if ot == "O、X、X、O":
                return oid

    best: tuple[tuple[int, int], str] | None = None
    for hint, ans in ANSWER_HINTS:
        hint_n = normalize_match(hint)
        in_text = hint_n in text
        in_all = hint_n in all_text
        if not in_text and not in_all:
            continue
        score = (1 if in_text else 0, len(hint_n))
        if best is None or score > best[0]:
            best = (score, ans)
    if best:
        return best[1]

    if "ALTER TABLE Customer ADD (District INTEGER)" in opts.values():
        return "b"

    if "TRUNCATE TABLE" in opts.values():
        return "c"

    return None


def main() -> None:
    all_questions: list[dict] = []

    for i in range(1, 5):
        rtf = SOURCE_DIR / f"{i}.rtfd" / "TXT.rtf"
        if rtf.exists():
            all_questions.extend(parse_html_questions(rtf))
            all_questions.extend(parse_text_questions(rtf))

    def question_key(text: str) -> str:
        # 以題幹開頭去重，合併僅選項順序/措辭不同的同一題
        return hashlib.sha256(normalize(text)[:45].encode()).hexdigest()

    def score_question(q: dict) -> tuple:
        ans = 1 if q.get("answer") else 0
        return (ans, len(q["options"]), -len(q["text"]))

    seen: dict[str, dict] = {}
    for q in all_questions:
        key = question_key(q["text"])
        if key not in seen or score_question(q) > score_question(seen[key]):
            seen[key] = q

    unique: list[dict] = []
    for q in seen.values():
        q = post_process_question(q)
        answer = derive_answer(q)
        multi = q.get("multi", False) or ("," in (answer or ""))
        unique.append(
            {
                "id": len(unique) + 1,
                "text": q["text"],
                "options": q["options"],
                "answer": answer,
                "multi": multi,
                "hasImage": q["hasImage"],
            }
        )

    # 複製共用圖片
    assets = ROOT / "assets" / "images"
    for i in range(1, 5):
        img = SOURCE_DIR / f"{i}.rtfd" / "WM3fb26v.jpg"
        if img.exists():
            dest = assets / "schema-address.jpg"
            if not dest.exists():
                dest.write_bytes(img.read_bytes())
            break

    data = {
        "title": "SQL 資料庫練習題",
        "total": len(unique),
        "questions": unique,
    }

    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    js_output = ROOT / "questions.js"
    js_output.write_text(
        "window.QUIZ_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    answered = sum(1 for q in unique if q["answer"])
    print(f"已輸出 {len(unique)} 道題目（含答案 {answered} 道）")
    print(f"  → {OUTPUT}")
    print(f"  → {js_output}")


if __name__ == "__main__":
    main()
