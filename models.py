import enum
import json

from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, JSON, DateTime, func, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    active = Column(Boolean, nullable=False, server_default="true")

class AccountSide(enum.Enum):
    Assets = "Assets"
    Liabilities = "Liabilities"
    Income = "Income"
    Expenses = "Expenses"
    Equity = "Equity"

class TransactionDirection(enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    TRANSFER = "transfer"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    name = Column(String(100), nullable=False)
    side = Column(Enum(AccountSide), nullable=False)
    path = Column(String(255), unique=True, index=True)

    children = relationship("Account", backref="parent", remote_side=[id])
    configs = relationship("AccountConfig", back_populates="account")
    rules = relationship("Rule", foreign_keys="[Rule.account_id]", back_populates="account")
    entries = relationship("Entry", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, parent_id={self.parent_id}, name={self.name}, side={self.side}, path={self.path})>"

class AccountConfig(Base):
    __tablename__ = "account_configs"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    parser = Column(String(100), nullable=False)
    raw_extension = Column(String(100), nullable=False, server_default="csv")

    account = relationship("Account", back_populates="configs")
    
    def __repr__(self):
        return f"<AccountConfig(id={self.id}, account_id={self.account_id}, parser={self.parser}, raw_extension={self.raw_extension})>"

class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    target_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    conditions = Column(JSON, nullable=False)

    account = relationship("Account", foreign_keys=[account_id], back_populates="rules")
    target_account = relationship("Account", foreign_keys=[target_account_id])
    
    def __repr__(self):
        return f"<Rule(id={self.id}, account_id={self.account_id}, target_account_id={self.target_account_id}, conditions={self.conditions})>"

class RawImport(Base):
    __tablename__ = "raw_imports"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    raw_data = Column(JSON, nullable=False)
    row_hash = Column(String(64), unique=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False)
    
    batch = relationship("Import", back_populates="raw_rows")
    entry = relationship("Entry", back_populates="raw_import")
    
    def __repr__(self):
        return f"<RawImport(id={self.id}, account_id={self.account_id}, raw_data={self.raw_data}, row_hash={self.row_hash}, import_id={self.import_id})>"

    @property
    def details(self):
        return json.loads(self.raw_data)

class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    file_name = Column(String(255), nullable=False)
    row_count = Column(Integer)
    imported_count = Column(Integer)
    min_date = Column(DateTime)
    max_date = Column(DateTime)
    success = Column(Boolean)
    
    raw_rows = relationship("RawImport", back_populates="batch")
    
    def __repr__(self):
        return f"<RawImport(id={self.id}, account_id={self.account_id}, file_name={self.file_name}, row_count={self.row_count}, imported_count={self.imported_count}, min_date={self.min_date}, max_date={self.max_date}, success={self.success})>"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    description = Column(String(255))
    source = Column(String(255), nullable=False)
    direction = Column(Enum(TransactionDirection), nullable=False)
    source_raw_import_id = Column(Integer, ForeignKey("raw_imports.id"), nullable=False)
    is_temporary = Column(Boolean, nullable=False, server_default="false")

    entries = relationship("Entry", back_populates="transaction")
    
    def __repr__(self):
        return f"<RawImport(id={self.id}, date={self.date}, description={self.description}, source={self.source}, direction={self.direction}, source_raw_import_id={self.source_raw_import_id}, is_temporary={self.is_temporary})>"

    @property
    def amount(self):
        if not self.entries:
            return 0
        return sum([entry.amount_huf for entry in self.entries if entry.amount_huf > 0]) * (-1 if self.direction.value == "outgoing" else 1)
    @property
    def base_account_name(self):
        entry = next(filter(lambda e: e.is_base, self.entries), None)
        return entry.account_name if entry else ""
    @property
    def base_account_path(self):
        entry = next(filter(lambda e: e.is_base, self.entries), None)
        return entry.account_path if entry else ""
    @property
    def target_account_names(self):
        return " | ".join(map(lambda e2: e2.account_name, filter(lambda e: not e.is_base, self.entries)))
    @property
    def target_account_paths(self):
        return " | ".join(map(lambda e2: e2.account_path, filter(lambda e: not e.is_base, self.entries)))
    @property
    def raw_imports(self):
        return list({e.raw_import.id: e.raw_import for e in self.entries}.values())

class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    raw_import_id = Column(Integer, ForeignKey("raw_imports.id"), nullable=True)
    is_base = Column(Boolean, nullable=False)
    amount_huf = Column(Numeric(precision=20, scale=4), nullable=False)
    amount_orig = Column(Numeric(precision=20, scale=4), nullable=False)
    exchange_rate = Column(Numeric(precision=20, scale=4), nullable=False, server_default="1")
    currency = Column(String(3), nullable=False, server_default="HUF")
    
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="entries")
    raw_import = relationship("RawImport", back_populates="entry")
    
    def __repr__(self):
        return f"<Entry(id={self.id}, transaction_id={self.transaction_id}, account_id={self.account_id}, raw_import_id={self.raw_import_id}, is_base={self.is_base}, amount_huf={self.amount_huf}, amount_orig={self.amount_orig}, exchange_rate={self.exchange_rate}, currency={self.currency})>"

    @property
    def account_name(self):
        return self.account.name
    @property
    def account_path(self):
        return self.account.path
