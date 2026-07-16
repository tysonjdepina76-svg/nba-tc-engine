from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class GradedPick(Base):
    __tablename__ = "graded_picks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String(10), nullable=False, index=True)
    player_name = Column(String(100), nullable=False)
    stat = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    line = Column(Float, nullable=False)
    tc_projection = Column(Float, nullable=False)
    edge = Column(Float, nullable=False)
    signal = Column(String(10), nullable=True)
    actual_value = Column(Float, nullable=True)
    hit = Column(Boolean, nullable=True)
    game_date = Column(DateTime, nullable=False)
    graded_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    features = Column(JSON, nullable=True)


def get_session(database_url: str):
    engine = create_engine(database_url)
    return sessionmaker(bind=engine)()


def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
