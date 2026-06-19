import os
from pathlib import Path
from urllib.parse import quote_plus, urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        # If the URL references an sslrootcert file that does not exist on this
        # host, strip that param so psycopg can still connect.
        if "sslrootcert=" in explicit_url:
            parsed = urlparse(explicit_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            cert_path = params.get("sslrootcert", [None])[0]
            if cert_path and not Path(cert_path).exists():
                params.pop("sslrootcert", None)
                # Downgrade sslmode to require when cert file is absent
                if params.get("sslmode", [""])[0] == "verify-full":
                    params["sslmode"] = ["require"]
                new_query = urlencode({k: v[0] for k, v in params.items()})
                explicit_url = urlunparse(parsed._replace(query=new_query))
        return explicit_url

    # Prefer RDS-style env vars when host is provided.
    rds_host = os.getenv("RDSHOST")
    if rds_host:
        rds_port = os.getenv("RDSPORT", "5432")
        rds_db = os.getenv("RDSDB", "postgres")
        rds_user = os.getenv("RDSUSER", "postgres")
        rds_password = quote_plus(os.getenv("RDSPASSWORD", ""))
        sslmode = os.getenv("DB_SSLMODE", "verify-full")
        default_cert = Path(__file__).resolve().parents[1] / "global-bundle.pem"
        sslrootcert = os.getenv("DB_SSLROOTCERT", str(default_cert))
        return (
            "postgresql+psycopg://"
            f"{rds_user}:{rds_password}@{rds_host}:{rds_port}/{rds_db}"
            f"?sslmode={sslmode}&sslrootcert={sslrootcert}"
        )

    return "sqlite:///./mygardenos_dev.db"


DATABASE_URL = _build_database_url()
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)


if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
