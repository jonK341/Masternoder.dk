"""
User Onboarding Service
Handles new user creation with information scraping and agent skill assignment
"""
import os
import json
import uuid
from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UserOnboarding:
    """Service for user onboarding"""
    
    # Define onboarding steps
    ONBOARDING_STEPS = [
        {'id': 'welcome', 'name': 'Welcome', 'required': True, 'skipable': False, 'order': 1},
        {'id': 'profile_setup', 'name': 'Profile Setup', 'required': False, 'skipable': True, 'order': 2},
        {'id': 'skill_path', 'name': 'Skill Path Selection', 'required': True, 'skipable': False, 'order': 3},
        {'id': 'first_actions', 'name': 'First Actions', 'required': True, 'skipable': False, 'order': 4},
        {'id': 'dashboard_tour', 'name': 'Dashboard Tour', 'required': False, 'skipable': True, 'order': 5},
        {'id': 'complete', 'name': 'Complete', 'required': True, 'skipable': False, 'order': 6}
    ]
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.progress_dir = os.path.join(self.base_dir, 'logs', 'onboarding_progress')
        os.makedirs(self.progress_dir, exist_ok=True)
        
        # Initialize dependencies
        try:
            from backend.services.user_info_scraper import user_info_scraper
            self.info_scraper = user_info_scraper
        except:
            self.info_scraper = None
        
        try:
            from backend.services.user_agent_skills import user_agent_skills
            self.agent_skills = user_agent_skills
        except:
            self.agent_skills = None
    
    def create_new_user(self, request_data: Dict, user_id: Optional[str] = None) -> Dict:
        """Create a new user with full onboarding"""
        # Generate user_id if not provided
        if not user_id:
            user_id = self._generate_user_id(request_data)
        
        # Check if user already exists
        existing_user = self._check_user_exists(user_id)
        if existing_user:
            return {
                'success': False,
                'error': 'User already exists',
                'user_id': user_id,
                'existing': True
            }
        
        # Step 1: Scrape information
        scraped_info = {}
        if self.info_scraper:
            try:
                scraped_info = self.info_scraper.scrape_all_info(request_data)
                # Save scraped info
                for info_type, info_data in scraped_info.items():
                    if info_type not in ['scraped_at', 'scraping_version', 'confidence_score']:
                        self.info_scraper.save_scraped_info(user_id, info_type, info_data)
            except Exception as e:
                print(f"Error scraping info: {e}")
        
        # Step 2: Create user profile
        profile_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'username': self._generate_username(request_data),
            'preferences': json.dumps(scraped_info.get('preferences', {})),
            'scraped_info': json.dumps(scraped_info),
            'onboarding_complete': False,
            'onboarding_data': json.dumps({
                'created_at': datetime.now().isoformat(),
                'scraped_info': scraped_info
            }),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Step 3: Assign agent skills
        assigned_skills = {}
        if self.agent_skills:
            try:
                assigned_skills = self.agent_skills.assign_initial_skills(user_id, scraped_info)
                profile_data['agent_skillset_id'] = assigned_skills.get('skill_path', 'balanced')
                profile_data['assigned_agent_ids'] = json.dumps(assigned_skills.get('assigned_agents', []))
            except Exception as e:
                print(f"Error assigning skills: {e}")

        # Step 3.5: Provision full premium agent package for this user account.
        provisioning = self.provision_user_features(user_id, profile_data)
        
        # Step 4: Save user profile (try database first, fallback to file)
        profile_saved = False
        try:
            # Try to save to database
            from src.db.models import db
            from src.app import create_app
            
            app = create_app()
            with app.app_context():
                # Check if UserProfile model exists
                try:
                    from src.db.models import UserProfile
                    user = UserProfile(**profile_data)
                    db.session.add(user)
                    db.session.commit()
                    profile_saved = True
                except ImportError:
                    # UserProfile model doesn't exist, save to file
                    profile_saved = self._save_profile_to_file(user_id, profile_data)
                except Exception as e:
                    print(f"Error saving to database: {e}")
                    profile_saved = self._save_profile_to_file(user_id, profile_data)
        except:
            # Fallback to file storage
            profile_saved = self._save_profile_to_file(user_id, profile_data)
        
        # Step 5: Initialize user points (if system available)
        points_initialized = False
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db:
                # Initialize with welcome bonus
                unified_points_db.add_points(user_id, 'xp_points', 100, source='onboarding_welcome')
                # Start new accounts with 5.5 coins
                unified_points_db.add_points(user_id, 'coins', 5.5, source='onboarding_welcome')
                points_initialized = True
        except:
            pass
        
        # Step 6: Mark onboarding as complete
        profile_data['onboarding_complete'] = True
        profile_data['updated_at'] = datetime.now().isoformat()
        
        if not profile_saved:
            self._save_profile_to_file(user_id, profile_data)
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('onboarding')
        except Exception:
            pass
        return {
            'success': True,
            'user_id': user_id,
            'profile': profile_data,
            'scraped_info': scraped_info,
            'assigned_skills': assigned_skills,
            'provisioning': provisioning,
            'points_initialized': points_initialized,
            'onboarding_complete': True
        }

    def provision_user_features(self, user_id: str, profile_data: Optional[Dict] = None) -> Dict:
        """
        Attach full system features to a user:
        - all agent skills (including unique + battle)
        - battle ecosystem enrollment defaults
        - premium feature flags in profile metadata
        """
        provisioning = {
            'success': True,
            'user_id': user_id,
            'full_agent_access': None,
            'battle_skill_sync': None,
            'battle_enrollment': {},
            'feature_flags_applied': False,
        }
        try:
            # Ensure battle skills are present system-wide.
            try:
                from backend.services.agent_skillset import agent_skillset
                provisioning['battle_skill_sync'] = agent_skillset.ensure_battle_skills_per_agent(count=30)
                provisioning['sales_skill_sync'] = agent_skillset.ensure_sales_skillsets_per_agent(count=50)
                provisioning['paypal_skill_sync'] = agent_skillset.ensure_paypal_skillsets_per_agent(count=15)
                provisioning['top25_skill_sync'] = agent_skillset.ensure_top25_skill_upgrades_per_agent(count=25)
                provisioning['shared_growth_sync'] = agent_skillset.ensure_shared_growth_skills(count=100)
                provisioning['progression_sync'] = agent_skillset.update_agent_progression_from_results()
            except Exception as e:
                provisioning['battle_skill_sync'] = {'success': False, 'error': str(e)}

            # Grant all agents + unique/battle skills to this user.
            if self.agent_skills:
                try:
                    provisioning['full_agent_access'] = self.agent_skills.grant_full_agent_access(
                        user_id=user_id,
                        include_unique_skills=True,
                        include_battle_skills=True,
                    )
                except Exception as e:
                    provisioning['full_agent_access'] = {'success': False, 'error': str(e)}

            # Auto-enroll user into first clan + tournament (best effort).
            try:
                from backend.routes.battle_routes import _BATTLE_CLANS, _BATTLE_TOURNAMENTS
                if _BATTLE_CLANS:
                    clan = _BATTLE_CLANS[0]
                    if user_id not in clan['members']:
                        clan['members'].append(user_id)
                    provisioning['battle_enrollment']['clan'] = clan.get('id')
                if _BATTLE_TOURNAMENTS:
                    tour = _BATTLE_TOURNAMENTS[0]
                    if user_id not in tour['participants']:
                        tour['participants'].append(user_id)
                    provisioning['battle_enrollment']['tournament'] = tour.get('id')
            except Exception as e:
                provisioning['battle_enrollment']['error'] = str(e)

            # Attach premium flags into profile metadata.
            if profile_data is None:
                profile_data = self.get_user_profile(user_id) or {}
            flags = {
                'full_agent_package': True,
                'ai_super_upgrade_enabled': True,
                'battle_mode_enabled': True,
                'clans_enabled': True,
                'tournaments_enabled': True,
                'provisioned_at': datetime.now().isoformat(),
            }
            try:
                prefs = profile_data.get('preferences', {})
                if isinstance(prefs, str):
                    prefs = json.loads(prefs or '{}')
                if not isinstance(prefs, dict):
                    prefs = {}
                prefs['feature_flags'] = {**prefs.get('feature_flags', {}), **flags}
                profile_data['preferences'] = json.dumps(prefs)
                provisioning['feature_flags_applied'] = True
            except Exception:
                pass

            # Persist profile update (best effort).
            try:
                self.update_user_profile(user_id, {'preferences': profile_data.get('preferences', '{}')})
            except Exception:
                pass

            return provisioning
        except Exception as e:
            provisioning['success'] = False
            provisioning['error'] = str(e)
            return provisioning
    
    def enrich_user_profile(self, user_id: str, additional_data: Dict) -> Dict:
        """Enrich existing user profile with additional information"""
        # Get existing profile
        profile = self.get_user_profile(user_id)
        
        if not profile:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        # Scrape additional info
        if self.info_scraper:
            additional_scraped = self.info_scraper.scrape_all_info(additional_data)
            
            # Merge with existing scraped info
            existing_scraped = json.loads(profile.get('scraped_info', '{}'))
            for key, value in additional_scraped.items():
                if key not in ['scraped_at', 'scraping_version', 'confidence_score']:
                    existing_scraped[key] = value
            
            profile['scraped_info'] = json.dumps(existing_scraped)
            profile['updated_at'] = datetime.now().isoformat()
            
            # Save updated profile
            self._save_profile_to_file(user_id, profile)
        
        return {
            'success': True,
            'user_id': user_id,
            'profile': profile
        }
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile"""
        # Try database first
        try:
            from src.db.models import db, UserProfile
            from src.app import create_app
            
            app = create_app()
            with app.app_context():
                user = UserProfile.query.filter_by(user_id=user_id).first()
                if user:
                    return {
                        'id': user.id,
                        'user_id': user.user_id,
                        'username': user.username,
                        'preferences': user.preferences,
                        'scraped_info': getattr(user, 'scraped_info', '{}'),
                        'agent_skillset_id': getattr(user, 'agent_skillset_id', None),
                        'assigned_agent_ids': getattr(user, 'assigned_agent_ids', '[]'),
                        'onboarding_complete': getattr(user, 'onboarding_complete', False),
                        'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                        'updated_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') else None
                    }
        except:
            pass
        
        # Fallback to file
        return self._load_profile_from_file(user_id)

    def update_user_profile(self, user_id: str, update_data: Dict) -> Dict:
        """Update an existing user profile (DB first, then file fallback)."""
        profile = self.get_user_profile(user_id)
        if not profile:
            return {'success': False, 'error': 'User not found'}

        # Normalize and merge fields
        merged = dict(profile)
        for key, value in (update_data or {}).items():
            if key in ('preferences', 'scraped_info', 'assigned_agent_ids', 'onboarding_data', 'obtained_agents'):
                # Store as JSON string in persisted profile
                merged[key] = json.dumps(value) if isinstance(value, (dict, list)) else (value or "[]" if key == 'obtained_agents' else "{}")
            else:
                merged[key] = value

        merged['updated_at'] = datetime.now().isoformat()

        # Try DB update against raw table `user_profiles` (works even if ORM model missing)
        try:
            from src.db.models import db
            from src.app import create_app
            app = create_app()
            with app.app_context():
                # Only update known columns if present in update_data
                fields = {}
                allowed = {
                    'username', 'preferences', 'scraped_info', 'agent_skillset_id',
                    'assigned_agent_ids', 'obtained_agents', 'onboarding_complete', 'onboarding_data', 'updated_at'
                }
                for k in allowed:
                    if k in merged:
                        fields[k] = merged[k]

                if fields:
                    set_clause = ", ".join([f"{k} = :{k}" for k in fields.keys()])
                    fields['user_id'] = user_id
                    sql = text(f"UPDATE user_profiles SET {set_clause} WHERE user_id = :user_id")
                    result = db.session.execute(sql, fields)
                    db.session.commit()

                    # If nothing updated (row missing), fall back to file
                    if getattr(result, "rowcount", 0) > 0:
                        return {'success': True, 'profile': merged, 'message': 'Profile updated in DB'}
        except Exception as e:
            # DB errors should not break file fallback
            try:
                print(f"Error updating profile in DB: {e}")
            except Exception:
                pass

        # File fallback
        if self._save_profile_to_file(user_id, merged):
            return {'success': True, 'profile': merged, 'message': 'Profile updated in file'}
        return {'success': False, 'error': 'Failed to update profile'}
    
    def _generate_user_id(self, request_data: Dict) -> str:
        """Generate unique user ID"""
        # Try to use device fingerprint
        device_fingerprint = request_data.get('device_fingerprint')
        if device_fingerprint:
            return f"user_{device_fingerprint[:16]}"
        
        # Use MAC address if available
        mac_address = request_data.get('mac_address')
        if mac_address:
            return f"user_{mac_address.replace(':', '')[:16]}"
        
        # Generate random ID
        return f"user_{uuid.uuid4().hex[:16]}"
    
    def _generate_username(self, request_data: Dict) -> str:
        """Generate username"""
        # Try to extract from preferences
        preferences = request_data.get('preferences', {})
        if isinstance(preferences, dict) and preferences.get('username'):
            return preferences['username']
        
        # Generate default username
        return f"Player_{uuid.uuid4().hex[:8]}"
    
    def _check_user_exists(self, user_id: str) -> bool:
        """Check if user exists"""
        # Try database
        try:
            from src.db.models import db, UserProfile
            from src.app import create_app
            
            app = create_app()
            with app.app_context():
                user = UserProfile.query.filter_by(user_id=user_id).first()
                if user:
                    return True
        except:
            pass
        
        # Check file
        profile_file = os.path.join(self.base_dir, 'logs', 'user_profiles', f"{user_id}.json")
        return os.path.exists(profile_file)
    
    def _save_profile_to_file(self, user_id: str, profile_data: Dict) -> bool:
        """Save profile to file"""
        try:
            profiles_dir = os.path.join(self.base_dir, 'logs', 'user_profiles')
            os.makedirs(profiles_dir, exist_ok=True)
            
            file_path = os.path.join(profiles_dir, f"{user_id}.json")
            with open(file_path, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving profile to file: {e}")
            return False
    
    def _load_profile_from_file(self, user_id: str) -> Optional[Dict]:
        """Load profile from file"""
        try:
            file_path = os.path.join(self.base_dir, 'logs', 'user_profiles', f"{user_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except:
            pass
        
        return None

# Global instance
user_onboarding = UserOnboarding()
