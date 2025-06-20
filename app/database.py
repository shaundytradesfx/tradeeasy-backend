import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Get database URL from environment variable or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")

# Import performance optimizer
try:
    from .performance import db_optimizer
    PERFORMANCE_MONITORING = True
except ImportError:
    # Handle circular import during initial setup
    db_optimizer = None
    PERFORMANCE_MONITORING = False

def get_optimized_engine_params(database_url: str):
    """Get optimized engine parameters based on database type."""
    if "postgresql" in database_url.lower():
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),  # 1 hour
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",
            "connect_args": {
                "options": "-c timezone=utc",
                "application_name": "tradeeasy_backend",
                "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
                "statement_timeout": int(os.getenv("DB_STATEMENT_TIMEOUT", "30000")),  # 30 seconds
            }
        }
    elif "sqlite" in database_url.lower():
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_pre_ping": True,
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "connect_args": {
                "check_same_thread": False,
                "timeout": int(os.getenv("DB_TIMEOUT", "20")),
                "isolation_level": None,
            }
        }
    else:
        # Default parameters for other databases
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        }

def create_optimized_engine(database_url: str):
    """Create an optimized database engine with performance monitoring."""
    try:
        # Get optimized parameters
        engine_params = get_optimized_engine_params(database_url)
        
        # Create engine with optimized parameters
        engine = create_engine(database_url, **engine_params)
        
        # Add performance monitoring if available
        if PERFORMANCE_MONITORING and db_optimizer:
            db_optimizer.optimize_engine_config(engine)
            logger.info("Performance monitoring enabled for database engine")
        
        # Add connection event listeners for logging
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            logger.debug("New database connection established")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Database connection returned to pool")
        
        logger.info(f"Database engine created with optimized parameters: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        return engine
        
    except Exception as e:
        logger.error(f"Error creating optimized database engine: {e}")
        raise

# If no DATABASE_URL is provided or there's an issue with PostgreSQL,
# use SQLite as a fallback for development
if not DATABASE_URL:
    SQLITE_URL = "sqlite:///./tradeeasy.db"
    logger.info(f"No DATABASE_URL found, using SQLite: {SQLITE_URL}")
    engine = create_optimized_engine(SQLITE_URL)
else:
    try:
        # Attempt to create optimized PostgreSQL engine
        engine = create_optimized_engine(DATABASE_URL)
        logger.info("Successfully connected to PostgreSQL with optimized configuration")
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        # Fall back to SQLite
        SQLITE_URL = "sqlite:///./tradeeasy.db"
        logger.warning(f"Falling back to SQLite: {SQLITE_URL}")
        engine = create_optimized_engine(SQLITE_URL)

# Create SessionLocal class for database sessions with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent lazy loading issues
)

# Create Base class for declarative models using the updated method
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """
    Dependency function that yields a SQLAlchemy database session.
    This session is automatically closed when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_performance_indexes(engine):
    """
    Create performance indexes for existing databases.
    
    This function safely adds indexes to databases that might not have them,
    especially useful for upgrading existing installations.
    """
    import logging
    from sqlalchemy import text, inspect
    
    logger = logging.getLogger(__name__)
    
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            
            # Define indexes to create if they don't exist
            indexes_to_create = [
                # Users table indexes
                ("users", "idx_users_username", "CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)"),
                ("users", "idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"),
                ("users", "idx_users_created_at", "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at)"),
                
                # Assets table indexes
                ("assets", "idx_assets_symbol", "CREATE INDEX IF NOT EXISTS idx_assets_symbol ON assets (symbol)"),
                ("assets", "idx_assets_type", "CREATE INDEX IF NOT EXISTS idx_assets_type ON assets (type)"),
                ("assets", "idx_asset_symbol_type", "CREATE INDEX IF NOT EXISTS idx_asset_symbol_type ON assets (symbol, type)"),
                
                # Articles table indexes
                ("articles", "idx_articles_source", "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles (source)"),
                ("articles", "idx_articles_published_at", "CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles (published_at)"),
                ("articles", "idx_article_published_source", "CREATE INDEX IF NOT EXISTS idx_article_published_source ON articles (published_at, source)"),
                
                # Sentiments table indexes
                ("sentiments", "idx_sentiments_article_id", "CREATE INDEX IF NOT EXISTS idx_sentiments_article_id ON sentiments (article_id)"),
                ("sentiments", "idx_sentiment_article_scores", "CREATE INDEX IF NOT EXISTS idx_sentiment_article_scores ON sentiments (article_id, lexicon_score, finbert_score)"),
                
                # SentimentAggregates table indexes
                ("sentiment_aggregates", "idx_sentiment_agg_asset_id", "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_asset_id ON sentiment_aggregates (asset_id)"),
                ("sentiment_aggregates", "idx_sentiment_agg_timestamp", "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_timestamp ON sentiment_aggregates (timestamp)"),
                ("sentiment_aggregates", "idx_sentiment_agg_asset_timestamp", "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_asset_timestamp ON sentiment_aggregates (asset_id, timestamp)"),
                ("sentiment_aggregates", "idx_sentiment_agg_timestamp_score", "CREATE INDEX IF NOT EXISTS idx_sentiment_agg_timestamp_score ON sentiment_aggregates (timestamp, avg_score)"),
                
                # Watchlists table indexes
                ("watchlists", "idx_watchlists_user_id", "CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists (user_id)"),
                ("watchlists", "idx_watchlists_asset_id", "CREATE INDEX IF NOT EXISTS idx_watchlists_asset_id ON watchlists (asset_id)"),
                ("watchlists", "idx_watchlists_created_at", "CREATE INDEX IF NOT EXISTS idx_watchlists_created_at ON watchlists (created_at)"),
                ("watchlists", "idx_watchlist_user_created", "CREATE INDEX IF NOT EXISTS idx_watchlist_user_created ON watchlists (user_id, created_at)"),
                
                # Alerts table indexes
                ("alerts", "idx_alerts_user_id", "CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts (user_id)"),
                ("alerts", "idx_alerts_asset_id", "CREATE INDEX IF NOT EXISTS idx_alerts_asset_id ON alerts (asset_id)"),
                ("alerts", "idx_alerts_direction", "CREATE INDEX IF NOT EXISTS idx_alerts_direction ON alerts (direction)"),
                ("alerts", "idx_alerts_created_at", "CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at)"),
                ("alerts", "idx_alerts_triggered_at", "CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON alerts (triggered_at)"),
                ("alerts", "idx_alerts_is_active", "CREATE INDEX IF NOT EXISTS idx_alerts_is_active ON alerts (is_active)"),
                ("alerts", "idx_alert_user_active", "CREATE INDEX IF NOT EXISTS idx_alert_user_active ON alerts (user_id, is_active)"),
                ("alerts", "idx_alert_asset_active", "CREATE INDEX IF NOT EXISTS idx_alert_asset_active ON alerts (asset_id, is_active)"),
                ("alerts", "idx_alert_asset_active_threshold", "CREATE INDEX IF NOT EXISTS idx_alert_asset_active_threshold ON alerts (asset_id, is_active, threshold)"),
            ]
            
            # Get existing indexes
            existing_indexes = set()
            for table_name in ["users", "assets", "articles", "sentiments", "sentiment_aggregates", "watchlists", "alerts"]:
                if inspector.has_table(table_name):
                    for index_info in inspector.get_indexes(table_name):
                        existing_indexes.add(index_info['name'])
            
            # Create missing indexes
            created_count = 0
            for table_name, index_name, create_sql in indexes_to_create:
                if inspector.has_table(table_name) and index_name not in existing_indexes:
                    try:
                        conn.execute(text(create_sql))
                        conn.commit()
                        created_count += 1
                        logger.info(f"Created index: {index_name} on table {table_name}")
                    except Exception as e:
                        logger.warning(f"Failed to create index {index_name}: {e}")
                        conn.rollback()
            
            logger.info(f"Database index creation complete. Created {created_count} new indexes.")
            return created_count
            
    except Exception as e:
        logger.error(f"Error creating performance indexes: {e}")
        return 0
