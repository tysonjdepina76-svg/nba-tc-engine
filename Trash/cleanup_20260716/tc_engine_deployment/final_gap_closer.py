import os
import sys
import textwrap
from pathlib import Path

BASE = Path("/home/workspace/tc_engine_deployment")

FILES = {
    BASE / "Dockerfile": textwrap.dedent("""\
        FROM python:3.12-slim
        WORKDIR /app
        RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY . .
        ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
    """),

    BASE / "requirements.txt": textwrap.dedent("""\
        fastapi>=0.110.0
        uvicorn[standard]>=0.29.0
        sqlalchemy[asyncio]>=2.0.30
        asyncpg>=0.29.0
        alembic>=1.13.0
        psycopg2-binary>=2.9.9
        xgboost>=2.0.3
        shap>=0.45.0
        pandas>=2.2.0
        numpy>=1.26.0
        scikit-learn>=1.4.0
        matplotlib>=3.8.0
        seaborn>=0.13.0
        streamlit>=1.33.0
        python-telegram-bot>=21.0
        httpx>=0.27.0
        pydantic>=2.7.0
        python-dotenv>=1.0.0
        joblib>=1.4.0
    """),

    BASE / "alembic.ini": textwrap.dedent("""\
        [alembic]
        script_location = migrations
        sqlalchemy.url = postgresql+asyncpg://postgres:postgres@postgres:5432/tc_engine

        [loggers]
        keys = root,sqlalchemy,alembic

        [handlers]
        keys = console

        [formatters]
        keys = generic

        [logger_root]
        level = WARN
        handlers = console

        [logger_sqlalchemy]
        level = WARN
        handlers =
        qualname = sqlalchemy.engine

        [logger_alembic]
        level = INFO
        handlers =
        qualname = alembic

        [handler_console]
        class = StreamHandler
        args = (sys.stderr,)
        level = NOTSET
        formatter = generic

        [formatter_generic]
        format = %(levelname)-5.5s [%(name)s] %(message)s
        datefmt = %H:%M:%S
    """),

    BASE / "migrations" / "env.py": textwrap.dedent("""\
        from logging.config import fileConfig
        from sqlalchemy import engine_from_config, pool
        from alembic import context

        config = context.config
        if config.config_file_name is not None:
            fileConfig(config.config_file_name)

        target_metadata = None

        def run_migrations_offline():
            url = config.get_main_option("sqlalchemy.url")
            context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
            with context.begin_transaction():
                context.run_migrations()

        def run_migrations_online():
            connectable = engine_from_config(
                config.get_section(config.config_ini_section, {}),
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
            with connectable.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata)
                with context.begin_transaction():
                    context.run_migrations()

        if context.is_offline_mode():
            run_migrations_offline()
        else:
            run_migrations_online()
    """),

    BASE / "migrations" / "script.py.mako": textwrap.dedent("""\
        '''${message}

        Revision ID: ${up_revision}
        Revises: ${down_revision | comma,n}
        Create Date: ${create_date}
        '''
        from alembic import op
        import sqlalchemy as sa

        revision = ${repr(up_revision)}
        down_revision = ${repr(down_revision)}
        branch_labels = ${repr(branch_labels)}
        depends_on = ${repr(depends_on)}

        def upgrade():
            ${upgrades if upgrades else "pass"}

        def downgrade():
            ${downgrades if downgrades else "pass"}
    """),

    BASE / "migrations" / "versions" / "001_add_features_and_actual.sql": textwrap.dedent("""\
        ALTER TABLE picks ADD COLUMN IF NOT EXISTS prediction_features JSONB;
        ALTER TABLE picks ADD COLUMN IF NOT EXISTS actual_value FLOAT;
        ALTER TABLE picks ADD COLUMN IF NOT EXISTS ml_edge FLOAT;
        ALTER TABLE picks ADD COLUMN IF NOT EXISTS model_version VARCHAR(32);
    """),

    BASE / "engine" / "__init__.py": "",

    BASE / "engine" / "stagger.py": textwrap.dedent("""\
        import os
        import time
        import random
        import httpx
        from datetime import datetime

        STAGGER_SECONDS = int(os.environ.get("STAGGER_SECONDS", "300"))
        API_URL = os.environ.get("API_URL", "http://api:8000")

        def main():
            print(f"Stagger engine starting — check every {STAGGER_SECONDS}s")
            while True:
                try:
                    now = datetime.now()
                    print(f"[{now.isoformat()}] Heartbeat check...")
                    with httpx.Client(timeout=10) as client:
                        resp = client.get(f"{API_URL}/health")
                        data = resp.json()
                        print(f"  Health: {data.get('status')}, Picks: {data.get('picks_today')}, Model: {data.get('model_loaded')}")
                except Exception as e:
                    print(f"  Heartbeat error: {e}")

                jitter = random.uniform(0.9, 1.1)
                time.sleep(STAGGER_SECONDS * jitter)

        if __name__ == "__main__":
            main()
    """),

    BASE / "engine" / "telegram_bot.py": textwrap.dedent("""\
        import os
        import asyncio
        from telegram import Bot
        from datetime import datetime
        import httpx

        TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
        API_URL = os.environ.get("API_URL", "http://api:8000")

        async def send_daily_report():
            if not TOKEN or not CHAT_ID:
                print("Telegram not configured — skipping")
                return

            bot = Bot(token=TOKEN)
            today = datetime.now().strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{API_URL}/picks/today")
                data = resp.json()
                count = data.get("count", 0)

            if count > 0:
                msg = f"TC Daily Report — {today}\\n"
                msg += f"Total picks: {count}\\n"
                msg += "Dash: http://localhost:8510"
            else:
                msg = f"TC Daily Report — {today}\\nNo picks generated yet."

            await bot.send_message(chat_id=CHAT_ID, text=msg)
            print(f"Telegram report sent: {count} picks")

        if __name__ == "__main__":
            asyncio.run(send_daily_report())
    """),

    BASE / "engine" / "ml_dashboard.py": textwrap.dedent("""\
        import os
        import json
        import pandas as pd
        import streamlit as st

        st.set_page_config(page_title="TC ML Dashboard", layout="wide")

        MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")
        DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

        st.title("TC Engine — ML Dashboard")

        col1, col2, col3 = st.columns(3)

        metrics_path = os.path.join(MODEL_DIR, "training_metrics.json")
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                metrics = json.load(f)
            col1.metric("Model Accuracy", f"{metrics['mean_accuracy']:.1%}")
            col1.metric("Training Samples", metrics["n_samples"])
        else:
            col1.warning("Model not trained yet")

        data_path = os.path.join(DATA_DIR, "training_data.csv")
        if os.path.exists(data_path):
            df = pd.read_csv(data_path)
            graded = df.dropna(subset=["won"])
            col2.metric("Total Picks (30d)", len(df))
            col2.metric("Graded Picks", len(graded))
            if len(graded) > 0:
                wr = graded["won"].astype(int).mean() * 100
                col2.metric("Win Rate", f"{wr:.1f}%")
        else:
            col2.warning("No training data")

        shap_path = os.path.join(MODEL_DIR, "shap_summary.png")
        if os.path.exists(shap_path):
            st.image(shap_path, caption="SHAP Summary Plot", use_container_width=True)

        pdp_path = os.path.join(MODEL_DIR, "pdp_plots.png")
        if os.path.exists(pdp_path):
            st.image(pdp_path, caption="Partial Dependence Plots", use_container_width=True)

        fi_path = os.path.join(MODEL_DIR, "feature_importance.png")
        if os.path.exists(fi_path):
            st.image(fi_path, caption="Feature Importances", use_container_width=True)

        if os.path.exists(metrics_path):
            st.json(metrics)
    """),

    BASE / "data" / ".gitkeep": "",
    BASE / "models" / ".gitkeep": "",
    BASE / "logs" / ".gitkeep": "",
}


def main():
    for path, content in FILES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.suffix in (".sql", ".py"):
            path.write_text(content)
            print(f"  CREATED: {path.relative_to(BASE)}")
        else:
            print(f"  EXISTS:  {path.relative_to(BASE)}")

    env_example = BASE / ".env.template"
    env_content = textwrap.dedent("""\
        POSTGRES_USER=postgres
        POSTGRES_PASSWORD=postgres
        POSTGRES_DB=tc_engine
        POSTGRES_HOST=postgres
        POSTGRES_PORT=5432
        DAILY_LOG=/app/Daily_Log
        DATA_DIR=/app/data
        MODEL_DIR=/app/models
        TELEGRAM_BOT_TOKEN=
        TELEGRAM_CHAT_ID=
        SGO_API_KEY=
        ODDS_API_KEY=
    """)
    if not env_example.exists():
        env_example.write_text(env_content)
        print(f"  CREATED: .env.template")

    print("\nfinal_gap_closer.py: All engine files generated.")
    print("Next steps:")
    print("  1. docker compose up -d --build")
    print("  2. docker compose run --rm live_engine alembic upgrade head")
    print("  3. python scripts/export_training_data.py")
    print("  4. python engine/train_with_shap.py")
    print("  5. python engine/generate_explainability_plots.py")
    print("  6. python engine/backtest.py")


if __name__ == "__main__":
    main()
