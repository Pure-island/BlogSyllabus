from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()


def _create_engine() -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

    if settings.database_url.startswith("sqlite:///./"):
        database_path = Path(settings.database_url.replace("sqlite:///./", "", 1))
        database_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(settings.database_url, echo=False, connect_args=connect_args)


engine = _create_engine()


def _ensure_sqlite_column(table_name: str, column_name: str, ddl: str) -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name not in columns:
            connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _migrate_sources_table() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]: {"notnull": bool(row[3])}
            for row in connection.exec_driver_sql("PRAGMA table_info(sources)").fetchall()
        }
        needs_rebuild = (
            "source_type" not in columns
            or columns.get("rss_url", {}).get("notnull", False)
            or "import_strategy" in columns
            or "sitemap_url" in columns
            or "archive_url" in columns
        )
        if not needs_rebuild:
            return

        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("ALTER TABLE sources RENAME TO sources_legacy")
        connection.exec_driver_sql(
            """
            CREATE TABLE sources (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                homepage_url TEXT,
                rss_url TEXT UNIQUE,
                source_type TEXT NOT NULL DEFAULT 'rss',
                language TEXT NOT NULL DEFAULT 'zh-CN',
                priority INTEGER NOT NULL DEFAULT 50,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                last_fetched_at DATETIME,
                last_fetch_status TEXT NOT NULL DEFAULT 'idle',
                last_fetch_error TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql("CREATE INDEX ix_sources_name ON sources (name)")
        connection.exec_driver_sql(
            """
            INSERT INTO sources (
                id,
                name,
                homepage_url,
                rss_url,
                source_type,
                language,
                priority,
                is_active,
                last_fetched_at,
                last_fetch_status,
                last_fetch_error,
                created_at,
                updated_at
            )
            SELECT
                id,
                name,
                homepage_url,
                NULLIF(TRIM(COALESCE(rss_url, '')), ''),
                CASE
                    WHEN TRIM(COALESCE(rss_url, '')) = '' THEN 'manual'
                    ELSE 'rss'
                END,
                COALESCE(language, 'zh-CN'),
                COALESCE(priority, 50),
                COALESCE(is_active, 1),
                last_fetched_at,
                COALESCE(last_fetch_status, 'idle'),
                last_fetch_error,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM sources_legacy
            """
        )
        connection.exec_driver_sql("DROP TABLE sources_legacy")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _run_sqlite_migrations() -> None:
    _migrate_sources_table()
    _ensure_sqlite_column("articles", "core_score", "core_score REAL")
    _ensure_sqlite_column("articles", "core_reason", "core_reason TEXT")
    _ensure_sqlite_column("articles", "analysis_status", "analysis_status TEXT DEFAULT 'pending'")
    _ensure_sqlite_column("articles", "analysis_error", "analysis_error TEXT")
    _ensure_sqlite_column("articles", "last_analyzed_at", "last_analyzed_at DATETIME")
    _ensure_sqlite_column("reading_logs", "created_at", "created_at DATETIME")
    _ensure_sqlite_column("weekly_reviews", "primary_article_ids", "primary_article_ids JSON DEFAULT '[]'")
    _ensure_sqlite_column("weekly_reviews", "supplemental_article_ids", "supplemental_article_ids JSON DEFAULT '[]'")
    _ensure_sqlite_column("weekly_reviews", "primary_topic_key", "primary_topic_key TEXT")
    _ensure_sqlite_column("weekly_reviews", "supplemental_topic_key", "supplemental_topic_key TEXT")
    _ensure_sqlite_column("weekly_reviews", "article_plan_metadata", "article_plan_metadata JSON DEFAULT '[]'")
    _ensure_sqlite_column("import_jobs", "discovered_urls", "discovered_urls INTEGER DEFAULT 0")
    _ensure_sqlite_column("import_job_items", "strategy_used", "strategy_used TEXT")
    _ensure_sqlite_column("import_job_items", "discovered_urls", "discovered_urls INTEGER DEFAULT 0")


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _run_sqlite_migrations()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
