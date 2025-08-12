import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.redis_client import RedisClient
from app.services.usage_tracking_service import UsageTrackingService
from app.core.config import settings

logger = logging.getLogger(__name__)


class BackgroundTasks:
    def __init__(self):
        self.redis_client = None
        self.running = False
        
    async def initialize(self):
        """Initialize background tasks."""
        self.redis_client = RedisClient()
        try:
            await self.redis_client.initialize()
            logger.info("Background tasks Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client for background tasks: {e}")
            raise
    
    async def start(self):
        """Start all background tasks."""
        if self.running:
            logger.warning("Background tasks already running")
            return
            
        self.running = True
        logger.info("Starting background tasks")
        
        # Start usage data persistence task
        asyncio.create_task(self._usage_persistence_task())
        
        # Start rate limit cleanup task
        asyncio.create_task(self._rate_limit_cleanup_task())
        
        # Start cache cleanup task
        asyncio.create_task(self._cache_cleanup_task())
        
    async def stop(self):
        """Stop all background tasks."""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Background tasks stopped")
    
    async def _usage_persistence_task(self):
        """Periodically persist usage data from Redis to PostgreSQL."""
        logger.info("Starting usage persistence task")
        
        while self.running:
            try:
                # Run every hour at the 5-minute mark (e.g., 12:05, 13:05, etc.)
                now = datetime.utcnow()
                next_run = now.replace(minute=5, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(hours=1)
                
                sleep_seconds = (next_run - now).total_seconds()
                logger.info(f"Next usage persistence run in {sleep_seconds:.0f} seconds at {next_run}")
                
                await asyncio.sleep(sleep_seconds)
                
                if not self.running:
                    break
                
                # Perform persistence
                db = SessionLocal()
                try:
                    usage_service = UsageTrackingService(db, self.redis_client)
                    await usage_service.persist_usage_data()
                    logger.info("Usage data persistence completed successfully")
                except Exception as e:
                    logger.error(f"Usage data persistence failed: {e}")
                finally:
                    db.close()
                    
            except asyncio.CancelledError:
                logger.info("Usage persistence task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in usage persistence task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _rate_limit_cleanup_task(self):
        """Periodically clean up expired rate limit keys."""
        logger.info("Starting rate limit cleanup task")
        
        while self.running:
            try:
                # Run every 15 minutes
                await asyncio.sleep(900)
                
                if not self.running:
                    break
                
                # Clean up expired rate limit keys
                await self._cleanup_expired_rate_limits()
                logger.debug("Rate limit cleanup completed")
                
            except asyncio.CancelledError:
                logger.info("Rate limit cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in rate limit cleanup task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _cache_cleanup_task(self):
        """Periodically clean up expired cache entries."""
        logger.info("Starting cache cleanup task")
        
        while self.running:
            try:
                # Run every 30 minutes
                await asyncio.sleep(1800)
                
                if not self.running:
                    break
                
                # Clean up expired cache entries
                await self._cleanup_expired_cache()
                logger.debug("Cache cleanup completed")
                
            except asyncio.CancelledError:
                logger.info("Cache cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _cleanup_expired_rate_limits(self):
        """Clean up expired rate limit keys from Redis."""
        try:
            # Get all rate limit keys
            pattern = "rate_limit:*"
            keys = await self.redis_client.scan_iter(pattern=pattern)
            
            expired_keys = []
            now = datetime.utcnow()
            
            for key in keys:
                # Check if key has TTL
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    # Determine appropriate TTL based on key type
                    if ":minute:" in key:
                        await self.redis_client.expire(key, 120)  # 2 minutes
                    elif ":hour:" in key:
                        await self.redis_client.expire(key, 7200)  # 2 hours
                    elif ":day:" in key:
                        await self.redis_client.expire(key, 172800)  # 2 days
                    elif ":month:" in key:
                        await self.redis_client.expire(key, 2678400)  # 31 days
                elif ttl == -2:  # Key doesn't exist
                    expired_keys.append(key)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit keys")
                
        except Exception as e:
            logger.error(f"Error cleaning up rate limits: {e}")
    
    async def _cleanup_expired_cache(self):
        """Clean up expired cache entries from Redis."""
        try:
            # Get all cache keys
            patterns = [
                "user_subscription:*",
                "user_plan:*", 
                "cached_plans:*",
                "system_stats:*"
            ]
            
            total_cleaned = 0
            for pattern in patterns:
                keys = await self.redis_client.scan_iter(pattern=pattern)
                expired_keys = []
                
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        expired_keys.append(key)
                    elif ttl == -1:  # No expiration, set appropriate TTL
                        if "user_subscription:" in key or "user_plan:" in key:
                            await self.redis_client.expire(key, 3600)  # 1 hour
                        elif "cached_plans:" in key:
                            await self.redis_client.expire(key, 7200)  # 2 hours
                        elif "system_stats:" in key:
                            await self.redis_client.expire(key, 1800)  # 30 minutes
                
                total_cleaned += len(expired_keys)
            
            if total_cleaned > 0:
                logger.debug(f"Cleaned up {total_cleaned} expired cache keys")
                
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    async def manual_usage_persistence(self):
        """Manually trigger usage data persistence (for testing/admin)."""
        if not self.redis_client:
            raise RuntimeError("Background tasks not initialized")
        
        db = SessionLocal()
        try:
            usage_service = UsageTrackingService(db, self.redis_client)
            await usage_service.persist_usage_data()
            logger.info("Manual usage data persistence completed")
        finally:
            db.close()


# Global instance
background_tasks = BackgroundTasks()
