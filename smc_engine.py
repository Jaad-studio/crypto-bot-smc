"""
Moteur d'Analyse Institutionnelle Smart Money Concepts (SMC).
Détection mathématique des Market Structure Shifts, Fair Value Gaps (FVG),
Order Blocks (OB), et confirmation Volume Delta (CVD).
"""

import pandas as pd
import numpy as np

class SMCEngine:
    def __init__(self, atr_multiplier=1.5):
        self.atr_multiplier = atr_multiplier

    def analyze_market_structure_1h(self, df_1h):
        """
        Détermine la structure de marché macro sur 1H :
        - 'BULLISH' : Sommets et creux de plus en plus hauts (Higher Highs / Higher Lows).
        - 'BEARISH' : Sommets et creux de plus en plus bas (Lower Highs / Lower Lows).
        - 'NEUTRAL' : Marché en consolidation ou sans direction claire.
        """
        if df_1h is None or len(df_1h) < 20:
            return 'NEUTRAL', {}

        # Identification des Swing Highs et Swing Lows locaux (fenêtre de 3 bougies de chaque côté)
        window = 3
        df = df_1h.copy()
        df['swing_high'] = df['high'][(df['high'] == df['high'].rolling(window * 2 + 1, center=True).max())]
        df['swing_low'] = df['low'][(df['low'] == df['low'].rolling(window * 2 + 1, center=True).min())]

        recent_highs = df['swing_high'].dropna().tail(3).values
        recent_lows = df['swing_low'].dropna().tail(3).values

        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            is_hh = recent_highs[-1] > recent_highs[-2]
            is_hl = recent_lows[-1] > recent_lows[-2]
            is_lh = recent_highs[-1] < recent_highs[-2]
            is_ll = recent_lows[-1] < recent_lows[-2]

            if is_hh and is_hl:
                return 'BULLISH', {'recent_high': recent_highs[-1], 'recent_low': recent_lows[-1]}
            elif is_lh and is_ll:
                return 'BEARISH', {'recent_high': recent_highs[-1], 'recent_low': recent_lows[-1]}

        # Tendance de secours via Moyennes Mobiles Exponentielles Rapide/Lente (EMA 20 vs EMA 50)
        ema20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema50 = df['close'].ewm(span=50).mean().iloc[-1]
        current_close = df['close'].iloc[-1]

        if current_close > ema20 > ema50:
            return 'BULLISH', {'ema20': ema20, 'ema50': ema50}
        elif current_close < ema20 < ema50:
            return 'BEARISH', {'ema20': ema20, 'ema50': ema50}

        return 'NEUTRAL', {}

    def find_fair_value_gaps_15m(self, df_15m):
        """
        Détecte les Fair Value Gaps (FVG) non comblés sur 15m.
        Un FVG se forme sur 3 bougies consécutives (i-2, i-1, i) :
        - Bullish FVG : Low(i) > High(i-2) (trou de liquidité acheteur)
        - Bearish FVG : High(i) < Low(i-2) (trou de liquidité vendeur)
        """
        bullish_fvgs = []
        bearish_fvgs = []

        if df_15m is None or len(df_15m) < 10:
            return bullish_fvgs, bearish_fvgs

        # On analyse les 25 dernières bougies fermées
        for i in range(len(df_15m) - 25, len(df_15m) - 1):
            if i < 2:
                continue
            
            c_prev = df_15m.iloc[i - 2]
            c_curr = df_15m.iloc[i - 1]
            c_next = df_15m.iloc[i]

            # Bullish FVG
            if c_next['low'] > c_prev['high']:
                gap_size = c_next['low'] - c_prev['high']
                gap_pct = (gap_size / c_curr['close']) * 100.0
                
                # Seuil de significativité : au moins 0.25% de trou
                if gap_pct >= 0.25:
                    top = c_next['low']
                    bottom = c_prev['high']
                    midpoint = (top + bottom) / 2.0  # Consequent Encroachment (50%)
                    bullish_fvgs.append({
                        'index': i,
                        'timestamp': c_curr['timestamp'],
                        'top': top,
                        'bottom': bottom,
                        'midpoint': midpoint,
                        'gap_pct': gap_pct
                    })

            # Bearish FVG
            elif c_next['high'] < c_prev['low']:
                gap_size = c_prev['low'] - c_next['high']
                gap_pct = (gap_size / c_curr['close']) * 100.0
                
                if gap_pct >= 0.25:
                    top = c_prev['low']
                    bottom = c_next['high']
                    midpoint = (top + bottom) / 2.0
                    bearish_fvgs.append({
                        'index': i,
                        'timestamp': c_curr['timestamp'],
                        'top': top,
                        'bottom': bottom,
                        'midpoint': midpoint,
                        'gap_pct': gap_pct
                    })

        return bullish_fvgs, bearish_fvgs

    def find_order_blocks_15m(self, df_15m):
        """
        Repère les Order Blocks (OB) institutionnels :
        - Bullish OB : Dernière bougie baissière avant une violente impulsion haussière.
        - Bearish OB : Dernière bougie haussière avant une violente impulsion baissière.
        """
        bullish_obs = []
        bearish_obs = []

        if df_15m is None or len(df_15m) < 15:
            return bullish_obs, bearish_obs

        for i in range(len(df_15m) - 20, len(df_15m) - 2):
            c_ob = df_15m.iloc[i]
            c_impulse1 = df_15m.iloc[i + 1]
            c_impulse2 = df_15m.iloc[i + 2]

            # Bullish Order Block : Bougie rouge suivie d'une forte explosion verte
            if c_ob['close'] < c_ob['open']:
                impulse_size = (c_impulse1['close'] - c_ob['low']) / c_ob['low'] * 100.0
                if impulse_size >= 0.60:
                    bullish_obs.append({
                        'index': i,
                        'high': c_ob['high'],
                        'low': c_ob['low'],
                        'open': c_ob['open'],
                        'close': c_ob['close']
                    })

            # Bearish Order Block : Bougie verte suivie d'une violente chute rouge
            elif c_ob['close'] > c_ob['open']:
                dump_size = (c_ob['high'] - c_impulse1['close']) / c_ob['high'] * 100.0
                if dump_size >= 0.60:
                    bearish_obs.append({
                        'index': i,
                        'high': c_ob['high'],
                        'low': c_ob['low'],
                        'open': c_ob['open'],
                        'close': c_ob['close']
                    })

        return bullish_obs, bearish_obs

    def detect_setup(self, symbol, df_1h, df_15m, btc_dump_pct=0.0):
        """
        Scanne et synthétise tous les critères institutionnels pour générer
        un signal chirurgical avec prix exacts de Limit Order, Stop Loss et Take Profits.
        """
        if df_1h is None or df_15m is None or len(df_15m) < 20:
            return None

        # 1. Filtre Parapluie Bitcoin
        if symbol != 'BTC/USDT' and btc_dump_pct <= -1.8:
            return None # Alerte rouge : BTC chute, aucun achat altcoin autorisé

        # 2. Tendance Macro 1H
        macro_trend, _ = self.analyze_market_structure_1h(df_1h)
        if macro_trend == 'NEUTRAL':
            return None # Pas de consensus macro, on évite le chop

        # Données de la dernière bougie 15m
        last_candle = df_15m.iloc[-1]
        current_price = last_candle['close']
        atr_15m = last_candle['atr']
        if pd.isna(atr_15m) or atr_15m <= 0:
            atr_15m = current_price * 0.01

        # Anomalies 15m
        bullish_fvgs, bearish_fvgs = self.find_fair_value_gaps_15m(df_15m)
        bullish_obs, bearish_obs = self.find_order_blocks_15m(df_15m)

        # Vérification CVD / Delta sur les 5 dernières bougies
        recent_delta = df_15m['delta'].iloc[-5:].sum()

        # --- SCÉNARIO LONG (ACHAT) ---
        if macro_trend == 'BULLISH' and recent_delta > 0:
            # Cherche un FVG ou un OB actif juste sous le prix actuel pour placer un ordre Maker Limit
            target_fvg = None
            for fvg in reversed(bullish_fvgs):
                # La zone FVG doit être en dessous du prix actuel ou en cours de test
                if current_price >= fvg['bottom'] and (current_price - fvg['top']) / current_price < 0.025:
                    target_fvg = fvg
                    break

            if target_fvg:
                # Entrée Maker au sommet ou au midpoint du FVG
                entry_price = round(target_fvg['top'], 4)
                # Stop Loss sous le FVG avec tampon ATR
                sl_distance = (self.atr_multiplier * atr_15m)
                sl_price = round(target_fvg['bottom'] - sl_distance, 4)

                # Validation que le SL est cohérent (distance > 0.4%)
                risk_pct = (entry_price - sl_price) / entry_price * 100.0
                if 0.4 <= risk_pct <= 4.0:
                    risk_amount_price = entry_price - sl_price
                    tp1_price = round(entry_price + (1.5 * risk_amount_price), 4)
                    tp2_price = round(entry_price + (3.0 * risk_amount_price), 4)

                    return {
                        'symbol': symbol,
                        'direction': 'LONG',
                        'current_price': current_price,
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp1_price': tp1_price,
                        'tp2_price': tp2_price,
                        'risk_distance_pct': risk_pct,
                        'macro_trend': macro_trend,
                        'pattern': f"Bullish FVG [{round(target_fvg['bottom'], 2)} - {round(target_fvg['top'], 2)}]",
                        'cvd_confirmation': True,
                        'atr': atr_15m
                    }

        # --- SCÉNARIO SHORT (VENTE / DÉRIVÉS) ---
        elif macro_trend == 'BEARISH' and recent_delta < 0:
            target_fvg = None
            for fvg in reversed(bearish_fvgs):
                if current_price <= fvg['top'] and (fvg['bottom'] - current_price) / current_price < 0.025:
                    target_fvg = fvg
                    break

            if target_fvg:
                entry_price = round(target_fvg['bottom'], 4)
                sl_distance = (self.atr_multiplier * atr_15m)
                sl_price = round(target_fvg['top'] + sl_distance, 4)

                risk_pct = (sl_price - entry_price) / entry_price * 100.0
                if 0.4 <= risk_pct <= 4.0:
                    risk_amount_price = sl_price - entry_price
                    tp1_price = round(entry_price - (1.5 * risk_amount_price), 4)
                    tp2_price = round(entry_price - (3.0 * risk_amount_price), 4)

                    return {
                        'symbol': symbol,
                        'direction': 'SHORT',
                        'current_price': current_price,
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp1_price': tp1_price,
                        'tp2_price': tp2_price,
                        'risk_distance_pct': risk_pct,
                        'macro_trend': macro_trend,
                        'pattern': f"Bearish FVG [{round(target_fvg['bottom'], 2)} - {round(target_fvg['top'], 2)}]",
                        'cvd_confirmation': True,
                        'atr': atr_15m
                    }

        return None
