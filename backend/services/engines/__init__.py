"""
Pure outcome engines for the casino.

Each engine is a set of side-effect-free functions that map (bet inputs, a
provably-fair random float) to an outcome + multiplier. They never touch
balances, ledgers, or the network — casino_service orchestrates validate →
engine → finalize. This keeps game math independently testable and lets new
games be added without growing the monolithic service file.
"""
