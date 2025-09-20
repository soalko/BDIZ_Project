# ===== SQLAlchemy =====
from sqlalchemy import (
    create_engine
)

from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL


# ===== Files =====
from db.config import PgConfig



# -------------------------------
# Создание Engine и схемы
# -------------------------------
def make_engine(cfg: PgConfig) -> Engine:
    drivername_map = {
        "psycopg2": "postgresql+psycopg2",
        "psycopg": "postgresql+psycopg",
        "pg8000": "postgresql+pg8000",
    }
    drivername = drivername_map.get(cfg.driver, "postgresql+psycopg2")

    if cfg.driver in ("psycopg2", "psycopg"):
        query = {
            "sslmode": cfg.sslmode,
            "application_name": "QtEduDemo",
            "connect_timeout": str(cfg.connect_timeout),
        }
    else:  # pg8000 — только app_name
        query = {"application_name": "QtEduDemo"}

    url = URL.create(
        drivername=drivername,
        username=cfg.user,
        password=cfg.password,
        host=cfg.host,
        port=cfg.port,
        database=cfg.dbname,
        query=query,
    )

    engine = create_engine(url, future=True, pool_pre_ping=True)
    # sanity ping
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    return engine