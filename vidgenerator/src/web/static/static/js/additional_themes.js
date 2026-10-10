/**
 * Additional Themes - Comprehensive Theme Collection
 * Gathered from popular sci-fi, fantasy, and game universes
 * All themes follow the Futuristic Theme Model Structure (Year 3025)
 */

const additionalThemes = {
    // Star Wars Universe
    starwars: {
        id: 'starwars',
        name: 'Star Wars',
        description: 'A galaxy far, far away',
        era: 'long-ago-future',
        category: 'sci-fi',
        colors: {
            primary: '#4a9eff',
            secondary: '#ffd700',
            accent: '#ff4444',
            background: 'linear-gradient(135deg, #000000 0%, #001122 30%, #003366 50%, #001122 70%, #000000 100%)',
            text: '#4a9eff',
            glow: '#4a9eff',
            shadow: '#001133'
        },
        keywords: ['star wars', 'force', 'jedi', 'sith', 'lightsaber', 'death star', 'rebellion', 'empire', 'yoda', 'luke', 'vader', 'leia', 'han solo', 'lightspeed', 'hyperspace'],
        quotes: [
            'May the Force be with you.',
            'I am your father.',
            'Do or do not, there is no try.',
            'The Force will be with you, always.',
            'Never tell me the odds.',
            'A long time ago in a galaxy far, far away...',
            'Use the Force, Luke.',
            'The Force is strong with this one.'
        ],
        characters: ['luke skywalker', 'darth vader', 'yoda', 'leia organa', 'han solo', 'obi-wan kenobi', 'darth maul', 'emperor palpatine', 'padme amidala', 'anakin skywalker', 'qui-gon jinn', 'mace windu', 'rey', 'kylo ren', 'finn', 'poe dameron', 'bb-8', 'c-3po', 'r2-d2', 'chewbacca'],
        visualElements: ['lightsaber glow', 'death star', 'millennium falcon', 'tie fighter', 'x-wing', 'star destroyer', 'force lightning', 'jedi temple', 'dagobah', 'tatooine', 'naboo', 'hoth', 'bespin', 'endor'],
        sounds: ['lightsaber ignition', 'lightsaber hum', 'blaster fire', 'tie fighter scream', 'wilhelm scream', 'force sound', 'vader breathing', 'r2-d2 beeps'],
        locations: ['tatooine', 'dagobah', 'naboo', 'hoth', 'bespin', 'endor', 'coruscant', 'mustafar', 'death star', 'jedi temple'],
        items: ['lightsaber', 'blaster', 'force', 'death star plans', 'holocron', 'sith holocron', 'kyber crystal'],
        concepts: ['the force', 'jedi', 'sith', 'rebellion', 'empire', 'galactic republic', 'clone wars'],
        effects: {
            particles: ['lightsaber particles', 'force particles', 'starfield'],
            animations: ['lightsaber swing', 'force push', 'hyperspace jump'],
            filters: ['blue/red lightsaber glow', 'starfield overlay'],
            overlays: ['star wars crawl', 'death star overlay']
        },
        quantum: { entanglement: true, superposition: false, tunneling: true },
        ai: { voice: 'jedi', personality: 'wise', responses: ['May the Force be with you.'] },
        holographic: { enabled: true, depth: 12, layers: 4, projections: ['lightsaber', 'death star', 'force'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Cyberpunk 2077
    cyberpunk: {
        id: 'cyberpunk',
        name: 'Cyberpunk 2077',
        description: 'High-tech, low-life future',
        era: '2077-futuristic',
        category: 'sci-fi',
        colors: {
            primary: '#ff00ff',
            secondary: '#00ffff',
            accent: '#ffff00',
            background: 'linear-gradient(135deg, #000000 0%, #1a0033 30%, #330066 50%, #1a0033 70%, #000000 100%)',
            text: '#ff00ff',
            glow: '#ff00ff',
            shadow: '#330033'
        },
        keywords: ['cyberpunk', 'neon', 'hacking', 'cyberware', 'netrunner', 'corpo', 'street kid', 'nomad', 'night city', 'araska', 'johnny silverhand', 'cyberdeck', 'quickhack'],
        quotes: [
            'Wake up, samurai. We have a city to burn.',
            'In Night City, you can become anyone.',
            'The city always wins.',
            'Never stop fighting.',
            'Cyberpsychosis detected.',
            'System breach.',
            'Access granted.'
        ],
        characters: ['v', 'johnny silverhand', 'jackie welles', 'panam palmer', 'judy alvarez', 'takemura', 'rogue', 'kerry eurodyne', 'river ward', 'evelyn parker'],
        visualElements: ['neon signs', 'holographic ads', 'cyberware implants', 'brain dance', 'netrunning', 'quickhack effects', 'neon rain', 'night city skyline', 'corpo towers', 'dark alley'],
        sounds: ['neon buzz', 'cyberpunk synth', 'quickhack sound', 'netrunner music', 'city ambience', 'corpo speech'],
        locations: ['night city', 'heywood', 'westbrook', 'watson', 'santo domingo', 'badlands', 'araska tower', 'afterlife'],
        items: ['cyberdeck', 'quickhack', 'cyberware', 'smart weapon', 'mantis blades', 'monowire', 'gorilla arms'],
        concepts: ['cyberware', 'netrunning', 'quickhack', 'corpo', 'street', 'cyberpsychosis', 'brain dance'],
        effects: {
            particles: ['neon particles', 'digital glitch', 'cyber particles'],
            animations: ['neon flicker', 'glitch effect', 'holographic overlay'],
            filters: ['neon glow', 'cyberpunk filter', 'neon rain'],
            overlays: ['hud overlay', 'quickhack interface', 'corpo overlay']
        },
        quantum: { entanglement: true, superposition: true, tunneling: true },
        ai: { voice: 'synthetic', personality: 'cyberpunk', responses: ['Wake up, samurai.'] },
        holographic: { enabled: true, depth: 15, layers: 5, projections: ['neon city', 'holographic ads'] },
        neural: { enabled: true, thoughtControl: true, brainSync: true },
        temporal: { timeDilation: true, timeTravel: false, parallel: true }
    },
    
    // Blade Runner
    bladerunner: {
        id: 'bladerunner',
        name: 'Blade Runner',
        description: 'Neo-noir dystopian future',
        era: '2019-futuristic',
        category: 'sci-fi',
        colors: {
            primary: '#ffaa00',
            secondary: '#ff6600',
            accent: '#ff0088',
            background: 'linear-gradient(135deg, #000000 0%, #330000 30%, #660000 50%, #330000 70%, #000000 100%)',
            text: '#ffaa00',
            glow: '#ff6600',
            shadow: '#330000'
        },
        keywords: ['blade runner', 'replicant', 'tyrell', 'spinner', 'neon', 'rain', 'detective', 'tyrell corporation', 'off-world', 'retirement'],
        quotes: [
            'I\'ve seen things you people wouldn\'t believe.',
            'Time to die.',
            'All those moments will be lost in time, like tears in rain.',
            'More human than human.',
            'Wake up, time to die.',
            'The light that burns twice as bright burns half as long.'
        ],
        characters: ['rick deckard', 'roy batty', 'rachael', 'pris', 'zhora', 'leon', 'tyrell', 'gaff', 'bryant'],
        visualElements: ['rainy neon streets', 'spinner car', 'tyrell pyramid', 'holographic billboards', 'neon signs', 'smog', 'fog', 'dark alleys', 'apartment buildings'],
        sounds: ['vangelis soundtrack', 'rain', 'spinner engine', 'city ambience', 'blade runner theme'],
        locations: ['los angeles 2019', 'tyrell corporation', 'sewers', 'apartment', 'rooftops'],
        items: ['blaster', 'spinner', 'voight-kampff', 'photographs', 'replicant'],
        concepts: ['replicant', 'tyrell corporation', 'off-world', 'retirement', 'memory', 'empathy'],
        effects: {
            particles: ['rain particles', 'smog particles', 'neon glow'],
            animations: ['rain fall', 'neon flicker', 'spinner fly'],
            filters: ['noir filter', 'neon glow', 'rain overlay'],
            overlays: ['rain overlay', 'neon overlay', 'noir overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'noir', personality: 'detective', responses: ['I\'ve seen things you people wouldn\'t believe.'] },
        holographic: { enabled: true, depth: 8, layers: 3, projections: ['neon city', 'holographic billboards'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Mass Effect
    masseffect: {
        id: 'masseffect',
        name: 'Mass Effect',
        description: 'Galactic civilization and reapers',
        era: '2183-futuristic',
        category: 'sci-fi',
        colors: {
            primary: '#00aaff',
            secondary: '#0066ff',
            accent: '#ffaa00',
            background: 'linear-gradient(135deg, #000011 0%, #001133 30%, #003366 50%, #001133 70%, #000011 100%)',
            text: '#00aaff',
            glow: '#0066ff',
            shadow: '#001133'
        },
        keywords: ['mass effect', 'reaper', 'shepard', 'normandy', 'citadel', 'alliance', 'cerberus', 'biotics', 'omni-tool', 'mass relay'],
        quotes: [
            'I should go.',
            'We\'ll bang, okay?',
            'Stand amongst the ashes of a trillion dead souls.',
            'I\'m Commander Shepard, and this is my favorite store on the Citadel.',
            'Does this unit have a soul?',
            'I am the vanguard of your destruction.'
        ],
        characters: ['commander shepard', 'garrus vakarian', 'tali zorah', 'liara tsoni', 'wrex', 'ashley williams', 'kaiden alenko', 'joker', 'edi', 'legion', 'thane', 'mordin', 'jack', 'miranda', 'james vega'],
        visualElements: ['normandy sr2', 'citadel', 'mass relay', 'reaper', 'omni-tool', 'biotic effects', 'galactic map', 'planet scan', 'combat hud'],
        sounds: ['mass effect theme', 'reaper horn', 'normandy ambience', 'biotic sound', 'omni-tool beep', 'citadel ambience'],
        locations: ['normandy', 'citadel', 'earth', 'mars', 'illium', 'tuchanka', 'rannoch', 'thessia'],
        items: ['omni-tool', 'mass effect weapon', 'medi-gel', 'element zero', 'prothean beacon'],
        concepts: ['mass effect', 'reapers', 'biotics', 'galactic civilization', 'spectre', 'citadel'],
        effects: {
            particles: ['biotic particles', 'mass effect particles', 'reaper particles'],
            animations: ['biotic charge', 'mass relay jump', 'reaper arrival'],
            filters: ['blue energy glow', 'citadel overlay'],
            overlays: ['combat hud', 'galactic map', 'omni-tool interface']
        },
        quantum: { entanglement: true, superposition: false, tunneling: true },
        ai: { voice: 'synthetic', personality: 'commander', responses: ['I should go.'] },
        holographic: { enabled: true, depth: 10, layers: 3, projections: ['citadel', 'normandy'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Fallout
    fallout: {
        id: 'fallout',
        name: 'Fallout',
        description: 'Post-apocalyptic wasteland',
        era: 'post-apocalyptic',
        category: 'game',
        colors: {
            primary: '#00ff00',
            secondary: '#ffff00',
            accent: '#ff6600',
            background: 'linear-gradient(135deg, #663300 0%, #996600 30%, #cc9900 50%, #996600 70%, #663300 100%)',
            text: '#00ff00',
            glow: '#ffff00',
            shadow: '#330000'
        },
        keywords: ['fallout', 'vault', 'pip-boy', 'nuka-cola', 'caps', 'raider', 'super mutant', 'deathclaw', 'vault dweller', 'wasteland'],
        quotes: [
            'War... War never changes.',
            'Another settlement needs your help.',
            'Please assume the position.',
            'Would you like to know more?',
            'You\'re a little bitch and your brother was, too.',
            'Patrolling the Mojave almost makes you wish for a nuclear winter.'
        ],
        characters: ['vault dweller', 'sole survivor', 'courier', 'nicky', 'piper', 'cait', 'curie', 'codsworth', 'dogmeat', 'preston garvey'],
        visualElements: ['pip-boy', 'vault door', 'nuka-cola', 'radiation symbol', 'wasteland', 'super mutant', 'deathclaw', 'power armor', 'laser rifle'],
        sounds: ['fallout theme', 'pip-boy beep', 'radio static', 'vault door', 'explosion', 'power armor'],
        locations: ['vault', 'wasteland', 'diamond city', 'sanctuary', 'goodneighbor', 'the commonwealth'],
        items: ['pip-boy', 'nuka-cola', 'caps', 'stimpak', 'radaway', 'power armor', 'laser rifle', 'fat man'],
        concepts: ['vault', 'radiation', 'wasteland', 'nuclear war', 'vault-tec', 'brotherhood of steel'],
        effects: {
            particles: ['radiation particles', 'dust particles', 'explosion particles'],
            animations: ['pip-boy interface', 'vault door opening', 'explosion'],
            filters: ['sepia filter', 'radiation glow', 'wasteland overlay'],
            overlays: ['pip-boy overlay', 'radiation overlay', 'vault-tec overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'retro', personality: 'survivor', responses: ['War... War never changes.'] },
        holographic: { enabled: false, depth: 0, layers: 0, projections: [] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // The Elder Scrolls
    elder scrolls: {
        id: 'elderscrolls',
        name: 'The Elder Scrolls',
        description: 'Fantasy realm of Tamriel',
        era: 'medieval-fantasy',
        category: 'game',
        colors: {
            primary: '#d4af37',
            secondary: '#b8860b',
            accent: '#ffd700',
            background: 'linear-gradient(135deg, #1a0f00 0%, #4a2c00 30%, #6b3f00 50%, #4a2c00 70%, #1a0f00 100%)',
            text: '#d4af37',
            glow: '#ffd700',
            shadow: '#2a1f00'
        },
        keywords: ['elder scrolls', 'skyrim', 'tamriel', 'dragonborn', 'thu\'um', 'shout', 'nord', 'imperial', 'dark elf', 'dragon', 'talos', 'daedra'],
        quotes: [
            'Fus Ro Dah!',
            'I used to be an adventurer like you, then I took an arrow in the knee.',
            'Never should have come here!',
            'Sky above, voice within.',
            'Do you get to the Cloud District very often?',
            'The Dragonborn comes.'
        ],
        characters: ['dragonborn', 'paarthurnax', 'alduin', 'ulfric stormcloak', 'tullius', 'lydia', 'serana', 'delphine', 'esbern'],
        visualElements: ['elder scroll', 'thu\'um shout', 'dragon', 'soul gem', 'skyrim map', 'word wall', 'dragonsreach', 'high hrothgar'],
        sounds: ['skyrim theme', 'dragon roar', 'thu\'um shout', 'arrow hit', 'sword clash', 'magic cast'],
        locations: ['skyrim', 'whiterun', 'riverwood', 'high hrothgar', 'solitude', 'windhelm', 'markarth', 'rift'],
        items: ['elder scroll', 'dragon soul', 'word wall', 'soul gem', 'daedric artifact', 'shout', 'arrow'],
        concepts: ['dragonborn', 'thu\'um', 'dragons', 'talos', 'daedra', 'aedra', 'nordic'],
        effects: {
            particles: ['magic particles', 'dragon fire', 'soul particles'],
            animations: ['thu\'um shout', 'dragon flight', 'magic cast'],
            filters: ['fantasy filter', 'nordic overlay'],
            overlays: ['word wall overlay', 'dragon overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'nordic', personality: 'warrior', responses: ['Fus Ro Dah!'] },
        holographic: { enabled: false, depth: 0, layers: 0, projections: [] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Assassin's Creed
    assassinscreed: {
        id: 'assassinscreed',
        name: 'Assassin\'s Creed',
        description: 'Hidden blades and ancient conspiracies',
        era: 'historical-modern',
        category: 'game',
        colors: {
            primary: '#ff0000',
            secondary: '#ffffff',
            accent: '#ffaa00',
            background: 'linear-gradient(135deg, #000000 0%, #330000 30%, #660000 50%, #330000 70%, #000000 100%)',
            text: '#ff0000',
            glow: '#ff0000',
            shadow: '#330000'
        },
        keywords: ['assassins creed', 'assassin', 'templar', 'animus', 'hidden blade', 'leap of faith', 'ezio', 'altair', 'edward', 'connor'],
        quotes: [
            'Nothing is true, everything is permitted.',
            'Requiescat in pace.',
            'The Creed is a warning.',
            'May the Father of Understanding guide us.',
            'The Assassins have returned.',
            'It is a good life we lead, brother.'
        ],
        characters: ['altair', 'ezio auditore', 'connor kenway', 'edward kenway', 'desmond miles', 'alexios', 'kassandra', 'bayek'],
        visualElements: ['hidden blade', 'animus', 'leap of faith', 'assassin robes', 'templar cross', 'eagle vision', 'parkour', 'ancient ruins'],
        sounds: ['assassins creed theme', 'hidden blade', 'eagle cry', 'parkour', 'combat'],
        locations: ['jerusalem', 'constantinople', 'rome', 'florence', 'venice', 'boston', 'caribbean', 'egypt', 'greece'],
        items: ['hidden blade', 'assassin robes', 'eagle vision', 'apple of eden', 'animus'],
        concepts: ['assassins', 'templars', 'animus', 'first civilization', 'pieces of eden'],
        effects: {
            particles: ['eagle feathers', 'blood particles'],
            animations: ['leap of faith', 'parkour', 'hidden blade'],
            filters: ['eagle vision filter', 'animus overlay'],
            overlays: ['animus interface', 'eagle vision overlay']
        },
        quantum: { entanglement: false, superposition: true, tunneling: true },
        ai: { voice: 'assassin', personality: 'stealthy', responses: ['Nothing is true, everything is permitted.'] },
        holographic: { enabled: true, depth: 5, layers: 2, projections: ['animus', 'eagle vision'] },
        neural: { enabled: true, thoughtControl: true, brainSync: true },
        temporal: { timeDilation: false, timeTravel: true, parallel: false }
    },
    
    // Borderlands
    borderlands: {
        id: 'borderlands',
        name: 'Borderlands',
        description: 'Cell-shaded wasteland mayhem',
        era: 'futuristic-cartoon',
        category: 'game',
        colors: {
            primary: '#ffaa00',
            secondary: '#ff6600',
            accent: '#ff00ff',
            background: 'linear-gradient(135deg, #000000 0%, #330000 30%, #660000 50%, #330000 70%, #000000 100%)',
            text: '#ffaa00',
            glow: '#ff6600',
            shadow: '#330000'
        },
        keywords: ['borderlands', 'vault hunter', 'pandora', 'handsome jack', 'claptrap', 'bandit', 'hyperion', 'maliwan', 'jakobs', 'slag', 'iridium'],
        quotes: [
            'Butt stallion says hello.',
            'EXPLOSIONS!',
            'This is where the cars live. Get you one!',
            'CATCH A RIDE!',
            'I\'m gonna shoot you in the face!',
            'They called me a madman.'
        ],
        characters: ['handsome jack', 'claptrap', 'lilith', 'mordecai', 'brick', 'maya', 'zero', 'axton', 'salvador', 'gaige', 'krieg'],
        visualElements: ['cell-shaded style', 'comic book overlay', 'wasteland', 'vault symbol', 'weapon loot', 'badass rank', 'vault hunters'],
        sounds: ['borderlands theme', 'explosions', 'claptrap voice', 'weapon fire', 'loot drop'],
        locations: ['pandora', 'sanctuary', 'dahl headlands', 'eros', 'opportunity', 'the dust'],
        items: ['vault key', 'eridium', 'slag', 'legendary weapon', 'shield', 'grenade'],
        concepts: ['vault', 'vault hunters', 'eridian', 'slag', 'iridium', 'badass rank'],
        effects: {
            particles: ['cell-shaded particles', 'explosion particles'],
            animations: ['cell-shaded style', 'comic book effects'],
            filters: ['cell-shaded filter', 'comic book overlay'],
            overlays: ['comic book overlay', 'hud overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'cartoon', personality: 'wacky', responses: ['EXPLOSIONS!'] },
        holographic: { enabled: false, depth: 0, layers: 0, projections: [] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // The Witcher
    witcher: {
        id: 'witcher',
        name: 'The Witcher',
        description: 'Medieval fantasy monster hunting',
        era: 'medieval-fantasy',
        category: 'game',
        colors: {
            primary: '#ff6600',
            secondary: '#cc4400',
            accent: '#ffaa00',
            background: 'linear-gradient(135deg, #1a0f00 0%, #330000 30%, #660000 50%, #330000 70%, #1a0f00 100%)',
            text: '#ff6600',
            glow: '#ffaa00',
            shadow: '#330000'
        },
        keywords: ['witcher', 'geralt', 'ciri', 'yennefer', 'triss', 'monster', 'contract', 'sign', 'sword', 'silver sword', 'potions', 'mutations'],
        quotes: [
            'Wind\'s howling.',
            'How do you like that silver?',
            'Hmm.',
            'Place of power, gotta be.',
            'Damn, you\'re ugly!',
            'Evil is evil.'
        ],
        characters: ['geralt of rivia', 'ciri', 'yennefer', 'triss merigold', 'dandelion', 'vesemir', 'lambert', 'eskel', 'avallach'],
        visualElements: ['silver sword', 'steel sword', 'witcher signs', 'medallion', 'potions', 'monster', 'contract', 'kaer morhen'],
        sounds: ['witcher theme', 'sword clash', 'monster roar', 'sign cast', 'horse gallop'],
        locations: ['kaer morhen', 'novigrad', 'velen', 'skellige', 'toussaint', 'oxenfurt'],
        items: ['silver sword', 'steel sword', 'witcher signs', 'medallion', 'potions', 'mutagens'],
        concepts: ['witchers', 'monsters', 'mutations', 'signs', 'contracts', 'elder blood'],
        effects: {
            particles: ['sign particles', 'magic particles'],
            animations: ['sign cast', 'sword swing', 'monster fight'],
            filters: ['fantasy filter', 'medieval overlay'],
            overlays: ['witcher hud', 'sign overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'gritty', personality: 'hunter', responses: ['Hmm.'] },
        holographic: { enabled: false, depth: 0, layers: 0, projections: [] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Deus Ex
    deusex: {
        id: 'deusex',
        name: 'Deus Ex',
        description: 'Cyberpunk conspiracy and augmentation',
        era: 'futuristic',
        category: 'sci-fi',
        colors: {
            primary: '#00ffaa',
            secondary: '#00cc88',
            accent: '#ffaa00',
            background: 'linear-gradient(135deg, #000000 0%, #001100 30%, #003300 50%, #001100 70%, #000000 100%)',
            text: '#00ffaa',
            glow: '#00cc88',
            shadow: '#001100'
        },
        keywords: ['deus ex', 'augmentation', 'jensen', 'human revolution', 'illuminati', 'majestic 12', 'sarif industries', 'tycho', 'adam jensen'],
        quotes: [
            'I never asked for this.',
            'What a shame.',
            'A bomb!',
            'I\'m just following orders.',
            'Augmentation is the future.',
            'We\'re all puppets.'
        ],
        characters: ['adam jensen', 'megan reed', 'david sarif', 'prichard', 'faridah malik', 'eliza cassan'],
        visualElements: ['augmentation hud', 'cyberware', 'neon city', 'tycho panel', 'augmentation effects', 'conspiracy'],
        sounds: ['deus ex theme', 'augmentation sound', 'hud beep', 'city ambience'],
        locations: ['detroit', 'hengsha', 'panchaea', 'tycho', 'sarif industries'],
        items: ['augmentation', 'tycho', 'pocket secretary', 'augmentation parts'],
        concepts: ['augmentation', 'human revolution', 'illuminati', 'conspiracy', 'tycho'],
        effects: {
            particles: ['augmentation particles', 'cyber particles'],
            animations: ['augmentation effects', 'hud overlay'],
            filters: ['augmentation filter', 'cyberpunk overlay'],
            overlays: ['augmentation hud', 'tycho overlay']
        },
        quantum: { entanglement: true, superposition: false, tunneling: true },
        ai: { voice: 'synthetic', personality: 'augmented', responses: ['I never asked for this.'] },
        holographic: { enabled: true, depth: 8, layers: 3, projections: ['augmentation hud', 'tycho'] },
        neural: { enabled: true, thoughtControl: true, brainSync: true },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Final Fantasy
    finalfantasy: {
        id: 'finalfantasy',
        name: 'Final Fantasy',
        description: 'Epic fantasy JRPG',
        era: 'fantasy-futuristic',
        category: 'game',
        colors: {
            primary: '#00aaff',
            secondary: '#ffaa00',
            accent: '#ff0088',
            background: 'linear-gradient(135deg, #000011 0%, #001133 30%, #003366 50%, #001133 70%, #000011 100%)',
            text: '#00aaff',
            glow: '#ffaa00',
            shadow: '#001133'
        },
        keywords: ['final fantasy', 'chocobo', 'moguri', 'crystals', 'summon', 'magic', 'limit break', 'airship', 'cid'],
        quotes: [
            'Victory fanfare!',
            'Kweh!',
            'Let\'s mosey.',
            'This guy are sick.',
            'It\'s showtime!',
            'You spoony bard!'
        ],
        characters: ['cloud strife', 'sephiroth', 'aerith', 'tifa', 'squall', 'zidane', 'tidus', 'lightning', 'noctis', 'clive'],
        visualElements: ['chocobo', 'moguri', 'summon', 'crystals', 'airship', 'magic spell', 'limit break', 'victory pose'],
        sounds: ['final fantasy theme', 'victory fanfare', 'chocobo kweh', 'summon sound', 'battle music'],
        locations: ['midgar', 'spira', 'the world of balance', 'eorzea', 'hyrule'],
        items: ['chocobo', 'moguri', 'crystals', 'summon materia', 'limit break', 'potions'],
        concepts: ['crystals', 'summons', 'magic', 'chocobo', 'moguri', 'final fantasy'],
        effects: {
            particles: ['magic particles', 'crystal particles', 'summon particles'],
            animations: ['summon animation', 'magic cast', 'limit break'],
            filters: ['fantasy filter', 'crystal glow'],
            overlays: ['battle hud', 'victory overlay']
        },
        quantum: { entanglement: false, superposition: false, tunneling: true },
        ai: { voice: 'japanese', personality: 'heroic', responses: ['Victory fanfare!'] },
        holographic: { enabled: true, depth: 10, layers: 4, projections: ['summon', 'crystals'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: false, parallel: false }
    },
    
    // Portal
    portal: {
        id: 'portal',
        name: 'Portal',
        description: 'Puzzle-solving with portal gun',
        era: 'futuristic',
        category: 'game',
        colors: {
            primary: '#ff0088',
            secondary: '#00ffff',
            accent: '#ffffff',
            background: 'linear-gradient(135deg, #000000 0%, #330033 30%, #660066 50%, #330033 70%, #000000 100%)',
            text: '#ff0088',
            glow: '#00ffff',
            shadow: '#330033'
        },
        keywords: ['portal', 'glados', 'chell', 'aperture science', 'portal gun', 'companion cube', 'test chamber', 'cake'],
        quotes: [
            'The cake is a lie.',
            'This was a triumph.',
            'Now you\'re thinking with portals!',
            'I\'m still alive!',
            'The Enrichment Center is committed to the well-being of all participants.',
            'Speedy thing goes in, speedy thing comes out.'
        ],
        characters: ['chell', 'glados', 'wheatley', 'turret', 'cave johnson'],
        visualElements: ['portal gun', 'blue portal', 'orange portal', 'companion cube', 'test chamber', 'aperture science logo', 'turret'],
        sounds: ['portal theme', 'portal sound', 'glados voice', 'turret voice', 'test chamber'],
        locations: ['aperture science', 'test chambers', 'old aperture', 'enrichment center'],
        items: ['portal gun', 'companion cube', 'portal', 'aperture science'],
        concepts: ['portal', 'aperture science', 'test chambers', 'glados', 'cake'],
        effects: {
            particles: ['portal particles', 'energy particles'],
            animations: ['portal opening', 'portal jump', 'companion cube'],
            filters: ['portal filter', 'test chamber overlay'],
            overlays: ['portal overlay', 'aperture overlay']
        },
        quantum: { entanglement: true, superposition: true, tunneling: true },
        ai: { voice: 'synthetic', personality: 'sarcastic', responses: ['The cake is a lie.'] },
        holographic: { enabled: true, depth: 12, layers: 4, projections: ['portal', 'companion cube'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: true, timeTravel: false, parallel: true }
    },
    
    // Half-Life
    halflife: {
        id: 'halflife',
        name: 'Half-Life',
        description: 'Black Mesa incident and combine',
        era: 'futuristic',
        category: 'sci-fi',
        colors: {
            primary: '#ffaa00',
            secondary: '#ff6600',
            accent: '#ffff00',
            background: 'linear-gradient(135deg, #000000 0%, #330000 30%, #660000 50%, #330000 70%, #000000 100%)',
            text: '#ffaa00',
            glow: '#ff6600',
            shadow: '#330000'
        },
        keywords: ['half-life', 'gordon freeman', 'black mesa', 'combine', 'g-man', 'lambda', 'headcrab', 'crowbar', 'hev suit'],
        quotes: [
            'Rise and shine, Mr. Freeman.',
            'Wake up and smell the ashes.',
            'The right man in the wrong place.',
            'Unforseen consequences.',
            'Prepare for unforseen consequences.'
        ],
        characters: ['gordon freeman', 'alyx vance', 'eli vance', 'barney calhoun', 'g-man', 'dr. kleiner'],
        visualElements: ['crowbar', 'hev suit', 'gravity gun', 'lambda symbol', 'black mesa', 'combine', 'headcrab', 'vortigaunt'],
        sounds: ['half-life theme', 'crowbar hit', 'gravity gun', 'headcrab sound', 'g-man voice'],
        locations: ['black mesa', 'city 17', 'ravenholm', 'nova prospect'],
        items: ['crowbar', 'hev suit', 'gravity gun', 'lambda', 'headcrab'],
        concepts: ['black mesa', 'combine', 'resonance cascade', 'xen', 'vortigaunt'],
        effects: {
            particles: ['energy particles', 'explosion particles'],
            animations: ['gravity gun', 'portal effect'],
            filters: ['sci-fi filter', 'combine overlay'],
            overlays: ['hev suit hud', 'lambda overlay']
        },
        quantum: { entanglement: true, superposition: false, tunneling: true },
        ai: { voice: 'synthetic', personality: 'mysterious', responses: ['Rise and shine, Mr. Freeman.'] },
        holographic: { enabled: true, depth: 8, layers: 3, projections: ['combine', 'lambda'] },
        neural: { enabled: false, thoughtControl: false, brainSync: false },
        temporal: { timeDilation: false, timeTravel: true, parallel: false }
    }
};

// Export for use in main.js
if (typeof window !== 'undefined') {
    window.additionalThemes = additionalThemes;
}

