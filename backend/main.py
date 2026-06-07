from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from redis import Redis
from datetime import datetime
from typing import List, Optional
import os
from json import loads, dumps
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database configuration from environment variables (Docker Compose defaults)
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "user_password")
DB_NAME = os.getenv("DB_NAME", "sales")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ============================================================================
# SQLMODEL CLASSES
# ============================================================================

class Items(SQLModel, table=True):
    """Product/Item model for the sales inventory.

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
    """Request model for updating items (all fields optional).
    I do not like how I need to create threem odel classes for one table.
    But this enofrces the API contract and prevents clients from sending invalid data."""
    name: Optional[str] = None
    price: Optional[float] = None
    available: Optional[int] = None

# ============================================================================
# LIFESPAN - STARTUP AND SHUTDOWN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the lifespan of the FastAPI application.
    
    Startup phase:
    - Initialize database engine and store session factory in app.state
    - Initialize Redis cache connection in app.state
    
    Shutdown phase:
    - Close Redis connection and dispose database engine
    - Close mySQL sessions to prevent resource leaks
    """
    # STARTUP
    print("🚀 Starting up application...")
    
    # Initialize the database engine
    app.state.engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using them
        pool_size=10,
        max_overflow=20,
    )
  
    # Store session factory in app.state
    app.state.sqlSession = Session(app.state.engine)
    print("✅ Database engine initialized")
    
    # Initialize Redis cache connection
    app.state.cache = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True
    )
    print("✅ Redis cache connection established")
    
    yield  # Application runs here
    
    # SHUTDOWN
    print("🛑 Shutting down application...")
    
    # Close Redis connection
    if hasattr(app.state, 'cache'):
        app.state.cache.close()
        print("✅ Redis cache connection closed")
    
    # Close database sessions and dispose engine
    if hasattr(app.state, 'sqlSession'):
        app.state.sqlSession.close()
        app.state.engine.dispose()
        print("✅ Database sessions closed")
    
    # Dispose database engine
    print("✅ Shutdown Complete")

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="Sales Dashboard API", version="2.0.0", lifespan=lifespan)

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
def read_items(request: Request):
    cached_items = request.app.state.cache.get("items_cache")
    if cached_items:
        print("⚡️ Cache hit for /items")
        return [Items.model_validate_json(item) for item in loads(cached_items)]  # Convert string back to list of dicts
    else:
        print("⚡️ Cache miss for /items, querying database...")
        session = request.app.state.sqlSession
        items = session.exec(select(Items)).all()
        request.app.state.cache.set("items_cache", dumps([item.model_dump_json() for item in items]), ex=5)  
        return items

@app.get("/items/{item_id}", response_model=Items)
def read_item(item_id: int, request: Request):
    cached_item = request.app.state.cache.get(f"item_{item_id}")
    if cached_item:
        print(f"⚡️ Cache hit for /items/{item_id}")
        return Items.model_validate_json(cached_item)
    else:
        print(f"⚡️ Cache miss for /items/{item_id}, querying database...")
        session = request.app.state.sqlSession
        item = session.exec(select(Items).where(Items.id == item_id)).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        request.app.state.cache.set(f"item_{item_id}", item.model_dump_json(), ex=5)
        return item

@app.post("/items", response_model=Items)
def create_item(item: ItemsCreate, request: Request):
    session = request.app.state.sqlSession
    db_item = Items.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@app.put("/items/{item_id}", response_model=Items)
def update_item(
    item_id: int,
    item_update: ItemsUpdate,
    request: Request
):
    session = request.app.state.sqlSession
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
def delete_item(item_id: int, request: Request):
    session = request.app.state.sqlSession
    db_item = session.exec(select(Items).where(Items.id == item_id)).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    session.delete(db_item)
    session.commit()
    request.app.state.cache.delete(f"item_{item_id}")
    return {"deleted": True, "id": item_id}