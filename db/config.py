from dataclasses import dataclass



# -------------------------------
# Конфигурация подключения
# -------------------------------
@dataclass
class PgConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = "airport"
    user: str = "postgres"
    password: str = "root"
    sslmode: str = "prefer"  # для psycopg2/psycopg
    connect_timeout: int = 5  # секунды
    driver: str = "psycopg2"  # psycopg2 | psycopg | pg8000