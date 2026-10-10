"""
Keyword Foundation System
Translates Danish keywords to English AI power context for game/XP system
These keywords form the foundation/construction yard for the game
"""

# Danish to English AI Power Context Translation
KEYWORD_TRANSLATIONS = {
    # Power & Might
    'Chock': 'Shock',
    'Power': 'Power',
    'Might': 'Might',
    'Money': 'Currency',
    'Wealth': 'Wealth',
    'Riches': 'Riches',
    
    # War & Conflict
    'War': 'Conflict',
    'Ground contact': 'Territorial Control',
    'Gravity': 'Gravitational Force',
    
    # Knowledge & Skills
    'Vocabulary': 'Linguistic Intelligence',
    'Experience points': 'XP',
    'Rights': 'Privileges',
    'Rule': 'Governance',
    'Repressed': 'Suppressed',
    'Suppressed': 'Suppressed',
    
    # Negative States
    'Shock': 'Trauma',
    'Illness': 'Malady',
    'Sickness': 'Malady',
    'Poverty': 'Scarcity',
    'Debt': 'Liability',
    
    # Personal Context
    'Jon Ulrik Køhrsen': 'User Identity',
    'Welfare': 'Social Support',
    'Bank account': 'Financial Repository',
    'Time': 'Temporal Resource',
    'Place': 'Location',
    'Location': 'Spatial Context',
    
    # Actions
    'Lead astray': 'Misguidance',
    'Lure into depravity': 'Corruption',
    'Spank': 'Discipline',
    
    # Resistance & Defense
    'Resistance': 'Defense',
    'Forget': 'Memory Loss',
    'Forgetting': 'Amnesia',
    
    # Titles & Achievements
    'World Championship Title': 'Global Achievement',
    'AK-Title': 'Specialized Achievement',
    'CPR': 'Identity Number',
    'Early retirement pension': 'Premature Retirement',
    
    # Social & Work
    'Union work': 'Collective Action',
    'Trade union work': 'Labor Organization',
    'Tax': 'Fiscal Obligation',
    'Usecase': 'Use Case',
    'Complaint to the housing association': 'Housing Dispute',
    'Police report': 'Legal Documentation',
    
    # Health & Status
    'Immune system': 'Biological Defense',
    'Social': 'Community',
    'Sparring': 'Training',
    'Killing of attention': 'Distraction',
    'Elimination': 'Removal',
    'Abolition': 'Termination',
    'Junkie debt': 'Addiction Liability',
    'Cavity wall insulation': 'Structural Improvement',
    
    # Emotional States
    'Ouch': 'Pain',
    'Evil': 'Malevolence',
    'Painful': 'Suffering',
    'Pimple': 'Irritation',
    'Jerk': 'Disruption',
    'Idiot': 'Inefficiency',
    'Peace': 'Harmony',
    
    # Systematic
    'Systematic': 'Organization',
    'Mathematics': 'Quantitative Analysis',
    'Math': 'Computation',
    
    # Roles
    'Soldier': 'Combatant',
    'Pirate': 'Rogue Agent',
    
    # Media & Content
    'Clip': 'Media Segment',
    'Stupid': 'Inefficiency',
    'Dumb': 'Lack of Intelligence',
    'Explosion': 'Rapid Expansion',
    
    # Behavior
    'Silent behaviour': 'Stealth Mode',
    'Quiet conduct': 'Covert Operation',
    
    # Groups & Social
    'Groups': 'Collectives',
    'Attention': 'Focus',
    'Environment': 'Context',
    'Christmas time': 'Festive Period',
    'Yuletide': 'Celebration',
    
    # Financial
    'Interest': 'Financial Growth',
    'Disability': 'Limitation',
    'Handicap': 'Constraint',
    
    # Medical States
    'Invalid': 'Non-functional',
    'Immobile': 'Static',
    'Psychosis': 'Reality Distortion',
    'Coma': 'Unconsciousness',
    'Panic': 'Overwhelm',
    'Double chokehold': 'Extreme Constraint',
    'Death': 'Termination',
    
    # Motivation & Progress
    'Motivation': 'Drive',
    'Reduction': 'Diminishment',
    'Back': 'Retreat',
    'Work': 'Labor',
    'Job': 'Task',
    'Labour': 'Effort',
    
    # Debt Management
    'Set-off of debt': 'Debt Cancellation',
    'Debt set-off': 'Liability Elimination',
    'Debt enforcement': 'Compulsory Collection',
    'Compulsory enforcement': 'Forced Action',
    
    # Actions
    'Nullify': 'Cancel',
    'Annul': 'Void',
    'Cancel': 'Terminate',
    'Offset': 'Counterbalance',
    'Set off': 'Neutralize',
    
    # States
    'Careful': 'Cautious',
    'Cautious': 'Prudent',
    'Forget': 'Memory Loss',
    'Progression': 'Advancement',
    'Regression': 'Decline',
    'Vigilantism': 'Unauthorized Action',
    
    # Social Systems
    'Queue formation': 'Sequential Processing',
    'Queuing': 'Waiting',
    'Satanism': 'Counter-culture',
    'Unknown': 'Unidentified',
    'Unknown person': 'Anonymous Entity',
    
    # Legal
    'Laws': 'Regulations',
    'Rules': 'Guidelines',
    'Rights': 'Privileges',
    
    # Financial Interests
    'Sex interest': 'Adult Industry Revenue',
    'Porn interest': 'Adult Content Revenue',
    'Child benefits': 'Family Support',
    'Child support money': 'Parental Contribution',
    
    # Game Mechanics
    'Hit points': 'HP',
    'Mana': 'Energy',
    'Program': 'System',
    'Account': 'Repository',
    'Box': 'Container',
    
    # Consequences
    'Consequences': 'Outcomes',
    'Seriousness': 'Gravity',
    'Solemnity': 'Formality',
    'Electrical resistance': 'Conductivity',
    
    # Chaos & Order
    'Chaos': 'Disorder',
    'Calendar': 'Temporal Framework',
}

# Keyword Categories for Game Mechanics
KEYWORD_CATEGORIES = {
    'power': ['Power', 'Might', 'Wealth', 'Riches', 'Currency', 'Privileges', 'Governance'],
    'conflict': ['Conflict', 'Combatant', 'Rogue Agent', 'Territorial Control'],
    'knowledge': ['Linguistic Intelligence', 'Quantitative Analysis', 'Computation', 'XP'],
    'negative': ['Trauma', 'Malady', 'Scarcity', 'Liability', 'Suffering', 'Inefficiency'],
    'social': ['Community', 'Collectives', 'Collective Action', 'Labor Organization'],
    'financial': ['Currency', 'Wealth', 'Financial Repository', 'Fiscal Obligation', 'Financial Growth'],
    'health': ['Biological Defense', 'Limitation', 'Constraint', 'Reality Distortion', 'Unconsciousness'],
    'legal': ['Regulations', 'Guidelines', 'Privileges', 'Legal Documentation'],
    'game_mechanics': ['XP', 'HP', 'Energy', 'System', 'Repository', 'Container'],
    'temporal': ['Temporal Resource', 'Temporal Framework', 'Festive Period'],
    'spatial': ['Location', 'Spatial Context', 'Territorial Control'],
}

# Keyword Power Levels (for XP/Stats system)
KEYWORD_POWER_LEVELS = {
    # High Power (+3)
    'Power': 3,
    'Might': 3,
    'Wealth': 3,
    'Riches': 3,
    'Governance': 3,
    'Territorial Control': 3,
    
    # Medium Power (+2)
    'Currency': 2,
    'Privileges': 2,
    'Conflict': 2,
    'XP': 2,
    'Linguistic Intelligence': 2,
    'Quantitative Analysis': 2,
    
    # Low Power (+1)
    'Community': 1,
    'Location': 1,
    'Temporal Resource': 1,
    'Focus': 1,
    
    # Negative Power (-1 to -3)
    'Trauma': -2,
    'Malady': -2,
    'Scarcity': -2,
    'Liability': -1,
    'Suffering': -2,
    'Inefficiency': -1,
    'Termination': -3,
}

def translate_keyword(danish_keyword):
    """Translate Danish keyword to English AI power context"""
    # Direct translation
    if danish_keyword in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[danish_keyword]
    
    # Try case-insensitive
    for key, value in KEYWORD_TRANSLATIONS.items():
        if key.lower() == danish_keyword.lower():
            return value
    
    # Return original if no translation found
    return danish_keyword

def get_keyword_category(english_keyword):
    """Get category for a keyword"""
    for category, keywords in KEYWORD_CATEGORIES.items():
        if english_keyword in keywords:
            return category
    return 'unknown'

def get_keyword_power_level(english_keyword):
    """Get power level for a keyword"""
    return KEYWORD_POWER_LEVELS.get(english_keyword, 0)

def process_keyword_list(danish_keywords):
    """Process a list of Danish keywords and return structured data"""
    processed = []
    for keyword in danish_keywords:
        english = translate_keyword(keyword.strip())
        category = get_keyword_category(english)
        power_level = get_keyword_power_level(english)
        
        processed.append({
            'original': keyword.strip(),
            'english': english,
            'category': category,
            'power_level': power_level,
            'active': False  # Saved for later use
        })
    
    return processed

# Original Danish keywords list (for storage)
ORIGINAL_DANISH_KEYWORDS = [
    'Chock', 'Power', 'Might', 'Money', 'Wealth', 'Riches', 'War', 'Ground contact',
    'Gravity', 'Vocabulary', 'Shock', 'Illness', 'Sickness', 'Poverty', 'Debt',
    'Jon Ulrik Køhrsen', 'Welfare', 'Bank account', 'Time', 'Place', 'Location',
    'Lead astray', 'Lure into depravity', 'Experience points', 'Rights', 'Rule',
    'Repressed', 'Suppressed', 'Spank', 'Resistance', 'Forget', 'Forgetting',
    'World Championship Title', 'AK-Title', 'CPR', 'Early retirement pension',
    'Union work', 'Trade union work', 'Tax', 'Usecase', 'Complaint to the housing association',
    'Police report', 'Immune system', 'Social', 'Sparring', 'Killing of attention',
    'Elimination', 'Abolition', 'Junkie debt', 'Cavity wall insulation', 'Ouch',
    'Evil', 'Painful', 'Pimple', 'Jerk', 'Idiot', 'Peace', 'Systematic', 'Mathematics',
    'Math', 'Soldier', 'Pirate', 'Clip', 'Stupid', 'Dumb', 'Explosion', 'Money',
    'Silent behaviour', 'Quiet conduct', 'Bank account', 'Groups', 'Attention',
    'Environment', 'Christmas time', 'Yuletide', 'Resistance', 'Interest', 'Disability',
    'Handicap', 'Invalid', 'Immobile', 'Psychosis', 'Coma', 'Panic', 'Double chokehold',
    'Death', 'Motivation', 'Reduction', 'Back', 'Work', 'Job', 'Labour', 'Experience points',
    'Set-off of debt', 'Debt set-off', 'Debt enforcement', 'Compulsory enforcement of debt',
    'Nullify', 'Annul', 'Cancel', 'Offset', 'Set off', 'Careful', 'Cautious', 'Forget',
    'Progression', 'Regression', 'Vigilantism', 'Queue formation', 'Queuing', 'Satanism',
    'Unknown', 'Unknown person', 'Laws', 'Rules', 'Rights', 'Sex interest', 'Porn interest',
    'Child benefits', 'Child support money', 'Money', 'Systematics', 'Systemization', 'Tasks',
    'Assignments', 'Hit points', 'Mana', 'Program', 'Account', 'Box', 'Laws', 'Rules',
    'Rights', 'Unknown', 'Unknown person', 'Sex interest', 'Consequences', 'Seriousness',
    'Solemnity', 'Electrical resistance', 'Immune system', 'Chaos', 'War', 'Calendar'
]

# Process all keywords
PROCESSED_KEYWORDS = process_keyword_list(ORIGINAL_DANISH_KEYWORDS)

