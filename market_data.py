"""
Module de Récupération des Données de Marché via CCXT.
Accède aux flux publics sans clé API requise pour l'analyse.
"""

import ccxt
import pandas as pd
import numpy as np
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class MarketDataProvider:
    def __init__(self, exchange_id='binance', exchange_type='swap'):
        self.exchange_id = exchange_id
        self.exchange_type = exchange_type
        
        exchange_class = getattr(ccxt, exchange_id)
        params = {
            'enableRateLimit': True,
            'timeout': 15000,
        }
        if exchange_type == 'swap':
            params['options'] = {'defaultType': 'swap'}
            
        self.exchange = exchange_class(params)
        logging.info(f"Exchange initialisé : {exchange_id.upper()} ({exchange_type})")

    def fetch_ohlcv(self, symbol, timeframe='15m', limit=150):
        """
        Récupère les bougies OHLCV historiques et calcule les indicateurs de base (ATR, Volume Delta).
        """
        try:
            raw_candles = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            min_needed = min(15, limit)
            if not raw_candles or len(raw_candles) < min_needed:
                logging.warning(f"Données insuffisantes reçues pour {symbol} en {timeframe}")
                return None
            
            df = pd.DataFrame(raw_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calcul de l'ATR (Average True Range) sur 14 périodes
            df['high_low'] = df['high'] - df['low']
            df['high_close_prev'] = (df['high'] - df['close'].shift(1)).abs()
            df['low_close_prev'] = (df['low'] - df['close'].shift(1)).abs()
            df['tr'] = df[['high_low', 'high_close_prev', 'low_close_prev']].max(axis=1)
            df['atr'] = df['tr'].rolling(window=14).mean()
            
            # Estimation du Volume Delta (CVD) sur les bougies :
            # Approximation institutionnelle : répartition du volume selon la position de clôture dans le range
            range_span = df['high'] - df['low']
            # Évite division par zéro
            range_span = range_span.replace(0, np.nan).fillna(0.00001)
            
            # Ratio d'agressivité acheteuse : (Close - Low) / (High - Low)
            buy_ratio = (df['close'] - df['low']) / range_span
            df['buy_vol'] = df['volume'] * buy_ratio
            df['sell_vol'] = df['volume'] * (1 - buy_ratio)
            df['delta'] = df['buy_vol'] - df['sell_vol']
            df['cvd'] = df['delta'].cumsum()
            
            return df
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des bougies pour {symbol} ({timeframe}): {e}")
            return None

    def get_btc_macro_status(self, symbol='BTC/USDT'):
        """
        Calcule la performance du Bitcoin sur la dernière heure pour le filtre Parapluie.
        """
        df_1h = self.fetch_ohlcv(symbol, timeframe='1h', limit=20)
        if df_1h is None or len(df_1h) < 2:
            return 0.0, 0.0
        
        last_candle = df_1h.iloc[-1]
        prev_candle = df_1h.iloc[-2]
        change_pct = ((last_candle['close'] - prev_candle['close']) / prev_candle['close']) * 100.0
        
        return change_pct, last_candle['close']

    def get_current_price(self, symbol):
        """Récupère le prix actuel en temps réel."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logging.error(f"Erreur fetch_ticker pour {symbol}: {e}")
            return None
