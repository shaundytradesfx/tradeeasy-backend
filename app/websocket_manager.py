"""
WebSocket Connection Manager for Real-time Sentiment Broadcasting.

This module manages WebSocket connections and handles broadcasting sentiment
updates to connected clients when new aggregates are processed.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts real-time updates.
    """

    def __init__(self):
        # Store active connections
        self.active_connections: List[WebSocket] = []
        # Track connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_info: Optional[Dict[str, Any]] = None):
        """
        Accept a new WebSocket connection and add it to active connections.
        
        Args:
            websocket: The WebSocket connection
            client_info: Optional metadata about the client
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Store connection metadata
        self.connection_info[websocket] = {
            "connected_at": datetime.utcnow(),
            "client_info": client_info or {},
            "message_count": 0
        }
        
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to TradeEasy sentiment stream",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(self.active_connections)
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        if websocket in self.connection_info:
            connection_duration = datetime.utcnow() - self.connection_info[websocket]["connected_at"]
            logger.info(f"WebSocket client disconnected after {connection_duration}. "
                       f"Remaining active: {len(self.active_connections)}")
            del self.connection_info[websocket]

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: The message to send (will be JSON serialized)
            websocket: The target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message, default=str))
            
            # Update message count
            if websocket in self.connection_info:
                self.connection_info[websocket]["message_count"] += 1
                
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Remove problematic connection
            self.disconnect(websocket)

    async def broadcast_message(self, message: Dict[str, Any]):
        """
        Broadcast a message to all active WebSocket connections.
        
        Args:
            message: The message to broadcast (will be JSON serialized)
        """
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return

        logger.info(f"Broadcasting message to {len(self.active_connections)} clients")
        
        # Keep track of connections to remove
        dead_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
                
                # Update message count
                if connection in self.connection_info:
                    self.connection_info[connection]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for dead_connection in dead_connections:
            self.disconnect(dead_connection)

    async def broadcast_sentiment_update(self, article_data: Dict[str, Any], sentiment_data: Dict[str, Any]):
        """
        Broadcast a sentiment update for a newly processed article.
        
        Args:
            article_data: Information about the processed article
            sentiment_data: Sentiment analysis results
        """
        message = {
            "type": "sentiment_update",
            "timestamp": datetime.utcnow().isoformat(),
            "article": {
                "id": str(article_data.get("id", "")),
                "title": article_data.get("title", ""),
                "source": article_data.get("source", ""),
                "url": article_data.get("url", ""),
                "published_at": article_data.get("published_at", ""),
                "asset_class": article_data.get("asset_class", "unknown")
            },
            "sentiment": {
                "lexicon_score": sentiment_data.get("lexicon_score"),
                "finbert_score": sentiment_data.get("finbert_score"),
                "overall_sentiment": self._categorize_sentiment(
                    sentiment_data.get("finbert_score", 0.0)
                )
            },
            "metadata": {
                "processing_time": sentiment_data.get("processing_time", 0),
                "active_connections": len(self.active_connections)
            }
        }
        
        await self.broadcast_message(message)

    async def broadcast_aggregate_update(self, asset_symbol: str, aggregate_data: Dict[str, Any]):
        """
        Broadcast an update when sentiment aggregates are computed.
        
        Args:
            asset_symbol: The asset symbol for the aggregate
            aggregate_data: The computed aggregate data
        """
        message = {
            "type": "aggregate_update",
            "timestamp": datetime.utcnow().isoformat(),
            "asset": {
                "symbol": asset_symbol,
                "avg_sentiment": aggregate_data.get("avg_score", 0.0),
                "article_count": aggregate_data.get("article_count", 0),
                "time_period": aggregate_data.get("time_period", "1h")
            },
            "sentiment_category": self._categorize_sentiment(
                aggregate_data.get("avg_score", 0.0)
            ),
            "metadata": {
                "active_connections": len(self.active_connections)
            }
        }
        
        await self.broadcast_message(message)

    async def broadcast_alert_triggered(self, alert_data: Dict[str, Any]):
        """
        Broadcast when an alert is triggered.
        
        Args:
            alert_data: Information about the triggered alert
        """
        message = {
            "type": "alert_triggered",
            "timestamp": datetime.utcnow().isoformat(),
            "alert": {
                "id": str(alert_data.get("alert_id", "")),
                "asset_symbol": alert_data.get("asset_symbol", ""),
                "threshold": alert_data.get("threshold", 0.0),
                "direction": alert_data.get("direction", ""),
                "current_sentiment": alert_data.get("current_sentiment", 0.0),
                "user_id": str(alert_data.get("user_id", ""))
            },
            "metadata": {
                "active_connections": len(self.active_connections)
            }
        }
        
        await self.broadcast_message(message)

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current WebSocket connections.
        
        Returns:
            Dictionary with connection statistics
        """
        total_messages = sum(
            info["message_count"] for info in self.connection_info.values()
        )
        
        return {
            "active_connections": len(self.active_connections),
            "total_messages_sent": total_messages,
            "connections": [
                {
                    "connected_at": info["connected_at"].isoformat(),
                    "message_count": info["message_count"],
                    "client_info": info["client_info"]
                }
                for info in self.connection_info.values()
            ]
        }

    def _categorize_sentiment(self, score: float) -> str:
        """
        Categorize a sentiment score into human-readable categories.
        
        Args:
            score: Sentiment score (typically -1 to 1)
            
        Returns:
            Sentiment category string
        """
        if score > 0.1:
            return "positive"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"


# Global WebSocket manager instance
websocket_manager = WebSocketManager() 