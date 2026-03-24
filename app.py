import json
import os
import sqlite3

import anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aws-saa-study-secret")

DATABASE = "study.db"

AWS_TOPICS = [
    {"id": "iam", "name": "IAM", "description": "Identity & Access Management", "icon": "🔐", "color": "danger"},
    {"id": "s3", "name": "S3", "description": "Simple Storage Service", "icon": "🗄️", "color": "warning"},
    {"id": "ec2", "name": "EC2", "description": "Elastic Compute Cloud", "icon": "💻", "color": "primary"},
    {"id": "vpc", "name": "VPC", "description": "Virtual Private Cloud", "icon": "🌐", "color": "info"},
    {"id": "rds", "name": "RDS", "description": "Relational Database Service", "icon": "🗃️", "color": "success"},
    {"id": "lambda", "name": "Lambda", "description": "Serverless Functions", "icon": "⚡", "color": "warning"},
    {"id": "cloudfront", "name": "CloudFront", "description": "Content Delivery Network", "icon": "🚀", "color": "primary"},
    {"id": "route53", "name": "Route 53", "description": "DNS & Routing", "icon": "🌍", "color": "info"},
    {"id": "elb", "name": "ELB", "description": "Elastic Load Balancing", "icon": "⚖️", "color": "secondary"},
    {"id": "autoscaling", "name": "Auto Scaling", "description": "Auto Scaling Groups", "icon": "📈", "color": "success"},
    {"id": "dynamodb", "name": "DynamoDB", "description": "NoSQL Database", "icon": "📊", "color": "danger"},
    {"id": "sqs_sns", "name": "SQS/SNS", "description": "Messaging Services", "icon": "📨", "color": "warning"},
    {"id": "cloudwatch", "name": "CloudWatch", "description": "Monitoring & Logs", "icon": "👁️", "color": "info"},
    {"id": "efs_ebs", "name": "EFS/EBS", "description": "Storage Services", "icon": "💾", "color": "primary"},
    {"id": "elasticache", "name": "ElastiCache", "description": "In-Memory Caching", "icon": "🚄", "color": "success"},
    {"id": "mixed", "name": "総合問題", "description": "AWS全般", "icon": "🎯", "color": "dark"},
]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
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


def get_topic_name(topic_id):
    return next((t["name"] for t in AWS_TOPICS if t["id"] == topic_id), topic_id)


def generate_question(topic, difficulty="medium"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 環境変数が設定されていません。.env ファイルを確認してください。")

    client = anthropic.Anthropic(api_key=api_key)
    topic_name = get_topic_name(topic)
    difficulty_text = {"easy": "初級", "medium": "中級", "hard": "上級"}.get(difficulty, "中級")

    prompt = f"""あなたはAWS認定ソリューションアーキテクト - アソシエイト (SAA-C03) の試験対策の専門家です。
{topic_name}に関する{difficulty_text}レベルの問題を1問生成してください。

以下のJSON形式**のみ**で返答してください（JSONの前後に余分なテキストやmarkdownコードブロックを含めないでください）：
{{
  "question": "問題文をここに記載",
  "options": {{
    "A": "選択肢A",
    "B": "選択肢B",
    "C": "選択肢C",
    "D": "選択肢D"
  }},
  "correct": "正解の選択肢（A/B/C/Dのどれか1文字）",
  "explanation": "詳細な解説：なぜその答えが正しいか、他の選択肢がなぜ間違いかを日本語で説明"
}}

作問のポイント：
- 問題文と解説は必ず日本語で書く
- 実際のSAA-C03試験に出るようなシナリオベースの問題にする（実際の業務シナリオを使う）
- 全ての選択肢が技術的に妥当に見えるようにする（明らかな誤答は避ける）
- 解説は充実させ、AWSのベストプラクティスや各サービスの特徴に触れる"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # markdownコードブロックが含まれる場合の対処
    if "```" in response_text:
        lines = response_text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    return json.loads(response_text)


@app.route("/")
def index():
    with get_db() as conn:
        stats = conn.execute(
            "SELECT COUNT(*) as total, COALESCE(SUM(is_correct), 0) as correct FROM answers"
        ).fetchone()
        topic_stats = conn.execute("""
            SELECT q.topic, COUNT(*) as total, COALESCE(SUM(a.is_correct), 0) as correct
            FROM questions q JOIN answers a ON q.id = a.question_id
            GROUP BY q.topic
        """).fetchall()
        topic_stats_dict = {r["topic"]: dict(r) for r in topic_stats}

    return render_template("index.html", topics=AWS_TOPICS, stats=stats, topic_stats=topic_stats_dict)


@app.route("/quiz/<topic>")
def quiz(topic):
    difficulty = request.args.get("difficulty", "medium")
    topic_info = next((t for t in AWS_TOPICS if t["id"] == topic), None)
    if not topic_info:
        return redirect("/")
    return render_template("quiz.html", topic=topic, difficulty=difficulty, topic_info=topic_info)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.json
    topic = data.get("topic", "mixed")
    difficulty = data.get("difficulty", "medium")

    try:
        question_data = generate_question(topic, difficulty)
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO questions (topic, difficulty, question, options, correct, explanation) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    topic,
                    difficulty,
                    question_data["question"],
                    json.dumps(question_data["options"], ensure_ascii=False),
                    question_data["correct"],
                    question_data["explanation"],
                ),
            )
            question_data["id"] = cursor.lastrowid
        return jsonify({"success": True, "question": question_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/answer", methods=["POST"])
def api_answer():
    data = request.json
    question_id = data.get("question_id")
    selected = data.get("selected")

    with get_db() as conn:
        question = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not question:
            return jsonify({"success": False, "error": "Question not found"}), 404

        is_correct = 1 if selected == question["correct"] else 0
        conn.execute(
            "INSERT INTO answers (question_id, selected, is_correct) VALUES (?, ?, ?)",
            (question_id, selected, is_correct),
        )

    return jsonify({
        "success": True,
        "is_correct": bool(is_correct),
        "correct": question["correct"],
        "explanation": question["explanation"],
    })


@app.route("/history")
def history():
    with get_db() as conn:
        records = conn.execute("""
            SELECT q.topic, q.difficulty, q.question, q.options, q.correct, q.explanation,
                   a.selected, a.is_correct, a.answered_at
            FROM questions q JOIN answers a ON q.id = a.question_id
            ORDER BY a.answered_at DESC LIMIT 50
        """).fetchall()
        topic_stats = conn.execute("""
            SELECT q.topic, COUNT(*) as total, COALESCE(SUM(a.is_correct), 0) as correct
            FROM questions q JOIN answers a ON q.id = a.question_id
            GROUP BY q.topic ORDER BY total DESC
        """).fetchall()
        overall = conn.execute(
            "SELECT COUNT(*) as total, COALESCE(SUM(is_correct), 0) as correct FROM answers"
        ).fetchone()

    return render_template(
        "history.html",
        records=records,
        topic_stats=topic_stats,
        overall=overall,
        topics=AWS_TOPICS,
        get_topic_name=get_topic_name,
        json=json,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
