"""
Agent Skillset System
Skillsets for agents and test players
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_UNIQUE_SKILLS_PER_AGENT = 500
DEFAULT_BATTLE_SKILLS_PER_AGENT = 30
DEFAULT_SALES_SKILLS_PER_AGENT = 50
DEFAULT_PAYPAL_SKILLS_PER_AGENT = 15
DEFAULT_TOP25_SKILLS_PER_AGENT = 25
DEFAULT_SHARED_GROWTH_SKILLS = 100
DEFAULT_CRITICISM_SKILLS_PER_AGENT = 20

class AgentSkillset:
    """Skillset management for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.skillsets_file = os.path.join(self.base_dir, 'logs', 'agent_skillsets', 'skillsets.json')
        self.load_skillsets()
    
    def load_skillsets(self):
        """Load skillsets"""
        os.makedirs(os.path.dirname(self.skillsets_file), exist_ok=True)
        if os.path.exists(self.skillsets_file):
            try:
                with open(self.skillsets_file, 'r') as f:
                    self.skillsets = json.load(f)
            except:
                self.skillsets = self._default_skillsets()
        else:
            self.skillsets = self._default_skillsets()
        self._ensure_tester_agent_skillset()
        self._ensure_unique_skillsets_for_agents()
        self.ensure_battle_skills_per_agent(count=DEFAULT_BATTLE_SKILLS_PER_AGENT)
        self.ensure_sales_skillsets_per_agent(count=DEFAULT_SALES_SKILLS_PER_AGENT)
        self.ensure_paypal_skillsets_per_agent(count=DEFAULT_PAYPAL_SKILLS_PER_AGENT)
        self.ensure_top25_skill_upgrades_per_agent(count=DEFAULT_TOP25_SKILLS_PER_AGENT)
        self.ensure_shared_growth_skills(count=DEFAULT_SHARED_GROWTH_SKILLS)
        self.ensure_knowledge_skills_per_agent()
        self.ensure_ai_skills_per_agent()
        self.ensure_criticism_skills_per_agent(count=DEFAULT_CRITICISM_SKILLS_PER_AGENT)
        self.ensure_blueprint_route_fixer_skills_per_agent()
        self.ensure_api_service_skills_per_agent()
        self.save_skillsets()

    def _ensure_tester_agent_skillset(self):
        """Ensure tester agent exists in persistent skillsets for production quality audits."""
        agents = self.skillsets.setdefault('agents', {})
        tester_defaults = {
            'name': 'Tester Agent',
            'skills': [
                'ui_smoke_test',
                'cross_browser_test',
                'mobile_responsive_audit',
                'accessibility_audit',
                'performance_lighthouse_check',
                'api_contract_validation',
                'visual_regression_check',
                'error_reproduction',
                'test_plan_generation',
                'release_quality_gate',
                'ai_quality_check',
                'ai_suggest_fix',
                'ai_auto_validate',
                'ai_nice_and_easy',
            ],
            'level': 4,
            'experience': 1200
        }

        existing = agents.get('tester_agent')
        if not isinstance(existing, dict):
            agents['tester_agent'] = tester_defaults
            return

        existing.setdefault('name', tester_defaults['name'])
        existing.setdefault('level', tester_defaults['level'])
        existing.setdefault('experience', tester_defaults['experience'])
        existing_skills = existing.setdefault('skills', [])
        for skill in tester_defaults['skills']:
            if skill not in existing_skills:
                existing_skills.append(skill)

    def _generate_sales_skill_profiles(self, agent_id: str, count: int = DEFAULT_SALES_SKILLS_PER_AGENT) -> List[Dict]:
        """
        Generate monetization and shop-conversion skills.
        Ethical focus: persuasion + optimization, not deception.
        """
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        domains = [
            'offer_positioning', 'value_stacking', 'cart_recovery', 'upsell_timing', 'cross_sell_mapping',
            'pricing_test', 'bundle_design', 'funnel_step_opt', 'checkout_clarity', 'cta_precision',
            'social_proof', 'trust_signal', 'objection_handle', 'retention_trigger', 'lifecycle_offer',
            'seasonal_campaign', 'segment_targeting', 'message_match', 'creative_hook', 'copy_variants',
            'email_nurture', 'sms_reengage', 'landing_opt', 'promo_calendar', 'roi_tracking',
        ]
        profiles = []
        for idx in range(1, max(1, count) + 1):
            domain = domains[(idx - 1) % len(domains)]
            skill_name = f"{normalized_agent}_sales_{idx:02d}_{domain}"
            profiles.append({
                'skill_name': skill_name,
                'domain': domain,
                'conversion_power': 40 + (idx * 3),
                'value_points': 500 + (idx * 20),
                'ethical_guardrail': True,
            })
        return profiles

    def ensure_sales_skillsets_per_agent(self, count: int = DEFAULT_SALES_SKILLS_PER_AGENT) -> Dict:
        """Ensure each agent has monetization-focused sales skills."""
        updated = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('sales_skill_profiles')
            if not isinstance(profiles, list) or len(profiles) < count:
                profiles = self._generate_sales_skill_profiles(agent_id, count=count)
                agent_data['sales_skill_profiles'] = profiles
                updated += 1
            else:
                agent_data['sales_skill_profiles'] = profiles[:count]

            skills = agent_data.setdefault('skills', [])
            for p in agent_data['sales_skill_profiles']:
                skill_name = p.get('skill_name')
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)

            agent_data['sales_skill_power_total'] = sum(
                int(p.get('conversion_power', 0)) for p in agent_data['sales_skill_profiles']
            )

        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'sales_skills_per_agent': count}

    def _generate_paypal_skill_profiles(self, agent_id: str, count: int = DEFAULT_PAYPAL_SKILLS_PER_AGENT) -> List[Dict]:
        """Generate PayPal-focused monetization skills for an agent."""
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        domains = [
            'paypal_checkout_speed',
            'paypal_trust_messaging',
            'paypal_conversion_copy',
            'paypal_cart_recovery',
            'paypal_order_value_lift',
            'paypal_coin_pack_upsell',
            'paypal_subscription_pitch',
            'paypal_one_click_rebuy',
            'paypal_refund_risk_reduction',
            'paypal_dispute_prevention',
            'paypal_mobile_checkout',
            'paypal_abandonment_prevent',
            'paypal_offer_personalization',
            'paypal_post_purchase_followup',
            'paypal_revenue_analytics',
        ]
        profiles = []
        for idx in range(1, max(1, count) + 1):
            domain = domains[(idx - 1) % len(domains)]
            skill_name = f"{normalized_agent}_paypal_{idx:02d}_{domain}"
            profiles.append({
                'skill_name': skill_name,
                'domain': domain,
                'paypal_power': 55 + (idx * 4),
                'value_points': 700 + (idx * 30),
                'ethical_guardrail': True,
            })
        return profiles

    def ensure_paypal_skillsets_per_agent(self, count: int = DEFAULT_PAYPAL_SKILLS_PER_AGENT) -> Dict:
        """Ensure each agent has PayPal monetization skills."""
        updated = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('paypal_skill_profiles')
            if not isinstance(profiles, list) or len(profiles) < count:
                profiles = self._generate_paypal_skill_profiles(agent_id, count=count)
                agent_data['paypal_skill_profiles'] = profiles
                updated += 1
            else:
                agent_data['paypal_skill_profiles'] = profiles[:count]

            skills = agent_data.setdefault('skills', [])
            for p in agent_data['paypal_skill_profiles']:
                skill_name = p.get('skill_name')
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)

            agent_data['paypal_skill_power_total'] = sum(
                int(p.get('paypal_power', 0)) for p in agent_data['paypal_skill_profiles']
            )

        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'paypal_skills_per_agent': count}

    def _generate_top25_upgrade_profiles(self, agent_id: str, count: int = DEFAULT_TOP25_SKILLS_PER_AGENT) -> List[Dict]:
        """Generate top-25 curated skills + upgrades for each agent."""
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        domains = [
            'conversion_orchestration',
            'offer_architecture',
            'pricing_intelligence',
            'bundle_engineering',
            'checkout_optimization',
            'cart_reactivation',
            'cross_sell_matrix',
            'upsell_sequence',
            'retention_automation',
            'lifecycle_revenue',
            'segment_personalization',
            'creative_performance',
            'landing_page_velocity',
            'cta_precision',
            'social_proof_systems',
            'trust_signal_stack',
            'paywall_refinement',
            'subscription_uplift',
            'profit_margin_guard',
            'refund_risk_control',
            'funnel_diagnostics',
            'kpi_forecasting',
            'sales_copy_adaptation',
            'campaign_compounding',
            'scale_readiness',
        ]
        profiles = []
        for idx in range(1, max(1, count) + 1):
            domain = domains[(idx - 1) % len(domains)]
            skill_name = f"{normalized_agent}_top25_{idx:02d}_{domain}"
            profiles.append({
                'skill_name': skill_name,
                'domain': domain,
                'upgrade_tier': f"u{idx:02d}",
                'upgrade_power': 80 + (idx * 5),
                'value_points': 1200 + (idx * 40),
                'ethical_guardrail': True,
            })
        return profiles

    def ensure_top25_skill_upgrades_per_agent(self, count: int = DEFAULT_TOP25_SKILLS_PER_AGENT) -> Dict:
        """Ensure each agent has the top-25 curated skills and upgrades."""
        updated = 0
        manifest = {}
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('top25_upgrade_profiles')
            if not isinstance(profiles, list) or len(profiles) < count:
                profiles = self._generate_top25_upgrade_profiles(agent_id, count=count)
                agent_data['top25_upgrade_profiles'] = profiles
                updated += 1
            else:
                agent_data['top25_upgrade_profiles'] = profiles[:count]

            skills = agent_data.setdefault('skills', [])
            for p in agent_data['top25_upgrade_profiles']:
                skill_name = p.get('skill_name')
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)

            agent_data['top25_upgrade_power_total'] = sum(
                int(p.get('upgrade_power', 0)) for p in agent_data['top25_upgrade_profiles']
            )
            manifest[agent_id] = [p.get('skill_name') for p in agent_data['top25_upgrade_profiles']]

        self.skillsets['top25_upgrade_manifest'] = {
            'generated_at': datetime.now().isoformat(),
            'skills_per_agent': count,
            'agents': manifest,
        }
        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'top25_skills_per_agent': count}

    def _shared_growth_skill_names(self, count: int = DEFAULT_SHARED_GROWTH_SKILLS) -> List[str]:
        """Generate shared skill pool names for cross-agent growth."""
        growth_domains = [
            'shop_conversion', 'product_story', 'price_psychology', 'sku_focus', 'offer_stack',
            'urgency_clean', 'scarcity_clean', 'checkout_friction', 'intent_capture', 'lead_qualify',
            'customer_voice', 'review_amplify', 'campaign_sync', 'channel_blend', 'remarketing_flow',
            'attribution_model', 'profit_guard', 'margin_opt', 'basket_boost', 'bundle_uplift',
            'churn_prevent', 'loyalty_ladder', 'referral_growth', 'sales_script', 'objection_map',
            'demo_to_close', 'close_rate', 'followup_sequence', 'deal_velocity', 'territory_focus',
            'pipeline_hygiene', 'forecast_stability', 'quota_focus', 'partner_enablement', 'merchandising',
            'catalog_priority', 'creative_refresh', 'offer_testing', 'geo_targeting', 'seasonality_signal',
            'discount_guardrail', 'cohort_value', 'aov_lift', 'retention_curve', 'win_loss_learning',
            'kpi_discipline', 'hero_product', 'ad_to_checkout', 'micro_conversion', 'revenue_velocity'
        ]
        return [f"shared_growth_{i+1:02d}_{growth_domains[i % len(growth_domains)]}" for i in range(max(1, count))]

    def ensure_shared_growth_skills(self, count: int = DEFAULT_SHARED_GROWTH_SKILLS) -> Dict:
        """
        Add a shared pool of growth skills across existing agents.
        Distribution strategy: round-robin over agents so every skill is represented.
        """
        agents = list(self.skillsets.get('agents', {}).keys())
        if not agents:
            return {'success': False, 'error': 'no_agents_found'}

        shared = self._shared_growth_skill_names(count=count)
        distribution = {agent_id: 0 for agent_id in agents}

        for idx, skill_name in enumerate(shared):
            agent_id = agents[idx % len(agents)]
            agent = self.skillsets['agents'][agent_id]
            skills = agent.setdefault('skills', [])
            if skill_name not in skills:
                skills.append(skill_name)
            distribution[agent_id] += 1

        # Keep a manifest for UI/reporting.
        self.skillsets['shared_growth_skill_manifest'] = {
            'generated_at': datetime.now().isoformat(),
            'total_shared_skills': len(shared),
            'skills': shared,
            'distribution': distribution,
        }
        self.save_skillsets()
        return {
            'success': True,
            'total_shared_skills': len(shared),
            'distribution': distribution,
        }

    def update_agent_progression_from_results(
        self,
        experience_multiplier: float = 10.0,
        success_weight: float = 0.7,
    ) -> Dict:
        """
        Update agent experience/level based on tracked ability results.
        Also prepares next-step recommendations per agent.
        """
        try:
            from backend.services.agent_ability_tracker import agent_ability_tracker
            stats = agent_ability_tracker.get_all_stats()
            agent_stats = stats.get('agents', {}) if isinstance(stats, dict) else {}
        except Exception:
            agent_stats = {}

        updated = 0
        next_steps = {}
        for agent_id, data in self.skillsets.get('agents', {}).items():
            tracked = agent_stats.get(agent_id, {})
            total_exec = int(tracked.get('total_executions', 0))
            success_rate = float(tracked.get('success_rate', 0.0))

            gained_xp = int(total_exec * experience_multiplier * ((success_rate / 100.0) * success_weight + (1.0 - success_weight)))
            data['experience'] = int(data.get('experience', 0)) + max(0, gained_xp)
            data['level'] = max(1, int(data['experience'] // 500) + 1)

            # Result-based completion marker
            data['result_score'] = round((success_rate * 0.6) + (min(total_exec, 1000) / 10.0 * 0.4), 2)

            top_skills = tracked.get('top_skills', []) if isinstance(tracked, dict) else []
            weak = [s for s in top_skills if int(s.get('failure', 0)) > int(s.get('success', 0))]
            focus_skill = weak[0]['skill'] if weak else (top_skills[0]['skill'] if top_skills else None)
            steps = []
            if focus_skill:
                steps.append(f"Improve reliability for {focus_skill}")
            steps.append("Run battle optimization pass")
            steps.append("Run sales conversion optimization pass")
            steps.append("Track next 50 executions and recalculate")
            next_steps[agent_id] = steps
            updated += 1

        self.skillsets['agent_next_steps'] = {
            'generated_at': datetime.now().isoformat(),
            'steps_by_agent': next_steps,
        }
        self.save_skillsets()
        return {
            'success': True,
            'agents_updated': updated,
            'next_steps_generated': len(next_steps),
        }

    def get_best_agent_for_sale(self) -> Dict:
        """Pick best-performing agent candidate for shop sale."""
        best = None
        for agent_id, data in self.skillsets.get('agents', {}).items():
            level = int(data.get('level', 1))
            exp = int(data.get('experience', 0))
            result_score = float(data.get('result_score', 0.0))
            sales_power = int(data.get('sales_skill_power_total', 0))
            battle_power = int(data.get('battle_skill_power_total', 0))
            unique_value = int(data.get('unique_skillset_value_total', 0))
            composite = (level * 200) + (exp * 0.2) + (result_score * 10) + (sales_power * 0.8) + (battle_power * 0.5) + (unique_value * 0.001)
            candidate = {
                'agent_id': agent_id,
                'name': data.get('name', agent_id),
                'level': level,
                'experience': exp,
                'result_score': round(result_score, 2),
                'sales_skill_power_total': sales_power,
                'battle_skill_power_total': battle_power,
                'unique_skillset_value_total': unique_value,
                'composite_score': round(composite, 2),
            }
            if best is None or candidate['composite_score'] > best['composite_score']:
                best = candidate
        return best or {}

    def _generate_unique_skill_profiles(self, agent_id: str, agent_name: str, count: int = DEFAULT_UNIQUE_SKILLS_PER_AGENT) -> List[Dict]:
        """Generate unique premium skills for an agent with value points."""
        profiles = []
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        tiers = ['mythic', 'legendary', 'epic', 'elite', 'prime']
        domains = [
            'autonomy',
            'reasoning',
            'recovery',
            'content',
            'analytics',
            'security',
            'orchestration',
            'optimization',
            'coordination',
            'learning',
            'prediction',
            'compliance',
            'synthesis',
            'operations',
            'resilience',
            'innovation',
            'communication',
            'research',
            'execution',
            'monitoring',
            'quality',
            'deployment',
            'scaling',
            'integration',
            'strategy',
            'ai_assist',
            'ai_follow',
            'ai_win',
        ]
        for idx in range(1, max(1, count) + 1):
            domain = domains[(idx - 1) % len(domains)]
            tier = tiers[(idx - 1) % len(tiers)]
            skill_name = f"{normalized_agent}_unique_{idx:02d}_{domain}_{tier}"
            profiles.append({
                'skill_name': skill_name,
                'title': f"{agent_name} Unique Skill {idx}",
                'domain': domain,
                'tier': tier,
                'value_points': 1000 + (idx * 25),  # 10x-value style weighting
                'rarity_weight': round(1.0 + (idx * 0.08), 2),
                'auto_enabled': True,
            })
        return profiles

    def _ensure_unique_skillsets_for_agents(self):
        """Ensure each agent has 250 unique high-value skills."""
        agents = self.skillsets.get('agents', {})
        for agent_id, agent_data in agents.items():
            agent_name = agent_data.get('name', agent_id)
            profiles = agent_data.get('unique_skill_profiles')
            if not isinstance(profiles, list):
                profiles = []

            if len(profiles) < DEFAULT_UNIQUE_SKILLS_PER_AGENT:
                # Preserve existing profiles, append only missing tail.
                start_idx = len(profiles) + 1
                generated = self._generate_unique_skill_profiles(
                    agent_id,
                    agent_name,
                    count=DEFAULT_UNIQUE_SKILLS_PER_AGENT,
                )
                profiles = generated[:DEFAULT_UNIQUE_SKILLS_PER_AGENT]
                if start_idx > 1:
                    # Keep prior ordering/data when possible, but ensure full normalized set.
                    for i in range(min(len(agent_data.get('unique_skill_profiles', [])), len(profiles))):
                        if isinstance(agent_data['unique_skill_profiles'][i], dict):
                            profiles[i].update({k: v for k, v in agent_data['unique_skill_profiles'][i].items() if k in profiles[i]})
                agent_data['unique_skill_profiles'] = profiles
            else:
                agent_data['unique_skill_profiles'] = profiles[:DEFAULT_UNIQUE_SKILLS_PER_AGENT]

            skills = agent_data.setdefault('skills', [])
            unique_skill_names = [p.get('skill_name') for p in agent_data['unique_skill_profiles'] if p.get('skill_name')]
            for unique_skill in unique_skill_names:
                if unique_skill not in skills:
                    skills.append(unique_skill)

            # Total value indicator for "big system" prioritization.
            agent_data['unique_skillset_value_total'] = sum(
                int(p.get('value_points', 0)) for p in profiles
            )

    def _generate_battle_skill_profiles(self, agent_id: str, count: int = DEFAULT_BATTLE_SKILLS_PER_AGENT) -> List[Dict]:
        """Generate specialized battle skills for an agent."""
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        archetypes = [
            'berserker', 'guardian', 'assassin', 'strategist', 'duelist',
            'sniper', 'commander', 'saboteur', 'tank', 'support',
            'counter', 'rush', 'control', 'endgame', 'arena',
        ]
        battle_profiles = []
        for idx in range(1, max(1, count) + 1):
            archetype = archetypes[(idx - 1) % len(archetypes)]
            skill_name = f"{normalized_agent}_battle_{idx:02d}_{archetype}"
            battle_profiles.append({
                'skill_name': skill_name,
                'battle_power': 50 + (idx * 5),
                'cooldown': max(1, 20 - idx),
                'class': archetype,
            })
        return battle_profiles

    def ensure_battle_skills_per_agent(self, count: int = DEFAULT_BATTLE_SKILLS_PER_AGENT) -> Dict:
        """Ensure each agent has a specialized set of battle skills."""
        updated_agents = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('battle_skill_profiles')
            if not isinstance(profiles, list) or len(profiles) < count:
                profiles = self._generate_battle_skill_profiles(agent_id, count=count)
                agent_data['battle_skill_profiles'] = profiles
                updated_agents += 1

            skills = agent_data.setdefault('skills', [])
            for profile in profiles[:count]:
                skill_name = profile.get('skill_name')
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)

            agent_data['battle_skill_power_total'] = sum(
                int(p.get('battle_power', 0)) for p in profiles[:count]
            )

        self.save_skillsets()
        return {
            'success': True,
            'agents_updated': updated_agents,
            'battle_skills_per_agent': count,
        }

    def get_battle_skill_set_for_rulebook(self) -> Dict:
        """Export battle skill set for rulebooks and compendium. Used to wire agent battle knowledge."""
        out = {'agents': {}, 'skill_list': [], 'updated_at': datetime.now().isoformat()}
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('battle_skill_profiles') or []
            names = [p.get('skill_name') for p in profiles if p.get('skill_name')]
            if names:
                out['agents'][agent_id] = {
                    'name': agent_data.get('name', agent_id),
                    'battle_skills': names,
                    'battle_skill_power_total': agent_data.get('battle_skill_power_total', 0),
                }
                out['skill_list'].extend(names)
        out['skill_list'] = list(dict.fromkeys(out['skill_list']))
        return out

    KNOWLEDGE_SKILLS = [
        'sync_compendium', 'update_rulebook_docs', 'maintain_page_info',
        'learn_technology', 'write_rulebook_finish', 'agent_knowledge_push',
    ]

    AI_SKILLS = [
        'ai_follow_user_action',
        'ai_suggest_next',
        'ai_auto_optimize',
        'ai_nice_and_easy',
        'ai_assist_task',
        'ai_learn_from_action',
        'ai_win_with_user',
    ]

    # Register Intelligence / blueprint parity — see register_intelligence, agent_skillset_ops_service
    BLUEPRINT_ROUTE_FIXER_SKILLS = [
        'blueprint_gap_scan',
        'route_register_audit',
        'frontend_backend_parity_check',
        'missing_endpoint_triage',
    ]

    # REST/API surface health — frontend vs backend discovery (orchestrator discover_all)
    API_SERVICE_SKILLS = [
        'api_contract_probe',
        'rest_endpoint_health_scan',
        'api_version_consistency_check',
        'openapi_alignment_hint',
    ]

    def ensure_blueprint_route_fixer_skills_per_agent(self) -> Dict:
        """Ensure every agent can participate in blueprint & route fixer workflows."""
        updated = 0
        for _agent_id, agent_data in self.skillsets.get('agents', {}).items():
            skills = agent_data.setdefault('skills', [])
            for sk in self.BLUEPRINT_ROUTE_FIXER_SKILLS:
                if sk not in skills:
                    skills.append(sk)
                    updated += 1
        self.save_skillsets()
        return {
            'success': True,
            'skills_added': updated,
            'blueprint_route_fixer_skills': self.BLUEPRINT_ROUTE_FIXER_SKILLS,
        }

    def ensure_api_service_skills_per_agent(self) -> Dict:
        """Ensure every agent has API service / contract awareness skills."""
        updated = 0
        for _agent_id, agent_data in self.skillsets.get('agents', {}).items():
            skills = agent_data.setdefault('skills', [])
            for sk in self.API_SERVICE_SKILLS:
                if sk not in skills:
                    skills.append(sk)
                    updated += 1
        self.save_skillsets()
        return {
            'success': True,
            'skills_added': updated,
            'api_service_skills': self.API_SERVICE_SKILLS,
        }

    def ensure_ai_skills_per_agent(self) -> Dict:
        """Ensure every agent has AI skills so they do the job nice and easy."""
        updated = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            skills = agent_data.setdefault('skills', [])
            for sk in self.AI_SKILLS:
                if sk not in skills:
                    skills.append(sk)
                    updated += 1
        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'ai_skills': self.AI_SKILLS}

    def ensure_knowledge_skills_per_agent(self) -> Dict:
        """Ensure every agent has knowledge/compendium skills to maintain updated rulebook and page info."""
        updated = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            skills = agent_data.setdefault('skills', [])
            for sk in self.KNOWLEDGE_SKILLS:
                if sk not in skills:
                    skills.append(sk)
                    updated += 1
        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'knowledge_skills': self.KNOWLEDGE_SKILLS}

    def ensure_casino_agent_skillsets(self) -> Dict:
        """Register casino agent models (e.g. Kelly) in the skillset registry."""
        import json
        import os
        models_path = os.path.join(self.base_dir, 'data', 'casino_agent_models.json')
        models: Dict = {}
        if os.path.isfile(models_path):
            try:
                with open(models_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                models = raw.get('models') if isinstance(raw.get('models'), dict) else raw
            except Exception:
                models = {}
        if not isinstance(models, dict):
            models = {}
        agents = self.skillsets.setdefault('agents', {})
        updated = 0
        for model_id, row in models.items():
            if not isinstance(row, dict):
                continue
            agent = agents.setdefault(model_id, {'skills': [], 'model_id': model_id})
            skills = agent.setdefault('skills', [])
            for sk in row.get('skills') or ['kelly_sizing']:
                if sk not in skills:
                    skills.append(sk)
                    updated += 1
            agent['strategy'] = row.get('strategy') or agent.get('strategy')
            agent['name'] = row.get('name') or agent.get('name') or model_id
        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'casino_models': list(models.keys())}

    def _generate_criticism_skill_profiles(self, agent_id: str, count: int = DEFAULT_CRITICISM_SKILLS_PER_AGENT) -> List[Dict]:
        """Generate criticism skills: review, feedback, and quality assessment for code, content, and decisions."""
        normalized_agent = str(agent_id).strip().lower().replace(' ', '_')
        domains = [
            'code_review', 'logic_gaps', 'edge_case_audit', 'security_audit', 'performance_review',
            'copy_review', 'tone_consistency', 'fact_check', 'bias_detection', 'accessibility_review',
            'ux_critique', 'flow_analysis', 'assumption_challenge', 'risk_flag', 'alternative_suggest',
            'documentation_quality', 'api_design_review', 'test_coverage_critique', 'refactor_priority',
            'stakeholder_feedback',
        ]
        profiles = []
        for idx in range(1, max(1, count) + 1):
            domain = domains[(idx - 1) % len(domains)]
            skill_name = f"{normalized_agent}_criticism_{idx:02d}_{domain}"
            profiles.append({
                'skill_name': skill_name,
                'domain': domain,
                'criticism_power': 35 + (idx * 4),
                'value_points': 400 + (idx * 25),
                'constructive_only': True,
            })
        return profiles

    def ensure_criticism_skills_per_agent(self, count: int = DEFAULT_CRITICISM_SKILLS_PER_AGENT) -> Dict:
        """Ensure each agent has criticism skills for review, feedback, and quality assessment."""
        updated = 0
        for agent_id, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('criticism_skill_profiles')
            if not isinstance(profiles, list) or len(profiles) < count:
                profiles = self._generate_criticism_skill_profiles(agent_id, count=count)
                agent_data['criticism_skill_profiles'] = profiles
                updated += 1
            else:
                agent_data['criticism_skill_profiles'] = profiles[:count]

            skills = agent_data.setdefault('skills', [])
            for p in agent_data['criticism_skill_profiles']:
                skill_name = p.get('skill_name')
                if skill_name and skill_name not in skills:
                    skills.append(skill_name)

            agent_data['criticism_skill_power_total'] = sum(
                int(p.get('criticism_power', 0)) for p in agent_data['criticism_skill_profiles']
            )

        self.save_skillsets()
        return {'success': True, 'agents_updated': updated, 'criticism_skills_per_agent': count}

    def rebalance_unique_skill_values(self, target_total: int = 500000) -> Dict:
        """
        Rebalance unique skill values per agent to a target total.
        Keeps relative ordering while normalizing totals.
        """
        adjusted = 0
        for _, agent_data in self.skillsets.get('agents', {}).items():
            profiles = agent_data.get('unique_skill_profiles') or []
            if not profiles:
                continue
            current_total = sum(int(p.get('value_points', 0)) for p in profiles)
            if current_total <= 0:
                continue
            scale = float(target_total) / float(current_total)
            for profile in profiles:
                base = int(profile.get('value_points', 0))
                profile['value_points'] = max(1, int(round(base * scale)))
            agent_data['unique_skillset_value_total'] = sum(int(p.get('value_points', 0)) for p in profiles)
            adjusted += 1

        self.save_skillsets()
        return {
            'success': True,
            'agents_rebalanced': adjusted,
            'target_total_per_agent': target_total,
        }
    
    def _default_skillsets(self) -> Dict:
        """Default skillsets"""
        return {
            'agents': {
                'master_fix_agent': {
                    'name': 'Master Fix Agent',
                    'skills': [
                        'check_blueprints',
                        'verify_database',
                        'check_file_integrity',
                        'scan_missing_methods',
                        'monitor_system_health',
                        'run_full_diagnostic',
                        'execute_python_file',
                        'execute_python_code',
                        'list_python_scripts',
                        'create_support_ticket',
                        'get_support_tickets',
                        'get_services'
                    ],
                    'level': 5,
                    'experience': 1000
                },
                'monitoring_agent': {
                    'name': 'Monitoring Agent',
                    'skills': [
                        'monitor_system_health',
                        'monitor_performance',
                        'monitor_changes',
                        'monitor_api_structure'
                    ],
                    'level': 3,
                    'experience': 500
                },
                'scanner_agent': {
                    'name': 'Scanner Agent',
                    'skills': [
                        'scan_blueprints',
                        'scan_routes',
                        'scan_services',
                        'find_missing_methods'
                    ],
                    'level': 2,
                    'experience': 300
                },
                'content_generator_agent': {
                    'name': 'Content Generator Agent',
                    'skills': [
                        'generate_video',
                        'generate_clip',
                        'generate_image',
                        'generate_audio',
                        'generate_text',
                        'optimize_content',
                        'analyze_trends',
                        'create_template',
                        'generate_movie_clip',  # NEW: Generate movie clips
                        'create_epic_content',  # NEW: Create epic content
                        'the_end_war_generation'  # NEW: The End War movie generation
                    ],
                    'level': 1,
                    'experience': 0
                },
                'error_migration_agent': {
                    'name': 'Error Migration Agent',
                    'skills': [
                        'migrate_error_handlers',  # NEW: Migrate error handlers
                        'analyze_error_patterns',  # NEW: Analyze error patterns
                        'automate_migration',  # NEW: Automate migration process
                        'validate_migration',  # NEW: Validate migration results
                        'track_migration_progress',  # NEW: Track migration progress
                        'optimize_error_handling',  # NEW: Optimize error handling
                        'batch_migration',  # NEW: Batch migration operations
                        'error_handler_analysis'  # NEW: Analyze error handlers
                    ],
                    'level': 2,
                    'experience': 500
                },
                'master_dashboard_agent': {
                    'name': 'Master Dashboard Agent',
                    'skills': [
                        'generate_top10_insights',  # NEW: Generate top 10 insights
                        'aggregate_system_stats',  # NEW: Aggregate system statistics
                        'real_time_monitoring',  # NEW: Real-time monitoring
                        'dashboard_optimization',  # NEW: Dashboard optimization
                        'data_visualization',  # NEW: Data visualization
                        'performance_tracking',  # NEW: Performance tracking
                        'trend_analysis',  # NEW: Trend analysis
                        'predictive_analytics'  # NEW: Predictive analytics
                    ],
                    'level': 3,
                    'experience': 750
                },
                'ai_intelligence_agent': {
                    'name': 'AI Intelligence Agent',
                    'skills': [
                        'generate_ai_top10',  # NEW: Generate AI top 10
                        'intelligence_aggregation',  # NEW: Intelligence aggregation
                        'pattern_recognition',  # NEW: Pattern recognition
                        'predictive_modeling',  # NEW: Predictive modeling
                        'insight_generation',  # NEW: Insight generation
                        'optimization_recommendations',  # NEW: Optimization recommendations
                        'learning_analysis',  # NEW: Learning analysis
                        'intelligence_synthesis'  # NEW: Intelligence synthesis
                    ],
                    'level': 4,
                    'experience': 1000
                },
                'battle_strategy_agent': {
                    'name': 'Battle Strategy Agent',
                    'skills': [
                        'analyze_battle',
                        'create_strategy',
                        'predict_outcome',
                        'optimize_tactics',
                        'team_coordination',
                        'defense_planning',
                        'offense_planning',
                        'counter_strategy'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'social_engagement_agent': {
                    'name': 'Social Engagement Agent',
                    'skills': [
                        'manage_friends',
                        'coordinate_events',
                        'facilitate_discussions',
                        'moderate_content',
                        'build_community',
                        'organize_groups',
                        'manage_messages',
                        'track_engagement'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'analytics_agent': {
                    'name': 'Analytics Agent',
                    'skills': [
                        'analyze_user_behavior',
                        'track_metrics',
                        'generate_reports',
                        'predict_trends',
                        'identify_patterns',
                        'optimize_performance',
                        'data_visualization',
                        'insight_generation'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'security_agent': {
                    'name': 'Security Agent',
                    'skills': [
                        'scan_vulnerabilities',
                        'monitor_threats',
                        'detect_anomalies',
                        'enforce_policies',
                        'audit_access',
                        'incident_response',
                        'security_analysis',
                        'threat_prevention'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'performance_optimizer_agent': {
                    'name': 'Performance Optimizer Agent',
                    'skills': [
                        'optimize_queries',
                        'cache_management',
                        'resource_optimization',
                        'speed_improvement',
                        'load_balancing',
                        'database_tuning',
                        'api_optimization',
                        'performance_monitoring'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'user_experience_agent': {
                    'name': 'User Experience Agent',
                    'skills': [
                        'analyze_ux',
                        'improve_navigation',
                        'optimize_ui',
                        'gather_feedback',
                        'a_b_testing',
                        'usability_testing',
                        'accessibility_check',
                        'user_satisfaction'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'integration_agent': {
                    'name': 'Integration Agent',
                    'skills': [
                        'integrate_api',
                        'manage_endpoints',
                        'sync_data',
                        'coordinate_services',
                        'handle_webhooks',
                        'api_testing',
                        'integration_monitoring',
                        'service_coordination'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'agent_judge': {
                    'name': 'Agent Judge',
                    'skills': [
                        'judge_content_quality',
                        'evaluate_agent_performance',
                        'rate_system_health',
                        'assess_code_quality',
                        'judge_user_behavior',
                        'evaluate_competitions',
                        'rate_achievements',
                        'judge_creativity',
                        'evaluate_efficiency',
                        'assess_innovation',
                        'judge_collaboration',
                        'rate_overall_performance'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'data_processor_agent': {
                    'name': 'Data Processor Agent',
                    'skills': [
                        'process_data',
                        'transform_data',
                        'validate_data',
                        'clean_data',
                        'aggregate_data',
                        'export_data',
                        'import_data',
                        'data_migration'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'notification_agent': {
                    'name': 'Notification Agent',
                    'skills': [
                        'send_notifications',
                        'schedule_notifications',
                        'manage_channels',
                        'template_notifications',
                        'track_deliveries',
                        'handle_responses',
                        'notification_analytics',
                        'batch_notifications'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'workflow_agent': {
                    'name': 'Workflow Agent',
                    'skills': [
                        'create_workflow',
                        'execute_workflow',
                        'monitor_workflow',
                        'optimize_workflow',
                        'schedule_workflow',
                        'handle_errors',
                        'workflow_analytics',
                        'automate_tasks'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'ai_trainer_agent': {
                    'name': 'AI Trainer Agent',
                    'skills': [
                        'train_models',
                        'fine_tune_models',
                        'evaluate_models',
                        'optimize_models',
                        'deploy_models',
                        'monitor_models',
                        'update_models',
                        'model_analytics'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'tester_agent': {
                    'name': 'Tester Agent',
                    'skills': [
                        'ui_smoke_test',
                        'cross_browser_test',
                        'mobile_responsive_audit',
                        'accessibility_audit',
                        'performance_lighthouse_check',
                        'api_contract_validation',
                        'visual_regression_check',
                        'error_reproduction',
                        'test_plan_generation',
                        'release_quality_gate'
                    ],
                    'level': 4,
                    'experience': 1200
                },
                'quality_assurance_agent': {
                    'name': 'Quality Assurance Agent',
                    'skills': [
                        'run_tests',
                        'generate_tests',
                        'code_review',
                        'bug_detection',
                        'performance_testing',
                        'security_testing',
                        'regression_testing',
                        'test_automation'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'deployment_agent': {
                    'name': 'Deployment Agent',
                    'skills': [
                        'deploy_code',
                        'manage_releases',
                        'rollback_deployments',
                        'monitor_deployments',
                        'environment_management',
                        'version_control',
                        'ci_cd_integration',
                        'deployment_automation'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'backup_agent': {
                    'name': 'Backup Agent',
                    'skills': [
                        'create_backups',
                        'restore_backups',
                        'schedule_backups',
                        'verify_backups',
                        'manage_backup_storage',
                        'backup_encryption',
                        'disaster_recovery',
                        'backup_analytics'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'resource_manager_agent': {
                    'name': 'Resource Manager Agent',
                    'skills': [
                        'monitor_resources',
                        'allocate_resources',
                        'optimize_resources',
                        'scale_resources',
                        'manage_capacity',
                        'cost_optimization',
                        'resource_planning',
                        'resource_analytics'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'compliance_agent': {
                    'name': 'Compliance Agent',
                    'skills': [
                        'check_compliance',
                        'enforce_policies',
                        'audit_logs',
                        'generate_reports',
                        'regulatory_tracking',
                        'policy_management',
                        'compliance_monitoring',
                        'risk_assessment'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'learning_agent': {
                    'name': 'Learning Agent',
                    'skills': [
                        'learn_from_data',
                        'adapt_behavior',
                        'pattern_recognition',
                        'knowledge_extraction',
                        'skill_improvement',
                        'experience_learning',
                        'meta_learning',
                        'continuous_improvement'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'communication_agent': {
                    'name': 'Communication Agent',
                    'skills': [
                        'handle_communications',
                        'translate_languages',
                        'summarize_content',
                        'generate_responses',
                        'context_understanding',
                        'sentiment_analysis',
                        'communication_analytics',
                        'multi_modal_communication'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'research_agent': {
                    'name': 'Research Agent',
                    'skills': [
                        'conduct_research',
                        'gather_information',
                        'analyze_findings',
                        'synthesize_knowledge',
                        'generate_hypotheses',
                        'validate_claims',
                        'research_automation',
                        'knowledge_management'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'innovation_agent': {
                    'name': 'Innovation Agent',
                    'skills': [
                        'generate_ideas',
                        'evaluate_concepts',
                        'prototype_solutions',
                        'test_innovations',
                        'identify_opportunities',
                        'creative_problem_solving',
                        'innovation_analytics',
                        'trend_spotting'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'collaboration_agent': {
                    'name': 'Collaboration Agent',
                    'skills': [
                        'facilitate_collaboration',
                        'coordinate_teams',
                        'manage_projects',
                        'resolve_conflicts',
                        'share_knowledge',
                        'team_analytics',
                        'collaboration_tools',
                        'relationship_management'
                    ],
                    'level': 1,
                    'experience': 0
                },
                'llm_orchestrator_agent': {
                    'name': 'LLM Orchestrator Agent',
                    'skills': [
                        'chat_completion',
                        'embed_text',
                        'route_by_task',
                        'circuit_breaker_handle',
                        'provider_fallback',
                        'openai_compat',
                        'groq_speed',
                        'gemini_context',
                        'openrouter_multi_model',
                        'deepseek_reason'
                    ],
                    'level': 4,
                    'experience': 900,
                    'style': 'neon',
                    'accent_color': '#00d4ff',
                    'design': 'minimal'
                },
                'video_ai_agent': {
                    'name': 'Video AI Agent',
                    'skills': [
                        'runway_gen4_clip',
                        'pika_labs_clip',
                        'modelslab_cogvideox',
                        'stability_image_gen',
                        'pollinations_image',
                        'movie_clip_generation',
                        'epic_content_create',
                        'narration_tts_pipeline'
                    ],
                    'level': 3,
                    'experience': 600,
                    'style': 'cinema',
                    'accent_color': '#ff6b35',
                    'design': 'card'
                },
                'tts_narration_agent': {
                    'name': 'TTS Narration Agent',
                    'skills': [
                        'piper_tts_local',
                        'elevenlabs_tts',
                        'gtts_fallback',
                        'pyttsx3_offline',
                        'audio_enhance_deepfilter',
                        'audio_enhance_loudnorm',
                        'generate_narration_segments',
                        'voice_consistency'
                    ],
                    'level': 3,
                    'experience': 500,
                    'style': 'warm',
                    'accent_color': '#9d4edd',
                    'design': 'compact'
                },
                'intelligence_aggregator_agent': {
                    'name': 'Intelligence Aggregator Agent',
                    'skills': [
                        'get_research_papers',
                        'get_news_tech',
                        'get_trending',
                        'arxiv_category_fetch',
                        'cache_research_6h',
                        'cache_news_1h',
                        'intelligence_all_endpoint',
                        'insight_synthesis'
                    ],
                    'level': 3,
                    'experience': 550,
                    'style': 'dashboard',
                    'accent_color': '#06ffa5',
                    'design': 'card'
                },
                'agent_research_tracker_agent': {
                    'name': 'Agent Research Tracker',
                    'skills': [
                        'research_start',
                        'research_finding',
                        'research_summary',
                        'monitor_targets',
                        'auto_research',
                        'auto_research_summary',
                        'trigger_research_completed',
                        'topic_api_structure',
                        'topic_performance_security'
                    ],
                    'level': 3,
                    'experience': 650,
                    'style': 'dark',
                    'accent_color': '#ffd60a',
                    'design': 'minimal'
                },
                'content_ai_agent': {
                    'name': 'Content AI Agent',
                    'skills': [
                        'generate_text_llm',
                        'generate_image_providers',
                        'generate_video_pipeline',
                        'generate_audio_tts',
                        'optimize_content',
                        'analyze_trends',
                        'create_template',
                        'ai_content_unified'
                    ],
                    'level': 4,
                    'experience': 800,
                    'style': 'creative',
                    'accent_color': '#e0aaff',
                    'design': 'card'
                },
                'security_audit_agent': {
                    'name': 'Security Audit Agent',
                    'skills': [
                        'scan_vulnerabilities',
                        'threat_detection',
                        'anomaly_detection',
                        'policy_enforcement',
                        'access_audit',
                        'incident_response',
                        'security_analysis',
                        'compliance_check'
                    ],
                    'level': 3,
                    'experience': 550,
                    'style': 'alert',
                    'accent_color': '#ef233c',
                    'design': 'compact'
                },
                'performance_agent': {
                    'name': 'Performance Agent',
                    'skills': [
                        'query_optimization',
                        'cache_management',
                        'resource_optimization',
                        'speed_improvement',
                        'load_balancing',
                        'db_tuning',
                        'api_optimization',
                        'lighthouse_metrics'
                    ],
                    'level': 3,
                    'experience': 500,
                    'style': 'speed',
                    'accent_color': '#00f5d4',
                    'design': 'minimal'
                },
                'support_ticket_agent': {
                    'name': 'Support Ticket Agent',
                    'skills': [
                        'create_support_ticket',
                        'get_support_tickets',
                        'triage_requests',
                        'suggest_solutions',
                        'escalation_handling',
                        'user_help_context',
                        'knowledge_base_lookup',
                        'response_draft'
                    ],
                    'level': 2,
                    'experience': 300,
                    'style': 'friendly',
                    'accent_color': '#48cae4',
                    'design': 'card'
                }
            },
            'test_players': {
                'test_player_1': {
                    'name': 'Test Player 1',
                    'skills': [
                        'basic_diagnostic',
                        'view_statistics'
                    ],
                    'level': 1,
                    'experience': 50
                },
                'test_player_2': {
                    'name': 'Test Player 2',
                    'skills': [
                        'basic_diagnostic',
                        'view_statistics',
                        'run_quests'
                    ],
                    'level': 2,
                    'experience': 150
                }
            }
        }
    
    def save_skillsets(self):
        """Save skillsets"""
        try:
            with open(self.skillsets_file, 'w') as f:
                json.dump(self.skillsets, f, indent=2, default=str)
            try:
                from backend.services.unified_points_sync import unified_points_sync_device
                unified_points_sync_device.record_domain_sync('agent_skillsets')
            except Exception:
                pass
        except Exception as e:
            print(f"Error saving skillsets: {e}")
    
    def get_skillset(self, agent_id: str, agent_type: str = 'agents') -> Dict:
        """Get skillset for an agent"""
        return self.skillsets.get(agent_type, {}).get(agent_id, {})
    
    def add_skill(self, agent_id: str, skill: str, agent_type: str = 'agents'):
        """Add skill to agent"""
        if agent_type not in self.skillsets:
            self.skillsets[agent_type] = {}
        
        if agent_id not in self.skillsets[agent_type]:
            self.skillsets[agent_type][agent_id] = {
                'name': agent_id,
                'skills': [],
                'level': 1,
                'experience': 0
            }
        
        if skill not in self.skillsets[agent_type][agent_id]['skills']:
            self.skillsets[agent_type][agent_id]['skills'].append(skill)
            self.save_skillsets()
    
    def remove_skill(self, agent_id: str, skill: str, agent_type: str = 'agents'):
        """Remove skill from agent"""
        if agent_id in self.skillsets.get(agent_type, {}):
            skills = self.skillsets[agent_type][agent_id].get('skills', [])
            if skill in skills:
                skills.remove(skill)
                self.save_skillsets()
    
    def level_up(self, agent_id: str, agent_type: str = 'agents', experience: int = 100):
        """Level up agent"""
        if agent_id in self.skillsets.get(agent_type, {}):
            agent = self.skillsets[agent_type][agent_id]
            agent['experience'] = agent.get('experience', 0) + experience
            
            # Level up every 500 experience
            new_level = (agent['experience'] // 500) + 1
            if new_level > agent.get('level', 1):
                agent['level'] = new_level
                print(f"🎉 {agent['name']} leveled up to {new_level}!")
            
            self.save_skillsets()
    
    def get_all_skillsets(self) -> Dict:
        """Get all skillsets"""
        return self.skillsets
    
    def get_skillset_stats(self) -> Dict:
        """Get statistics for all skillsets"""
        stats = {
            'total_agents': 0,
            'total_test_players': 0,
            'total_skills': 0,
            'agents_by_level': {},
            'skills_by_category': {},
            'top_skills': []
        }
        
        all_skills = set()
        
        # Count agents
        for agent_type in ['agents', 'test_players']:
            agents = self.skillsets.get(agent_type, {})
            count_key = 'total_agents' if agent_type == 'agents' else 'total_test_players'
            stats[count_key] = len(agents)
            
            for agent_id, agent_data in agents.items():
                level = agent_data.get('level', 1)
                stats['agents_by_level'][level] = stats['agents_by_level'].get(level, 0) + 1
                
                skills = agent_data.get('skills', [])
                all_skills.update(skills)
        
        stats['total_skills'] = len(all_skills)
        
        # Count skill usage
        for agent_type in ['agents', 'test_players']:
            agents = self.skillsets.get(agent_type, {})
            for agent_id, agent_data in agents.items():
                skills = agent_data.get('skills', [])
                for skill in skills:
                    stats['skills_by_category'][skill] = stats['skills_by_category'].get(skill, 0) + 1
        
        # Get top skills
        top_skills = sorted(stats['skills_by_category'].items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_skills'] = [{'skill': skill, 'count': count} for skill, count in top_skills]
        
        return stats
    
    def get_agent_count(self, agent_type: str = 'agents') -> int:
        """Get count of agents"""
        return len(self.skillsets.get(agent_type, {}))
    
    def get_total_skills(self) -> int:
        """Get total unique skills across all agents"""
        all_skills = set()
        for agent_type in ['agents', 'test_players']:
            agents = self.skillsets.get(agent_type, {})
            for agent_id, agent_data in agents.items():
                skills = agent_data.get('skills', [])
                all_skills.update(skills)
        return len(all_skills)
    
    def search_agents_by_skill(self, skill: str) -> List[Dict]:
        """Search for agents with a specific skill"""
        results = []
        for agent_type in ['agents', 'test_players']:
            agents = self.skillsets.get(agent_type, {})
            for agent_id, agent_data in agents.items():
                skills = agent_data.get('skills', [])
                if skill in skills:
                    results.append({
                        'agent_id': agent_id,
                        'agent_type': agent_type,
                        'name': agent_data.get('name', agent_id),
                        'level': agent_data.get('level', 1),
                        'experience': agent_data.get('experience', 0)
                    })
        return results

# Global instance (lite init under pytest � avoids multi-minute skillset expansion on import)
def _agent_skillset_singleton():
    if os.environ.get('AGENT_SKILLSET_LITE_INIT') == '1':
        inst = AgentSkillset.__new__(AgentSkillset)
        inst.base_dir = BASE_DIR
        inst.skillsets = {'agents': {}}
        inst.skillsets_file = os.path.join(inst.base_dir, 'logs', 'agent_skillsets', 'skillsets.json')
        return inst
    return AgentSkillset()


agent_skillset = _agent_skillset_singleton()
