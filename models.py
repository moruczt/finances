import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, JSON, DateTime, func
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass

class AccountSide(enum.Enum):
    Assets = "Assets"
    Liabilities = "Liabilities"
    Income = "Income"
    Expenses = "Expenses"
    Equity = "Equity"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    name = Column(String(100), nullable=False)
    side = Column(Enum(AccountSide), nullable=False)
    path = Column(String(255), unique=True)
    created_at = Column(DateTime, server_default=func.now())
    test = Column(String(100))

    children = relationship("Account", backref="parent", remote_side=[id])

class AccountConfig(Base):
    __tablename__ = "account_configs"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    parser = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    children = relationship("Account", backref="parent", remote_side=[id])

class Rule(Base):
    __tablename__ = "rule"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    target_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    conditions = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    children = relationship("Account", backref="parent", remote_side=[id])

class RawImport(Base):
    __tablename__ = "raw_imports"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    raw_data = Column(JSON, nullable=False)
    row_hash = Column(String(64), unique=True, index=True)
    source_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    description = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    entries = relationship("Entry", back_populates="transaction")

class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    raw_import_id = Column(Integer, ForeignKey("raw_imports.id"), nullable=True)
    amount_huf = Column(Numeric(precision=20, scale=4), nullable=False)
    amount_orig = Column(Numeric(precision=20, scale=4), nullable=False)
    exchange_rate = Column(Numeric(precision=20, scale=4), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    transaction = relationship("Transaction", back_populates="entries")