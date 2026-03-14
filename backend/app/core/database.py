from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Neon requires SSL connection
connect_args = {}
if "neon.tech" in settings.DATABASE_URL:
    connect_args = {"sslmode": "require"}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300, 
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
    connect_args={"sslmode": "require"}, 
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    from app.models.base import Base
    import app.models  # noqa
    Base.metadata.create_all(bind=engine)
    print("✅ All database tables created successfully.")