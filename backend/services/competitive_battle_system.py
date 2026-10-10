"""
Competitive Battle System - Tournaments, Seasons, Challenges
Enhanced battle mechanics with comprehensive point rewards
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)


class CompetitiveBattleSystem:
    """
    Competitive Battle System with tournaments, seasons, and challenges
    Awards comprehensive points for competitive progression
    """
    
    def __init__(self):
        """Initialize competitive battle system"""
        self._tournaments = {}  # {tournament_id: tournament_data}
        self._seasons = {}  # {season_id: season_data}
        self._challenges = {}  # {challenge_id: challenge_data}
        self._leaderboards = {}  # {leaderboard_type: [entries]}
        self._rankings = {}  # {user_id: {category: rank}}
        
    # ========================================================================
    # TOURNAMENTS
    # ========================================================================
    
    def create_tournament(self, name: str, tournament_type: str = 'single_elimination',
                         max_participants: int = 16, entry_fee: int = 0,
                         prize_pool: Dict[str, int] = None) -> Dict[str, Any]:
        """Create a new tournament"""
        tournament_id = f"tournament_{datetime.utcnow().timestamp()}"
        
        tournament = {
            'tournament_id': tournament_id,
            'name': name,
            'type': tournament_type,  # single_elimination, double_elimination, round_robin
            'max_participants': max_participants,
            'entry_fee': entry_fee,
            'prize_pool': prize_pool or {
                '1st': 1000,
                '2nd': 500,
                '3rd': 250
            },
            'participants': [],
            'matches': [],
            'status': 'open',  # open, active, completed
            'created_at': datetime.utcnow().isoformat(),
            'starts_at': None,
            'ends_at': None
        }
        
        self._tournaments[tournament_id] = tournament
        return {'success': True, 'tournament': tournament}
    
    def join_tournament(self, tournament_id: str, user_id: str) -> Dict[str, Any]:
        """Join a tournament"""
        if tournament_id not in self._tournaments:
            return {'success': False, 'error': 'Tournament not found'}
        
        tournament = self._tournaments[tournament_id]
        
        if tournament['status'] != 'open':
            return {'success': False, 'error': 'Tournament not open'}
        
        if len(tournament['participants']) >= tournament['max_participants']:
            return {'success': False, 'error': 'Tournament full'}
        
        if user_id in tournament['participants']:
            return {'success': False, 'error': 'Already joined'}
        
        tournament['participants'].append(user_id)
        
        return {'success': True, 'tournament': tournament}
    
    def start_tournament(self, tournament_id: str) -> Dict[str, Any]:
        """Start a tournament"""
        if tournament_id not in self._tournaments:
            return {'success': False, 'error': 'Tournament not found'}
        
        tournament = self._tournaments[tournament_id]
        
        if tournament['status'] != 'open':
            return {'success': False, 'error': 'Tournament not open'}
        
        if len(tournament['participants']) < 2:
            return {'success': False, 'error': 'Not enough participants'}
        
        tournament['status'] = 'active'
        tournament['starts_at'] = datetime.utcnow().isoformat()
        
        # Generate matches based on tournament type
        matches = self._generate_tournament_matches(tournament)
        tournament['matches'] = matches
        
        return {'success': True, 'tournament': tournament}
    
    def _generate_tournament_matches(self, tournament: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate matches for tournament"""
        participants = tournament['participants']
        matches = []
        
        if tournament['type'] == 'single_elimination':
            # Pair up participants
            for i in range(0, len(participants), 2):
                if i + 1 < len(participants):
                    match = {
                        'match_id': f"match_{tournament['tournament_id']}_{len(matches)}",
                        'player1': participants[i],
                        'player2': participants[i + 1],
                        'winner': None,
                        'status': 'pending',
                        'round': 1
                    }
                    matches.append(match)
        
        return matches
    
    def complete_tournament_match(self, tournament_id: str, match_id: str, winner: str) -> Dict[str, Any]:
        """Complete a tournament match"""
        if tournament_id not in self._tournaments:
            return {'success': False, 'error': 'Tournament not found'}
        
        tournament = self._tournaments[tournament_id]
        
        match = None
        for m in tournament['matches']:
            if m['match_id'] == match_id:
                match = m
                break
        
        if not match:
            return {'success': False, 'error': 'Match not found'}
        
        match['winner'] = winner
        match['status'] = 'completed'
        match['completed_at'] = datetime.utcnow().isoformat()
        
        # Award points to winner
        points_awarded = {
            'tournament_win_points': random.randint(100, 500),
            'battle_points': random.randint(50, 200),
            'xp': random.randint(200, 1000)
        }
        
        return {
            'success': True,
            'match': match,
            'points_awarded': points_awarded
        }
    
    def get_tournament(self, tournament_id: str) -> Dict[str, Any]:
        """Get tournament details"""
        if tournament_id not in self._tournaments:
            return {'success': False, 'error': 'Tournament not found'}
        return {'success': True, 'tournament': self._tournaments[tournament_id]}
    
    def list_tournaments(self, status: str = None) -> List[Dict[str, Any]]:
        """List tournaments"""
        tournaments = list(self._tournaments.values())
        if status:
            tournaments = [t for t in tournaments if t['status'] == status]
        return tournaments
    
    # ========================================================================
    # SEASONS
    # ========================================================================
    
    def create_season(self, name: str, duration_days: int = 30) -> Dict[str, Any]:
        """Create a new season"""
        season_id = f"season_{datetime.utcnow().timestamp()}"
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=duration_days)
        
        season = {
            'season_id': season_id,
            'name': name,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'status': 'active',
            'participants': {},  # {user_id: {points: 0, rank: 0, rewards: []}}
            'rewards': {
                'top_1': {'coins': 5000, 'tokens': 100, 'trophy': 'Season Champion'},
                'top_10': {'coins': 2000, 'tokens': 50, 'trophy': 'Season Elite'},
                'top_100': {'coins': 1000, 'tokens': 25, 'trophy': 'Season Veteran'},
                'all': {'coins': 100, 'tokens': 5}
            }
        }
        
        self._seasons[season_id] = season
        return {'success': True, 'season': season}
    
    def update_season_score(self, season_id: str, user_id: str, points: int) -> Dict[str, Any]:
        """Update season score for user"""
        if season_id not in self._seasons:
            return {'success': False, 'error': 'Season not found'}
        
        season = self._seasons[season_id]
        
        if season['status'] != 'active':
            return {'success': False, 'error': 'Season not active'}
        
        if user_id not in season['participants']:
            season['participants'][user_id] = {
                'points': 0,
                'rank': 0,
                'rewards': []
            }
        
        season['participants'][user_id]['points'] += points
        
        # Update rankings
        self._update_season_rankings(season_id)
        
        return {'success': True, 'participant': season['participants'][user_id]}
    
    def _update_season_rankings(self, season_id: str):
        """Update season rankings"""
        season = self._seasons[season_id]
        participants = list(season['participants'].items())
        participants.sort(key=lambda x: x[1]['points'], reverse=True)
        
        for rank, (user_id, data) in enumerate(participants, 1):
            season['participants'][user_id]['rank'] = rank
    
    def get_season_leaderboard(self, season_id: str, limit: int = 100) -> Dict[str, Any]:
        """Get season leaderboard"""
        if season_id not in self._seasons:
            return {'success': False, 'error': 'Season not found'}
        
        season = self._seasons[season_id]
        participants = list(season['participants'].items())
        participants.sort(key=lambda x: x[1]['points'], reverse=True)
        
        leaderboard = [
            {
                'rank': rank,
                'user_id': user_id,
                'points': data['points']
            }
            for rank, (user_id, data) in enumerate(participants[:limit], 1)
        ]
        
        return {'success': True, 'leaderboard': leaderboard}
    
    def end_season(self, season_id: str) -> Dict[str, Any]:
        """End season and distribute rewards"""
        if season_id not in self._seasons:
            return {'success': False, 'error': 'Season not found'}
        
        season = self._seasons[season_id]
        season['status'] = 'completed'
        season['ended_at'] = datetime.utcnow().isoformat()
        
        # Update final rankings
        self._update_season_rankings(season_id)
        
        # Distribute rewards
        rewards_distributed = []
        participants = list(season['participants'].items())
        participants.sort(key=lambda x: x[1]['points'], reverse=True)
        
        for rank, (user_id, data) in enumerate(participants, 1):
            if rank == 1:
                reward = season['rewards']['top_1']
            elif rank <= 10:
                reward = season['rewards']['top_10']
            elif rank <= 100:
                reward = season['rewards']['top_100']
            else:
                reward = season['rewards']['all']
            
            season['participants'][user_id]['rewards'].append(reward)
            rewards_distributed.append({
                'user_id': user_id,
                'rank': rank,
                'reward': reward
            })
        
        return {
            'success': True,
            'season': season,
            'rewards_distributed': rewards_distributed
        }
    
    # ========================================================================
    # CHALLENGES
    # ========================================================================
    
    def create_challenge(self, name: str, challenge_type: str,
                        target: int, reward: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new challenge"""
        challenge_id = f"challenge_{datetime.utcnow().timestamp()}"
        
        challenge = {
            'challenge_id': challenge_id,
            'name': name,
            'type': challenge_type,  # win_streak, total_wins, perfect_victory, etc.
            'target': target,
            'current': {},
            'reward': reward,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        self._challenges[challenge_id] = challenge
        return {'success': True, 'challenge': challenge}
    
    def update_challenge_progress(self, challenge_id: str, user_id: str, progress: int = 1) -> Dict[str, Any]:
        """Update challenge progress for user"""
        if challenge_id not in self._challenges:
            return {'success': False, 'error': 'Challenge not found'}
        
        challenge = self._challenges[challenge_id]
        
        if challenge['status'] != 'active':
            return {'success': False, 'error': 'Challenge not active'}
        
        if user_id not in challenge['current']:
            challenge['current'][user_id] = 0
        
        challenge['current'][user_id] += progress
        
        # Check if completed
        if challenge['current'][user_id] >= challenge['target']:
            return {
                'success': True,
                'completed': True,
                'reward': challenge['reward']
            }
        
        return {
            'success': True,
            'completed': False,
            'progress': challenge['current'][user_id],
            'target': challenge['target']
        }
    
    def list_challenges(self) -> List[Dict[str, Any]]:
        """List active challenges"""
        return [c for c in self._challenges.values() if c['status'] == 'active']
    
    # ========================================================================
    # LEADERBOARDS
    # ========================================================================
    
    def update_leaderboard(self, leaderboard_type: str, user_id: str, score: int):
        """Update leaderboard"""
        if leaderboard_type not in self._leaderboards:
            self._leaderboards[leaderboard_type] = []
        
        # Find or create entry
        entry = None
        for e in self._leaderboards[leaderboard_type]:
            if e['user_id'] == user_id:
                entry = e
                break
        
        if entry:
            entry['score'] = max(entry['score'], score)
            entry['updated_at'] = datetime.utcnow().isoformat()
        else:
            self._leaderboards[leaderboard_type].append({
                'user_id': user_id,
                'score': score,
                'updated_at': datetime.utcnow().isoformat()
            })
        
        # Sort leaderboard
        self._leaderboards[leaderboard_type].sort(key=lambda x: x['score'], reverse=True)
        
        # Update rankings
        for rank, entry in enumerate(self._leaderboards[leaderboard_type], 1):
            entry['rank'] = rank
    
    def get_leaderboard(self, leaderboard_type: str, limit: int = 100) -> Dict[str, Any]:
        """Get leaderboard"""
        if leaderboard_type not in self._leaderboards:
            return {'success': True, 'leaderboard': []}
        
        leaderboard = self._leaderboards[leaderboard_type][:limit]
        return {'success': True, 'leaderboard': leaderboard}


# Global instance
competitive_battle_system = CompetitiveBattleSystem()
