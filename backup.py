"""
学習データのバックアップ・復元スクリプト

使い方:
  uv run python backup.py export              # study_backup.json にエクスポート
  uv run python backup.py export --out my.json  # ファイル名を指定
  uv run python backup.py import              # study_backup.json からインポート
  uv run python backup.py import --file my.json --replace  # DBをリセットしてインポート
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import os

DATABASE = os.environ.get("DATABASE_PATH", "study.db")
DEFAULT_BACKUP = "study_backup.json"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_export(out_path: str) -> None:
    if not Path(DATABASE).exists():
        print(f"エラー: {DATABASE} が見つかりません。アプリを一度起動してください。")
        sys.exit(1)

    with get_db() as conn:
        questions = conn.execute("SELECT * FROM questions ORDER BY id").fetchall()
        answers = conn.execute("SELECT * FROM answers ORDER BY id").fetchall()

    # questions に answers をネストして持たせる
    q_map = {}
    for q in questions:
        q_dict = dict(q)
        q_dict["answers"] = []
        q_map[q["id"]] = q_dict

    for a in answers:
        qid = a["question_id"]
        if qid in q_map:
            q_map[qid]["answers"].append({
                "selected": a["selected"],
                "is_correct": a["is_correct"],
                "answered_at": a["answered_at"],
            })

    backup = {
        "exported_at": datetime.now().isoformat(),
        "version": 1,
        "records": list(q_map.values()),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    total_q = len(q_map)
    total_a = sum(len(v["answers"]) for v in q_map.values())
    print(f"エクスポート完了: {out_path}")
    print(f"  問題数: {total_q}  回答数: {total_a}")


def cmd_import(file_path: str, replace: bool) -> None:
    if not Path(file_path).exists():
        print(f"エラー: {file_path} が見つかりません。")
        sys.exit(1)

    with open(file_path, encoding="utf-8") as f:
        backup = json.load(f)

    records = backup.get("records", [])
    if not records:
        print("バックアップファイルにデータがありません。")
        return

    with get_db() as conn:
        # DBテーブルが存在しない場合は作成
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER,
                selected TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)

        if replace:
            conn.execute("DELETE FROM answers")
            conn.execute("DELETE FROM questions")
            print("既存データを削除しました。")

        # 既存の問題文セットを取得（マージ時の重複スキップ用）
        existing = set()
        if not replace:
            rows = conn.execute("SELECT question FROM questions").fetchall()
            existing = {r["question"] for r in rows}

        imported_q = 0
        skipped_q = 0
        imported_a = 0

        for rec in records:
            question_text = rec["question"]

            if not replace and question_text in existing:
                skipped_q += 1
                continue

            cursor = conn.execute(
                "INSERT INTO questions (topic, difficulty, question, options, correct, explanation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    rec["topic"],
                    rec.get("difficulty", "medium"),
                    question_text,
                    rec["options"] if isinstance(rec["options"], str) else json.dumps(rec["options"], ensure_ascii=False),
                    rec["correct"],
                    rec["explanation"],
                    rec.get("created_at"),
                ),
            )
            new_id = cursor.lastrowid
            imported_q += 1

            for ans in rec.get("answers", []):
                conn.execute(
                    "INSERT INTO answers (question_id, selected, is_correct, answered_at) VALUES (?, ?, ?, ?)",
                    (new_id, ans["selected"], ans["is_correct"], ans.get("answered_at")),
                )
                imported_a += 1

    print(f"インポート完了: {file_path}")
    print(f"  インポート: 問題 {imported_q}件  回答 {imported_a}件")
    if skipped_q:
        print(f"  スキップ（重複）: {skipped_q}件")


def main():
    parser = argparse.ArgumentParser(description="学習データのバックアップ・復元")
    sub = parser.add_subparsers(dest="command", required=True)

    exp = sub.add_parser("export", help="JSONにエクスポート")
    exp.add_argument("--out", default=DEFAULT_BACKUP, help=f"出力ファイル (デフォルト: {DEFAULT_BACKUP})")

    imp = sub.add_parser("import", help="JSONからインポート")
    imp.add_argument("--file", default=DEFAULT_BACKUP, help=f"入力ファイル (デフォルト: {DEFAULT_BACKUP})")
    imp.add_argument("--replace", action="store_true", help="既存データを削除してからインポート")

    args = parser.parse_args()

    if args.command == "export":
        cmd_export(args.out)
    elif args.command == "import":
        cmd_import(args.file, args.replace)


if __name__ == "__main__":
    main()
