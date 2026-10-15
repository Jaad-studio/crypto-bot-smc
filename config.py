"""
Configuration du Bot de Day Trading Quantitatif (Smart Money Concepts)
Conçu pour micro-capital (300 €) évolutif vers 3 000 €+.
"""

import os

# --- CAPITAL & GESTION DU RISQUE ---
INITIAL_CAPITAL = 300.0  # Capital de départ en EUR / USDT

# Mode de risque configurable :
# 'percentage' (ex: 5.0 pour 5%) ou 'fixed' (ex: 15.0 pour 15 €)
RISK_MODE = 'percentage'
RISK_PERCENT = 5.0       # 5% de 300 € = 15 € risqué par trade (plus réaliste et agressif pour faire grossir un petit compte)
FIXED_RISK_AMOUNT = 15.0 # Utilisé si RISK_MODE == 'fixed'

# Ratios de Prise de Profit (Risk / Reward)
TP1_RR = 1.5   # Take Profit 1 à 1.5x le risque (on vend 50% et on passe le SL à Breakeven)
TP2_RR = 3.0   # Take Profit 2 final à 3.0x le risque (on laisse courir les 50% restants)
ATR_SL_MULTIPLIER = 1.5 # Distance Stop Loss = 1.5 x ATR(14) 15m

# --- ACTIFS ET TIMEFRAMES ---
PAIRS = [
    'SOL/USDT',
    'AVAX/USDT',
    'INJ/USDT',
    'BTC/USDT'
]

TIMEFRAME_MACRO = '1h'  # Tendance institutionnelle macro (Market Structure)
TIMEFRAME_MICRO = '15m' # Détection des anomalies de liquidité (FVG, Order Blocks)

# --- FILTRE PARAPLUIE BITCOIN (BTC UMBRELLA) ---
BTC_DUMP_THRESHOLD_1H = -1.8 # Si BTC chute de plus de -1.8% en 1H, gel de tous les signaux Long

# --- EXCHANGE & EXÉCUTION ---
EXCHANGE_ID = 'binance' # Options : 'binance', 'bybit', 'bitget', 'kucoin'
EXCHANGE_TYPE = 'swap'  # 'swap' (Futures / Contrats Perpétuels avec levier) ou 'spot'
DEFAULT_LEVERAGE = 3    # Levier conservateur recommandé pour micro-capital (x2 à x5 max)

# Clés API Exchange (Optionnel si mode ALERTE DISCORD / DRY RUN uniquement)
API_KEY = os.getenv('EXCHANGE_API_KEY', '')
API_SECRET = os.getenv('EXCHANGE_API_SECRET', '')

# --- WEBHOOK DISCORD ---
# Collez ici votre URL de Webhook Discord (créée dans les paramètres de votre salon Discord)
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1560292303720022136/359CVKsV7cHUEUjW7ds-2uoU-ecbCt0eXVdfurlD2wkLmC3dQ6xtHSRj-2orgmXFoXoQ')

# Mode de fonctionnement : 'paper' (simulation en direct) ou 'alert_only'
BOT_MODE = 'paper' 
SCAN_INTERVAL_SECONDS = 60 # Vérification des marchés toutes les 60 secondes
