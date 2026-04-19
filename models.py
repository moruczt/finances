import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, JSON, DateTime, func, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    created_at = Column(DateTime, server_default=func.now())

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

    children = relationship("Account", backref="parent", remote_side=[id])
    configs = relationship("AccountConfig", back_populates="account")
    rules = relationship("Rule", foreign_keys="[Rule.account_id]", back_populates="account")
    entries = relationship("Entry", back_populates="account")

class AccountConfig(Base):
    __tablename__ = "account_configs"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    parser = Column(String(100), nullable=False)
    raw_extension = Column(String(100), nullable=False, server_default="csv")

    account = relationship("Account", back_populates="configs")

class Rule(Base):
    __tablename__ = "rule"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    target_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    conditions = Column(JSON, nullable=False)

    account = relationship("Account", foreign_keys=[account_id], back_populates="rules")
    target_account = relationship("Account", foreign_keys=[target_account_id])

class RawImport(Base):
    __tablename__ = "raw_imports"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    raw_data = Column(JSON, nullable=False)
    row_hash = Column(String(64), unique=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False)
    
    batch = relationship("Imports", back_populates="raw_rows")

class Imports(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    file_name = Column(String(255), nullable=False)
    row_count = Column(Integer)
    imported_count = Column(Integer)
    min_date = Column(DateTime)
    max_date = Column(DateTime)
    success = Column(Boolean, nullable=False)
    
    raw_rows = relationship("RawImport", back_populates="batch")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    description = Column(String(255))
    source = Column(String(255))

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

    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="entries")