from sqlalchemy import Column, Integer, String

from .bootstrap_db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "webwise"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)
    role = Column(String, default="client")
    is_active = Column(Integer, default=1)  # 1 = true
    factoring_company = Column(String, nullable=True)
    referral_status = Column(String, default="NONE")
    referred_by = Column(String, nullable=True)
    referral_code = Column(String, nullable=True, index=True)
    location_code = Column(String, nullable=True, index=True)  # e.g., "LOMBARDI_01", "PITCHER_02" for truck stop tracking