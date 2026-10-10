"""
Battle Extensions - Rule Books, Series, GPS, NEWS, Techno Tunnel Magi
Extended battle features for enhanced gameplay
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
import random

# Import Techno Tunnel Magi
from backend.services.battle_techno_tunnel_magi import battle_techno_tunnel_magi

class BattleRuleBooks:
    """Battle Rule Books System"""
    
    def __init__(self):
        self.rule_books = {}
        self.user_progress = defaultdict(dict)  # {user_id: {book_id: progress}}
        self._initialize_default_books()
    
    def _initialize_default_books(self):
        """Initialize default rule books"""
        self.rule_books = {
            "beginner_guide": {
                "id": "beginner_guide",
                "title": "Beginner's Battle Guide",
                "description": "Essential rules and strategies for new players",
                "category": "beginner",
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Getting Started",
                        "content": "Learn the basics of battle mechanics, clan systems, and how to participate in your first battle.",
                        "rules": [
                            "Each battle consists of multiple rounds",
                            "Clans compete for victory points",
                            "Video generation quality affects battle scores"
                        ]
                    },
                    {
                        "id": "ch2",
                        "title": "Battle Mechanics",
                        "content": "Understand how battles work, scoring systems, and victory conditions.",
                        "rules": [
                            "Battles are won by achieving the highest score",
                            "Scores are based on video quality and performance",
                            "Time limits apply to each battle round"
                        ]
                    },
                    {
                        "id": "ch3",
                        "title": "Clan Strategy",
                        "content": "Master clan coordination and teamwork for maximum effectiveness.",
                        "rules": [
                            "Coordinate with clan members for better results",
                            "Each member's contribution adds to clan score",
                            "Communication is key to victory"
                        ]
                    }
                ],
                "unlocked_by_default": True
            },
            "advanced_tactics": {
                "id": "advanced_tactics",
                "title": "Advanced Battle Tactics",
                "description": "Advanced strategies for experienced players",
                "category": "advanced",
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Power Optimization",
                        "content": "Maximize your battle power through strategic resource allocation.",
                        "rules": [
                            "Balance creativity, efficiency, and quality stats",
                            "Use resources strategically before battles",
                            "Power multipliers affect final scores"
                        ]
                    },
                    {
                        "id": "ch2",
                        "title": "Intelligence Systems",
                        "content": "Master intelligence gathering and nullification techniques.",
                        "rules": [
                            "Intelligence affects battle outcomes",
                            "Nullification can reduce opponent intelligence",
                            "Intelligence levels reset after battles"
                        ]
                    }
                ],
                "unlocked_by_default": False,
                "unlock_requirement": {"level": 10, "wins": 5}
            },
            "krimetime_rules": {
                "id": "krimetime_rules",
                "title": "KrimeTime WarZone Rules",
                "description": "Complete guide to KrimeTime WarZone battles",
                "category": "krimetime",
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Satanic & Goth Guilds",
                        "content": "Learn about Satanic and Goth guild mechanics.",
                        "rules": [
                            "Satanic guilds use dark rituals and soul harvesting",
                            "Goth guilds use melancholy aura and dark poetry",
                            "Both can nullify clan intelligence"
                        ]
                    },
                    {
                        "id": "ch2",
                        "title": "Timepockets & Teleports",
                        "content": "Master time travel and teleportation mechanics.",
                        "rules": [
                            "Timepockets allow time travel during battles",
                            "Teleports enable instant position changes",
                            "Both have limited uses and cooldowns"
                        ]
                    }
                ],
                "unlocked_by_default": False,
                "unlock_requirement": {"krimetime_battles": 1}
            }
        }
    
    def get_rule_books(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get available rule books for user"""
        books = []
        for book_id, book_data in self.rule_books.items():
            book = book_data.copy()
            if user_id:
                book["progress"] = self.user_progress.get(user_id, {}).get(book_id, {})
                book["unlocked"] = self._is_unlocked(book, user_id)
            else:
                book["unlocked"] = book.get("unlocked_by_default", False)
            books.append(book)
        return books
    
    def _is_unlocked(self, book: Dict[str, Any], user_id: str) -> bool:
        """Check if book is unlocked for user"""
        if book.get("unlocked_by_default", False):
            return True
        
        requirement = book.get("unlock_requirement", {})
        if not requirement:
            return True
        
        # Check requirements (would integrate with user stats)
        return True  # Simplified for now
    
    def get_rule_book(self, book_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get specific rule book"""
        if book_id not in self.rule_books:
            return None
        
        book = self.rule_books[book_id].copy()
        if user_id:
            book["progress"] = self.user_progress.get(user_id, {}).get(book_id, {})
            book["unlocked"] = self._is_unlocked(book, user_id)
        return book
    
    def update_progress(self, user_id: str, book_id: str, chapter_id: str) -> Dict[str, Any]:
        """Update user progress in rule book"""
        if book_id not in self.rule_books:
            return {"success": False, "error": "Book not found"}
        
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {}
        
        if book_id not in self.user_progress[user_id]:
            self.user_progress[user_id][book_id] = {
                "chapters_completed": [],
                "last_accessed": None
            }
        
        if chapter_id not in self.user_progress[user_id][book_id]["chapters_completed"]:
            self.user_progress[user_id][book_id]["chapters_completed"].append(chapter_id)
        
        self.user_progress[user_id][book_id]["last_accessed"] = datetime.utcnow().isoformat()
        
        return {"success": True, "progress": self.user_progress[user_id][book_id]}


class BattleSeries:
    """Battle Series/Tournament System"""
    
    def __init__(self):
        self.series = {}
        self.user_participations = defaultdict(list)  # {user_id: [series_ids]}
        self._initialize_default_series()
    
    def _initialize_default_series(self):
        """Initialize default battle series"""
        self.series = {
            "weekly_championship": {
                "id": "weekly_championship",
                "name": "Weekly Championship",
                "description": "Weekly battle series with rotating themes",
                "type": "weekly",
                "status": "active",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "prize_pool": 10000,
                "participants": [],
                "leaderboard": [],
                "rules": {
                    "max_participants": 100,
                    "battles_per_round": 3,
                    "elimination": True
                }
            },
            "monthly_grand_prix": {
                "id": "monthly_grand_prix",
                "name": "Monthly Grand Prix",
                "description": "Monthly elite tournament with major prizes",
                "type": "monthly",
                "status": "upcoming",
                "start_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=37)).isoformat(),
                "prize_pool": 50000,
                "participants": [],
                "leaderboard": [],
                "rules": {
                    "max_participants": 50,
                    "battles_per_round": 5,
                    "elimination": True,
                    "min_level": 20
                }
            },
            "krimetime_series": {
                "id": "krimetime_series",
                "name": "KrimeTime WarZone Series",
                "description": "Special series for KrimeTime WarZone battles",
                "type": "special",
                "status": "active",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
                "prize_pool": 25000,
                "participants": [],
                "leaderboard": [],
                "rules": {
                    "max_participants": 30,
                    "battles_per_round": 4,
                    "elimination": True,
                    "requires_krimetime": True
                }
            }
        }
    
    def get_series(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get available battle series"""
        series_list = []
        for series_id, series_data in self.series.items():
            series = series_data.copy()
            if user_id:
                series["participating"] = series_id in self.user_participations.get(user_id, [])
            else:
                series["participating"] = False
            series_list.append(series)
        return series_list
    
    def get_series_details(self, series_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get specific series details"""
        if series_id not in self.series:
            return None
        
        series = self.series[series_id].copy()
        if user_id:
            series["participating"] = series_id in self.user_participations.get(user_id, [])
        return series
    
    def join_series(self, user_id: str, series_id: str) -> Dict[str, Any]:
        """Join a battle series"""
        if series_id not in self.series:
            return {"success": False, "error": "Series not found"}
        
        series = self.series[series_id]
        
        if series["status"] != "active":
            return {"success": False, "error": "Series is not active"}
        
        if user_id in series["participants"]:
            return {"success": False, "error": "Already participating"}
        
        if len(series["participants"]) >= series["rules"].get("max_participants", 100):
            return {"success": False, "error": "Series is full"}
        
        series["participants"].append(user_id)
        if user_id not in self.user_participations:
            self.user_participations[user_id] = []
        self.user_participations[user_id].append(series_id)
        
        return {"success": True, "series": series}


class BattleGPS:
    """Battle GPS - Location-based Battle Features"""
    
    def __init__(self):
        self.battle_locations = {}
        self.user_locations = {}  # {user_id: location_data}
        self.nearby_battles = defaultdict(list)  # {user_id: [battle_ids]}
        self._initialize_default_locations()
    
    def _initialize_default_locations(self):
        """Initialize default battle locations"""
        self.battle_locations = {
            "arena_central": {
                "id": "arena_central",
                "name": "Central Arena",
                "description": "Main battle arena in the center",
                "coordinates": {"lat": 55.6761, "lng": 12.5683},  # Copenhagen
                "type": "arena",
                "active_battles": []
            },
            "krimetime_zone": {
                "id": "krimetime_zone",
                "name": "KrimeTime WarZone",
                "description": "Special zone for KrimeTime battles",
                "coordinates": {"lat": 55.6861, "lng": 12.5783},
                "type": "krimetime",
                "active_battles": []
            },
            "training_grounds": {
                "id": "training_grounds",
                "name": "Training Grounds",
                "description": "Practice battles and training",
                "coordinates": {"lat": 55.6661, "lng": 12.5583},
                "type": "training",
                "active_battles": []
            }
        }
    
    def update_user_location(self, user_id: str, lat: float, lng: float) -> Dict[str, Any]:
        """Update user GPS location"""
        self.user_locations[user_id] = {
            "coordinates": {"lat": lat, "lng": lng},
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Find nearby battles
        nearby = self._find_nearby_battles(lat, lng)
        self.nearby_battles[user_id] = nearby
        
        return {
            "success": True,
            "location": self.user_locations[user_id],
            "nearby_battles": nearby
        }
    
    def _find_nearby_battles(self, lat: float, lng: float, radius_km: float = 10.0) -> List[str]:
        """Find battles within radius"""
        # Simplified: return all active battles
        # In production, would calculate distance and filter
        return []
    
    def get_nearby_battles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get battles near user location"""
        if user_id not in self.user_locations:
            return []
        
        location = self.user_locations[user_id]
        nearby_ids = self.nearby_battles.get(user_id, [])
        
        # Return battle locations within range
        battles = []
        for loc_id, loc_data in self.battle_locations.items():
            battles.append({
                "location": loc_data,
                "distance_km": self._calculate_distance(
                    location["coordinates"]["lat"],
                    location["coordinates"]["lng"],
                    loc_data["coordinates"]["lat"],
                    loc_data["coordinates"]["lng"]
                )
            })
        
        return sorted(battles, key=lambda x: x["distance_km"])
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates (Haversine formula)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    def get_battle_locations(self) -> List[Dict[str, Any]]:
        """Get all battle locations"""
        return list(self.battle_locations.values())


class BattleNews:
    """Battle News System"""
    
    def __init__(self):
        self.news_items = []
        self._initialize_default_news()
    
    def _initialize_default_news(self):
        """Initialize default news items"""
        self.news_items = [
            {
                "id": "news_001",
                "title": "New Battle Series Announced",
                "content": "The Weekly Championship series is now open for registration. Compete for amazing prizes!",
                "category": "announcement",
                "priority": "high",
                "published_at": datetime.utcnow().isoformat(),
                "image_url": None
            },
            {
                "id": "news_002",
                "title": "KrimeTime WarZone Update",
                "content": "New intelligence nullification features have been added to KrimeTime WarZone battles.",
                "category": "update",
                "priority": "medium",
                "published_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "image_url": None
            },
            {
                "id": "news_003",
                "title": "Battle Rule Books Available",
                "content": "New rule books are now available to help you master battle mechanics and strategies.",
                "category": "feature",
                "priority": "medium",
                "published_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "image_url": None
            }
        ]
    
    def get_news(self, limit: int = 10, category: str = None) -> List[Dict[str, Any]]:
        """Get battle news"""
        news = self.news_items.copy()
        
        if category:
            news = [item for item in news if item.get("category") == category]
        
        # Sort by priority and date
        news.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low"), 2),
            x.get("published_at", "")
        ), reverse=True)
        
        return news[:limit]
    
    def add_news(self, title: str, content: str, category: str = "general", priority: str = "medium") -> Dict[str, Any]:
        """Add news item"""
        news_item = {
            "id": f"news_{len(self.news_items) + 1:03d}",
            "title": title,
            "content": content,
            "category": category,
            "priority": priority,
            "published_at": datetime.utcnow().isoformat(),
            "image_url": None
        }
        
        self.news_items.insert(0, news_item)
        return {"success": True, "news": news_item}


class BattlePeerNetwork:
    """Battle Peer Network - Network behavior and peer connections"""
    
    def __init__(self):
        self.peers = {}  # {peer_id: peer_data}
        self.connections = defaultdict(list)  # {peer_id: [connected_peer_ids]}
        self.network_stats = defaultdict(dict)  # {peer_id: network_stats}
        self.network_topology = {}  # Network graph structure
        self.behavior_logs = defaultdict(list)  # {peer_id: [behavior_events]}
        self._initialize_default_peers()
    
    def _initialize_default_peers(self):
        """Initialize default peer network"""
        # Create some example peers
        for i in range(10):
            peer_id = f"peer_{i+1:03d}"
            self.peers[peer_id] = {
                "id": peer_id,
                "name": f"Peer {i+1}",
                "status": random.choice(["online", "offline", "battling", "idle"]),
                "connection_strength": random.randint(50, 100),
                "latency_ms": random.randint(10, 200),
                "battles_participated": random.randint(0, 50),
                "wins": random.randint(0, 30),
                "network_role": random.choice(["node", "hub", "edge"]),
                "last_seen": (datetime.utcnow() - timedelta(minutes=random.randint(0, 60))).isoformat()
            }
    
    def get_peers(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get all peers in network"""
        peers_list = []
        for peer_id, peer_data in self.peers.items():
            peer = peer_data.copy()
            if user_id:
                # Check if connected to this peer
                peer["connected"] = peer_id in self.connections.get(user_id, [])
                peer["connection_strength"] = self._calculate_connection_strength(user_id, peer_id)
            else:
                peer["connected"] = False
            peers_list.append(peer)
        return peers_list
    
    def _calculate_connection_strength(self, user_id: str, peer_id: str) -> int:
        """Calculate connection strength between two peers"""
        if peer_id not in self.connections.get(user_id, []):
            return 0
        
        peer_data = self.peers.get(peer_id, {})
        base_strength = peer_data.get("connection_strength", 50)
        latency = peer_data.get("latency_ms", 100)
        
        # Lower latency = stronger connection
        latency_factor = max(0, 100 - latency) / 100
        return int(base_strength * latency_factor)
    
    def connect_peer(self, user_id: str, peer_id: str) -> Dict[str, Any]:
        """Connect to a peer"""
        if peer_id not in self.peers:
            return {"success": False, "error": "Peer not found"}
        
        if peer_id in self.connections.get(user_id, []):
            return {"success": False, "error": "Already connected"}
        
        if user_id not in self.connections:
            self.connections[user_id] = []
        
        self.connections[user_id].append(peer_id)
        
        # Log behavior
        self._log_behavior(user_id, "peer_connect", {"peer_id": peer_id})
        
        return {
            "success": True,
            "peer": self.peers[peer_id],
            "connection_strength": self._calculate_connection_strength(user_id, peer_id)
        }
    
    def disconnect_peer(self, user_id: str, peer_id: str) -> Dict[str, Any]:
        """Disconnect from a peer"""
        if peer_id in self.connections.get(user_id, []):
            self.connections[user_id].remove(peer_id)
            self._log_behavior(user_id, "peer_disconnect", {"peer_id": peer_id})
            return {"success": True}
        return {"success": False, "error": "Not connected"}
    
    def get_network_topology(self, user_id: str = None) -> Dict[str, Any]:
        """Get network topology graph"""
        nodes = []
        edges = []
        
        # Add all peers as nodes
        for peer_id, peer_data in self.peers.items():
            nodes.append({
                "id": peer_id,
                "label": peer_data.get("name", peer_id),
                "status": peer_data.get("status", "offline"),
                "role": peer_data.get("network_role", "node"),
                "group": 1 if peer_id in self.connections.get(user_id, []) else 2
            })
        
        # Add connections as edges
        for source_id, connected_peers in self.connections.items():
            for target_id in connected_peers:
                if source_id in self.peers and target_id in self.peers:
                    edges.append({
                        "from": source_id,
                        "to": target_id,
                        "value": self._calculate_connection_strength(source_id, target_id)
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    
    def get_network_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get network statistics"""
        total_peers = len(self.peers)
        online_peers = sum(1 for p in self.peers.values() if p.get("status") == "online")
        connected_count = len(self.connections.get(user_id, [])) if user_id else 0
        
        # Calculate network metrics
        avg_latency = sum(p.get("latency_ms", 0) for p in self.peers.values()) / total_peers if total_peers > 0 else 0
        avg_connection_strength = sum(p.get("connection_strength", 0) for p in self.peers.values()) / total_peers if total_peers > 0 else 0
        
        # Network roles distribution
        roles = {}
        for peer in self.peers.values():
            role = peer.get("network_role", "node")
            roles[role] = roles.get(role, 0) + 1
        
        return {
            "total_peers": total_peers,
            "online_peers": online_peers,
            "offline_peers": total_peers - online_peers,
            "connected_peers": connected_count,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_connection_strength": round(avg_connection_strength, 2),
            "network_roles": roles,
            "network_health": "healthy" if online_peers > total_peers * 0.7 else "degraded"
        }
    
    def get_peer_behavior(self, peer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get behavior logs for a peer"""
        return self.behavior_logs.get(peer_id, [])[-limit:]
    
    def _log_behavior(self, peer_id: str, behavior_type: str, data: Dict[str, Any]):
        """Log peer behavior"""
        if peer_id not in self.behavior_logs:
            self.behavior_logs[peer_id] = []
        
        self.behavior_logs[peer_id].append({
            "type": behavior_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def update_peer_status(self, peer_id: str, status: str) -> Dict[str, Any]:
        """Update peer status"""
        if peer_id not in self.peers:
            return {"success": False, "error": "Peer not found"}
        
        self.peers[peer_id]["status"] = status
        self.peers[peer_id]["last_seen"] = datetime.utcnow().isoformat()
        
        self._log_behavior(peer_id, "status_update", {"status": status})
        
        return {"success": True, "peer": self.peers[peer_id]}


# Global instances
battle_rule_books = BattleRuleBooks()
battle_series = BattleSeries()
battle_gps = BattleGPS()
battle_news = BattleNews()
battle_peer_network = BattlePeerNetwork()

