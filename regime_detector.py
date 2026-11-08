"""
Module de Détection des Régimes de Marché Macro (Market Regime Engine).
Catégorise le marché en 4 états stricts :
- 'trending' : Tendance saine et directionnelle (conditions idéales).
- 'mean_reverting' : Marché en range à faible volatilité.
- 'high_vol' : Volatilité anormale ou erratique (risque accru).
- 'crisis' : Décrochage brutal ou flash crash (verrouillage immédiat des positions).
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class MarketRegimeSnapshot:
    regime: str             # 'trending' | 'mean_reverting' | 'high_vol' | 'crisis'
    allow_trading: bool     # True si le régime autorise l'ouverture de nouveaux trades
    btc_1h_change_pct: float
    btc_price: float
    realized_volatility: float
    volatility_ratio: float
    reason: str
    risk_state: str         # 'safe' | 'near_limit' | 'reduce'

class MarketRegimeDetector:
    def __init__(self, provider, btc_crisis_threshold: float = -1.8, high_vol_multiplier: float = 2.2):
        self.provider = provider
        self.btc_crisis_threshold = btc_crisis_threshold
        self.high_vol_multiplier = high_vol_multiplier

    def evaluate_regime(self, benchmark_symbol: str = 'BTC/USDT') -> MarketRegimeSnapshot:
        """
        Analyse les bougies 1H du Bitcoin (la boussole du marché crypto)
        pour déterminer le régime macro actuel.
        """
        try:
            df_1h = self.provider.fetch_ohlcv(benchmark_symbol, timeframe='1h', limit=40)
            if df_1h is None or len(df_1h) < 20:
                # En cas de données incomplètes, principe de précaution
                return MarketRegimeSnapshot(
                    regime='crisis',
                    allow_trading=False,
                    btc_1h_change_pct=0.0,
                    btc_price=0.0,
                    realized_volatility=0.0,
                    volatility_ratio=1.0,
                    reason="Données de marché insuffisantes pour qualifier le régime",
                    risk_state='reduce'
                )

            # 1. Performance 1H
            last_close = df_1h['close'].iloc[-1]
            prev_close = df_1h['close'].iloc[-2]
            btc_1h_change = ((last_close - prev_close) / prev_close) * 100.0

            # 2. Volatilité Réalisée (écart-type des rendements horaires annualisé/normalisé)
            returns = df_1h['close'].pct_change().dropna()
            current_vol = returns.tail(6).std() * 100.0  # volatilité sur 6h
            baseline_vol = returns.std() * 100.0         # volatilité moyenne sur 40h
            vol_ratio = (current_vol / baseline_vol) if baseline_vol > 0 else 1.0

            # 3. Structure de tendance (EMA 10 vs EMA 30)
            ema10 = df_1h['close'].ewm(span=10).mean().iloc[-1]
            ema30 = df_1h['close'].ewm(span=30).mean().iloc[-1]
            is_trending = abs((ema10 - ema30) / ema30) > 0.006

            # --- DÉCISION DE RÉGIME DÉTERMINISTE ---

            # RÈGLE 1 : CRISIS (Flash crash ou dump sévère)
            if btc_1h_change <= self.btc_crisis_threshold or (returns.tail(3).sum() * 100.0) <= -3.0:
                return MarketRegimeSnapshot(
                    regime='crisis',
                    allow_trading=False,
                    btc_1h_change_pct=round(btc_1h_change, 2),
                    btc_price=round(last_close, 2),
                    realized_volatility=round(current_vol, 2),
                    volatility_ratio=round(vol_ratio, 2),
                    reason=f"Chute brutale du Bitcoin ({btc_1h_change:.2f}% en 1H) sous le seuil d'urgence ({self.btc_crisis_threshold}%)",
                    risk_state='reduce'
                )

            # RÈGLE 2 : HIGH VOLATILITY (Spike de volatilité sans direction claire)
            if vol_ratio >= self.high_vol_multiplier:
                return MarketRegimeSnapshot(
                    regime='high_vol',
                    allow_trading=False,
                    btc_1h_change_pct=round(btc_1h_change, 2),
                    btc_price=round(last_close, 2),
                    realized_volatility=round(current_vol, 2),
                    volatility_ratio=round(vol_ratio, 2),
                    reason=f"Volatilité anormale ({vol_ratio:.2f}x supérieure à la moyenne). Risque de slippage excessif.",
                    risk_state='near_limit'
                )

            # RÈGLE 3 : TRENDING (Tendance haussière ou baissière saine)
            if is_trending and vol_ratio < self.high_vol_multiplier:
                trend_dir = "haussière" if ema10 > ema30 else "baissière"
                return MarketRegimeSnapshot(
                    regime='trending',
                    allow_trading=True,
                    btc_1h_change_pct=round(btc_1h_change, 2),
                    btc_price=round(last_close, 2),
                    realized_volatility=round(current_vol, 2),
                    volatility_ratio=round(vol_ratio, 2),
                    reason=f"Tendance saine {trend_dir} avec volatilité maîtrisée ({vol_ratio:.2f}x)",
                    risk_state='safe'
                )

            # RÈGLE 4 : MEAN REVERTING (Consolidation / Range)
            return MarketRegimeSnapshot(
                regime='mean_reverting',
                allow_trading=True,
                btc_1h_change_pct=round(btc_1h_change, 2),
                btc_price=round(last_close, 2),
                realized_volatility=round(current_vol, 2),
                volatility_ratio=round(vol_ratio, 2),
                reason="Marché en range horizontal. Seuls les setups parfaits sur rebond sont filtrés.",
                risk_state='safe'
            )

        except Exception as e:
            logging.error(f"Erreur lors de l'évaluation du régime : {e}")
            return MarketRegimeSnapshot(
                regime='crisis',
                allow_trading=False,
                btc_1h_change_pct=0.0,
                btc_price=0.0,
                realized_volatility=0.0,
                volatility_ratio=1.0,
                reason=f"Exception interne : {e}",
                risk_state='reduce'
            )
