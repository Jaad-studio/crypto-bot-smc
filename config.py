"""
Configuration du Bot de Day Trading Quantitatif (Smart Money Concepts)
Conçu pour micro-capital (300 €) évolutif vers 3 000 €+.
"""

import os

# --- CAPITAL & GESTION DU RISQUE DÉTERMINISTE ---
INITIAL_CAPITAL = 300.0  # Capital de départ en EUR / USDT

# Mode de risque : 'kelly' (Quarter-Kelly statistique recommandé), 'percentage', ou 'fixed'
RISK_MODE = 'kelly'
KELLY_FRACTION = 0.25    # 0.25 = 1/4 Kelly (plafond anti-ruine)
RISK_PERCENT = 5.0       # Fallback si RISK_MODE == 'percentage'
FIXED_RISK_AMOUNT = 15.0 # Fallback si RISK_MODE == 'fixed'

# Garde-fous déterministes (Hard Risk Layer)
MAX_DRAWDOWN_LIMIT_PCT = 15.0  # Kill-Switch strict : coupure si -15% depuis sommet
MAX_DAILY_LOSS_LIMIT_PCT = 5.0 # Perte journalière maximale autorisée

# Filtrage chirurgical des signaux
MIN_SETUP_QUALITY = 2.0  # Score minimum de configuration (sur 3.0)
MIN_CONFIDENCE = 0.80    # Probabilité calibrée minimale (80%)

# Ratios de Prise de Profit (Risk / Reward)
TP1_RR = 1.5   # Take Profit 1 à 1.5x le risque (on vend 50% et on passe le SL à Breakeven)
TP2_RR = 3.0   # Take Profit 2 final à 3.0x le risque (on laisse courir les 50% restants)
ATR_SL_MULTIPLIER = 1.5 # Distance Stop Loss = 1.5 x ATR(14) 15m

# --- ACTIFS ET TIMEFRAMES ---
PAIRS = [
    'BTC/USDT',    # Boussole macro et valeur sûre
    'SOL/USDT',    # Ultra-liquide
    'AVAX/USDT',   # Très propre sur les FVG
    'INJ/USDT',    # Volatilité asymétrique forte
    'SUI/USDT',    # Momentum très puissant
    'NEAR/USDT',   # Fortes amplitudes intraday
    'APT/USDT',    # Mouvements vifs
    'TAO/USDT',    # Secteur AI à forte volatilité
    'FET/USDT',    # Secteur AI très réactif
    'RENDER/USDT', # Secteur AI & GPU Computing
    'SEI/USDT',    # Layer 1 ultra-rapide haute fréquence
    'TIA/USDT',    # Modular blockchain forte volatilité
    'ARB/USDT',    # Layer 2 Ethereum leader
    'OP/USDT',     # Layer 2 Optimism
    'AAVE/USDT',   # DeFi institutionnelle
    'PENDLE/USDT', # DeFi Yield trading explosif
    'WIF/USDT',    # Memecoin Solana très volatil
    'PEPE/USDT',   # Memecoin ultra-spéculatif
    'BONK/USDT',   # Memecoin Solana à grosses variations
    'FLOKI/USDT',  # Memecoin à fort momentum
    'DOGE/USDT',   # Gros volumes et mèches rapides
    'LINK/USDT'    # Oracles institutionnels dynamiques
]

TIMEFRAME_MACRO = '1h'  # Tendance institutionnelle macro (Market Structure)
TIMEFRAME_MICRO = '15m' # Détection des anomalies de liquidité (FVG, Order Blocks)

# --- FILTRE PARAPLUIE BITCOIN (BTC UMBRELLA) ---
BTC_DUMP_THRESHOLD_1H = -1.8 # Si BTC chute de plus de -1.8% en 1H, gel de tous les signaux Long

# --- EXCHANGE & EXÉCUTION ---
EXCHANGE_ID = 'binance' # Options : 'binance', 'bybit', 'bitget', 'kucoin'
EXCHANGE_TYPE = 'spot'  # 'spot' (Binance Spot sans levier, 100% conforme France)
ALLOW_SHORT = False     # 100% Achats (LONG) uniquement, 0 Short
DEFAULT_LEVERAGE = 1    # Spot classique (aucun effet de levier)

# Clés API Exchange (Optionnel si mode ALERTE DISCORD / DRY RUN uniquement)
API_KEY = os.getenv('EXCHANGE_API_KEY', '')
API_SECRET = os.getenv('EXCHANGE_API_SECRET', '')

# --- WEBHOOK DISCORD ---
# Collez ici votre URL de Webhook Discord (créée dans les paramètres de votre salon Discord)
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1560292303720022136/359CVKsV7cHUEUjW7ds-2uoU-ecbCt0eXVdfurlD2wkLmC3dQ6xtHSRj-2orgmXFoXoQ')

# Mode de fonctionnement : 'paper' (simulation en direct) ou 'alert_only'
BOT_MODE = 'paper' 
SCAN_INTERVAL_SECONDS = 60 # Vérification des marchés toutes les 60 secondes
