from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime
from typing import Annotated, List, Optional
import os

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Build database URL from environment variables (Docker Compose defaults)
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "user_password")
DB_NAME = os.getenv("DB_NAME", "sales")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,
    max_overflow=20,
)

# ============================================================================
# SQLMODEL CLASSES
# ============================================================================

class Items(SQLModel, table=True):
    """Product/Item model for the sales inventory.
    
    This model represents a product in the catalog with pricing and availability
    information. It mirrors the 'items' table in the MySQL database.
    
    Attributes:
        id: Primary key, auto-incremented
        name: Product name (e.g., "iPhone 15 Pro")
        price: Price in currency units (e.g., 999.99)
        available: Number of units in stock
        timestamp: Last modified datetime, auto-updated
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    price: float
    available: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ItemsCreate(SQLModel):
    """Request model for creating new Itemss (no id/timestamp)."""
    name: str
    price: float
    available: int


class ItemsUpdate(SQLModel):
    """Request model for updating items (all fields optional)."""
    name: Optional[str] = None
    price: Optional[float] = None
    available: Optional[int] = None


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def get_session() -> Session:
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="Sales Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def read_root():
    return {"message": "Welcome to the Sales Dashboard API!"}


@app.get("/items", response_model=List[Items])
def read_items(session: SessionDep):
    items = session.exec(select(Items)).all()
    return items


@app.get("/items/{item_id}", response_model=Items)
def read_item(item_id: int, session: SessionDep):
    item = session.exec(select(Items).where(Item.id == Items_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", response_model=Items)
def create_item(item: ItemsCreate, session: SessionDep):
    db_item = Items.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.put("/items/{item_id}", response_model=Items)
def update_item(
    item_id: int,
    item_update: ItemsUpdate,
    session: SessionDep
):
    db_item = session.exec(select(Items).where(Items.id == item_id)).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update only provided fields
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, session: SessionDep):
    db_item = session.exec(select(Items).where(Items.id == item_id)).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    session.delete(db_item)
    session.commit()
    return {"deleted": True, "id": item_id}