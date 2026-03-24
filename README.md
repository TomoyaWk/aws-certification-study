# AWS SAA 学習ツール

AWS 認定ソリューションアーキテクト - アソシエイト (SAA-C03) の試験対策として、Claude AI がオリジナル問題をリアルタイムで生成する Web アプリです。

## 機能

- **AI 問題生成** — トピックを選ぶと Claude がシナリオベースの問題を自動生成
- **16 トピック対応** — IAM, S3, EC2, VPC, RDS, Lambda, CloudFront など
- **3 段階の難易度** — 初級 / 中級 / 上級
- **即時フィードバック** — 正誤判定 + 日本語の詳細解説
- **学習履歴** — トピック別正答率と過去問の振り返り

## セットアップ

### 1. 依存パッケージのインストール

```bash
uv sync
```

### 2. API キーの設定

```bash
cp .env.example .env
```

`.env` を開いて `ANTHROPIC_API_KEY` を設定してください（[Anthropic Console](https://console.anthropic.com) で取得）。

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. アプリの起動

```bash
uv run python app.py
```

ブラウザで http://localhost:5000 を開いてください。

## 学習データのバックアップ

学習進捗は `study.db`（SQLite）に保存されます。このファイルは `.gitignore` で除外されているため、別途バックアップが必要です。

### エクスポート（バックアップ）

```bash
uv run python backup.py export
```

`study_backup.json` が生成されます。Git にコミットすることで進捗を管理できます。

```bash
git add study_backup.json
git commit -m "学習進捗のバックアップ"
```

### インポート（復元）

```bash
uv run python backup.py import
```

デフォルトは**マージモード**（既存データはそのまま、重複する問題はスキップ）。

DB をリセットして上書きしたい場合：

```bash
uv run python backup.py import --replace
```

### ファイル名を指定する場合

```bash
uv run python backup.py export --out my_backup.json
uv run python backup.py import --file my_backup.json
```

## プロジェクト構成

```
aws-certification-study/
├── app.py              # Flask アプリ本体
├── backup.py           # バックアップ・復元 CLI
├── pyproject.toml      # uv プロジェクト設定・依存関係
├── .python-version     # Python バージョン指定 (3.11)
├── .env.example        # 環境変数テンプレート
├── .gitignore
├── study_backup.json   # 学習データのバックアップ（コミット推奨）
├── templates/
│   ├── base.html
│   ├── index.html      # トピック選択
│   ├── quiz.html       # クイズ画面
│   └── history.html    # 学習履歴
└── static/
    └── style.css
```

> `study.db` と `.env` は `.gitignore` で除外されています。
