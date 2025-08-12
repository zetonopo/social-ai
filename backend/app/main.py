from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.core.redis_client import RedisClient
from app.routers import auth, users, admin, usage
from app.core.database import engine, get_db
from app.models import *  # Import all models to ensure they're registered
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.background_tasks import background_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global Redis client
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client
    
    # Startup
    logger.info("Starting up Social AI SaaS Backend")
    
    # Initialize Redis client
    redis_client = RedisClient()
    try:
        # Redis client will connect on first use
        logger.info("Redis client created successfully")
    except Exception as e:
        logger.warning(f"Redis client creation failed: {e}")
    
    # Create database tables
    from app.models.user import Base
    Base.metadata.create_all(bind=engine)
    
    # Store Redis client in app state
    app.state.redis = redis_client
    
    # Initialize and start background tasks
    try:
        await background_tasks.initialize()
        await background_tasks.start()
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.warning(f"Background tasks initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Social AI SaaS Backend")
    await background_tasks.stop()
    if redis_client:
        logger.info("Redis client cleanup completed")


# Create FastAPI application
app = FastAPI(
    title="Social AI SaaS API",
    description="A SaaS platform for AI-powered social media tools",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (after CORS)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware wrapper."""
    if hasattr(app.state, 'redis') and app.state.redis:
        middleware = RateLimitMiddleware(app.state.redis)
        return await middleware.dispatch(request, call_next)
    else:
        # If Redis is not available, just continue without rate limiting
        return await call_next(request)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "social-ai-backend"}


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Social AI SaaS API",
        "version": "1.0.0",
        "docs": "/docs"
    }
