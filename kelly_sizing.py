"""
Module de Dimensionnement Statistique de Position (Kelly Criterion Engine).
Implémente le critère de Kelly fractionnaire (Fractional Kelly) bridé à 1/4 Kelly.
Optimise la croissance géométrique du capital tout en prévenant mathématiquement le risque de ruine.
"""

import math
from typing import Dict, Any

class KellySizingEngine:
    def __init__(self, kelly_fraction: float = 0.25, min_risk_pct: float = 1.0, max_risk_pct: float = 5.0):
        """
        :param kelly_fraction: Fraction de Kelly appliquée (0.25 = Quarter Kelly, standard institutionnel)
        :param min_risk_pct: Plancher de risque minimum (% du capital)
        :param max_risk_pct: Plafond de risque absolu (% du capital, garde-fou)
        """
        self.kelly_fraction = kelly_fraction
        self.min_risk_pct = min_risk_pct
        self.max_risk_pct = max_risk_pct

    def compute_kelly_risk(self, win_probability: float, reward_to_risk: float, current_capital: float) -> Dict[str, Any]:
        """
        Calcule la part du capital à risquer selon la formule :
        f* = p - (1 - p) / b
        où :
        - p = probabilité estimée de gain (calibrée par le score de confiance)
        - b = ratio gain / perte attendu (Reward / Risk)
        """
        p = max(0.01, min(0.99, win_probability))
        q = 1.0 - p
        b = max(0.5, reward_to_risk)

        # Formule Kelly standard
        raw_kelly = (p * (b + 1.0) - 1.0) / b

        # Si l'espérance mathématique est négative, ne pas risquer de capital
        if raw_kelly <= 0:
            recommended_pct = 0.0
            risk_cash = 0.0
            is_viable = False
        else:
            # Application du quart de Kelly (0.25x)
            fractional_kelly_pct = (raw_kelly * self.kelly_fraction) * 100.0

            # Borner entre min_risk_pct et max_risk_pct
            recommended_pct = max(self.min_risk_pct, min(self.max_risk_pct, fractional_kelly_pct))
            risk_cash = (current_capital * recommended_pct) / 100.0
            is_viable = True

        return {
            'win_probability': round(p, 3),
            'reward_to_risk': round(b, 2),
            'raw_kelly_pct': round(max(0.0, raw_kelly * 100.0), 2),
            'fractional_factor': self.kelly_fraction,
            'recommended_risk_pct': round(recommended_pct, 2),
            'risk_cash': round(risk_cash, 2),
            'is_mathematically_viable': is_viable
        }
