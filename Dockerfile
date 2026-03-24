# ── ビルドステージ ──────────────────────────────────────────
FROM python:3.11-slim AS builder

# uvのインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 依存関係のキャッシュを活かすため lockfile → sync の順
COPY pyproject.toml uv.lock ./

# 仮想環境を .venv に作成し、依存パッケージをインストール
# --frozen: uv.lock を厳密に使用（lockfileと差異があればエラー）
# --no-dev: 開発用パッケージを除外
RUN uv sync --frozen --no-dev

# ── 実行ステージ ──────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# ビルドステージの .venv だけコピー（uvは不要）
COPY --from=builder /app/.venv /app/.venv

# アプリのコピー
COPY app.py backup.py ./
COPY static/ static/
COPY templates/ templates/

# SQLiteの保存先ディレクトリを作成
RUN mkdir -p /app/data

# .venv のPythonをPATHに追加
ENV PATH="/app/.venv/bin:$PATH"
ENV DATABASE_PATH=/app/data/study.db

EXPOSE 5000

CMD ["python", "app.py"]