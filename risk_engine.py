"""
Moteur de Gestion Mathématique du Risque et Position Sizing.
Calcule la taille exacte d'ordre pour ne jamais dépasser le risque alloué.
"""

import math

class RiskEngine:
    def __init__(self, initial_capital=300.0, risk_mode='percentage', risk_percent=5.0, fixed_risk=15.0):
        self.capital = initial_capital
        self.risk_mode = risk_mode
        self.risk_percent = risk_percent
        self.fixed_risk = fixed_risk

    def calculate_risk_amount(self):
        """Calcule le montant en EUR/USDT risqué sur le trade."""
        if self.risk_mode == 'percentage':
            return (self.capital * self.risk_percent) / 100.0
        else:
            return min(self.fixed_risk, self.capital * 0.20) # Garde-fou max 20%

    def compute_position_parameters(self, setup):
        """
        À partir du setup SMC, calcule :
        - La quantité exacte de crypto à acheter/vendre.
        - La valeur notionnelle de la position.
        - Le levier nécessaire.
        - Le gain attendu sur TP1 (50%) et TP2 (50%).
        """
        entry_price = setup['entry_price']
        sl_price = setup['sl_price']
        tp1_price = setup['tp1_price']
        tp2_price = setup['tp2_price']
        direction = setup['direction']

        # Distance en dollars/unités
        price_risk_distance = abs(entry_price - sl_price)
        if price_risk_distance <= 0:
            return None

        # Montant risqué (ex: 15 €)
        risk_cash = self.calculate_risk_amount()

        # Formule de Position Sizing : Quantité = Risque_Cash / |Entrée - SL|
        quantity = risk_cash / price_risk_distance

        # Valeur totale de la position en USDT
        notional_value = quantity * entry_price

        # Levier nécessaire par rapport au capital de 300 €
        leverage_needed = notional_value / self.capital
        leverage_recommended = max(1, math.ceil(leverage_needed))

        # Gains projetés
        gain_tp1 = 0.5 * quantity * abs(tp1_price - entry_price)
        gain_tp2 = 0.5 * quantity * abs(tp2_price - entry_price)
        total_projected_profit = gain_tp1 + gain_tp2

        # Ratio global Gain / Perte
        risk_reward_ratio = total_projected_profit / risk_cash if risk_cash > 0 else 0.0

        return {
            'symbol': setup['symbol'],
            'direction': direction,
            'entry_price': entry_price,
            'sl_price': sl_price,
            'tp1_price': tp1_price,
            'tp2_price': tp2_price,
            'quantity': round(quantity, 4),
            'notional_value': round(notional_value, 2),
            'capital_used': round(self.capital, 2),
            'risk_cash': round(risk_cash, 2),
            'risk_pct': round((risk_cash / self.capital) * 100.0, 1),
            'leverage_needed': round(leverage_needed, 2),
            'leverage_recommended': leverage_recommended,
            'gain_tp1': round(gain_tp1, 2),
            'gain_tp2': round(gain_tp2, 2),
            'total_projected_profit': round(total_projected_profit, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'pattern': setup['pattern']
        }
