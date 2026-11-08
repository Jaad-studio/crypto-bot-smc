"""
Moteur de Gestion Mathématique du Risque et Risk Layer Déterministe.
Garantit la protection absolue du capital :
- Hard Kill-Switch déterministe (Max Drawdown 15% infranchissable)
- Sizing par critère de Kelly fractionnaire (0.25x Kelly)
- Filtrage strict des setups (Setup Quality >= 2 / 3 et Confiance >= 80%)
"""

import math
import logging
from typing import Dict, Any, Optional
from kelly_sizing import KellySizingEngine

class RiskEngine:
    def __init__(
        self,
        initial_capital: float = 300.0,
        risk_mode: str = 'kelly',  # 'kelly', 'percentage', ou 'fixed'
        risk_percent: float = 5.0,
        fixed_risk: float = 15.0,
        max_drawdown_pct: float = 15.0,
        max_daily_loss_pct: float = 5.0,
        min_setup_quality: float = 2.0,
        min_confidence: float = 0.80
    ):
        self.capital = initial_capital
        self.high_water_mark = initial_capital
        self.daily_start_capital = initial_capital
        
        self.risk_mode = risk_mode
        self.risk_percent = risk_percent
        self.fixed_risk = fixed_risk

        # Limites déterministes infranchissables
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_setup_quality = min_setup_quality
        self.min_confidence = min_confidence

        self.kill_switch_triggered = False
        self.kill_switch_reason = ""

        self.kelly_engine = KellySizingEngine(
            kelly_fraction=0.25,
            min_risk_pct=1.0,
            max_risk_pct=5.0
        )

    def update_capital(self, current_capital: float):
        """Met à jour le capital actuel et vérifie les seuils de Drawdown."""
        self.capital = current_capital
        if current_capital > self.high_water_mark:
            self.high_water_mark = current_capital

        # Vérification du Max Drawdown depuis le sommet historique (High Water Mark)
        drawdown_pct = ((self.high_water_mark - self.capital) / self.high_water_mark) * 100.0
        if drawdown_pct >= self.max_drawdown_pct:
            self.kill_switch_triggered = True
            self.kill_switch_reason = f"MAX DRAWDOWN DÉPASSÉ : Chute de {drawdown_pct:.1f}% (limite max: {self.max_drawdown_pct}%)"
            logging.critical(f"🚨 [KILL-SWITCH ARMÉ] {self.kill_switch_reason}")

        # Vérification de la perte journalière
        daily_loss_pct = ((self.daily_start_capital - self.capital) / self.daily_start_capital) * 100.0
        if daily_loss_pct >= self.max_daily_loss_pct:
            self.kill_switch_triggered = True
            self.kill_switch_reason = f"PERTE JOURNALIÈRE ATTEINTE : -{daily_loss_pct:.1f}% (limite max: {self.max_daily_loss_pct}%)"
            logging.critical(f"🚨 [KILL-SWITCH ARMÉ] {self.kill_switch_reason}")

    def reset_daily_metrics(self):
        """Réinitialise le capital de référence au début de chaque journée de trading."""
        self.daily_start_capital = self.capital
        if not self.is_drawdown_breached():
            self.kill_switch_triggered = False
            self.kill_switch_reason = ""

    def is_drawdown_breached(self) -> bool:
        drawdown_pct = ((self.high_water_mark - self.capital) / self.high_water_mark) * 100.0
        return drawdown_pct >= self.max_drawdown_pct

    def check_kill_switch(self) -> Dict[str, Any]:
        """Évalué obligatoirement avant le traitement de tout ordre."""
        drawdown_pct = ((self.high_water_mark - self.capital) / self.high_water_mark) * 100.0
        daily_loss_pct = ((self.daily_start_capital - self.capital) / self.daily_start_capital) * 100.0

        is_safe = not self.kill_switch_triggered and drawdown_pct < self.max_drawdown_pct
        risk_state = 'safe' if is_safe and drawdown_pct < (self.max_drawdown_pct * 0.7) else ('near_limit' if is_safe else 'reduce')

        return {
            'is_armed_and_safe': is_safe,
            'kill_switch_triggered': self.kill_switch_triggered,
            'reason': self.kill_switch_reason if self.kill_switch_triggered else "Normal",
            'current_drawdown_pct': round(drawdown_pct, 2),
            'daily_loss_pct': round(daily_loss_pct, 2),
            'risk_state': risk_state,
            'capital': round(self.capital, 2),
            'high_water_mark': round(self.high_water_mark, 2)
        }

    def compute_position_parameters(self, setup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        À partir du setup SMC et des métriques quantitatives :
        1. Vérifie le Kill-Switch déterministe.
        2. Filtre la qualité du setup (>= 2 / 3) et la confiance (>= 80%).
        3. Calcule le sizing via le critère de Kelly fractionnaire (0.25x).
        """
        # 1. Garde-fou Kill Switch
        ks_status = self.check_kill_switch()
        if not ks_status['is_armed_and_safe']:
            logging.warning(f"Ordre rejeté : Kill-Switch actif ({ks_status['reason']})")
            return None

        # 2. Filtrage Qualité et Confiance
        setup_quality = setup.get('setup_quality', 2.0)
        confidence = setup.get('confidence', 0.80)

        if setup_quality < self.min_setup_quality:
            logging.info(f"Signal ignoré pour {setup.get('symbol')} : Qualité {setup_quality:.1f} < seuil minimum {self.min_setup_quality}")
            return None

        if confidence < self.min_confidence:
            logging.info(f"Signal ignoré pour {setup.get('symbol')} : Confiance {confidence*100:.1f}% < seuil minimum {self.min_confidence*100}%")
            return None

        entry_price = setup['entry_price']
        sl_price = setup['sl_price']
        tp1_price = setup['tp1_price']
        tp2_price = setup['tp2_price']
        direction = setup['direction']

        price_risk_distance = abs(entry_price - sl_price)
        if price_risk_distance <= 0:
            return None

        # Ratio Gain / Perte moyen entre TP1 (1.5R) et TP2 (3.0R) = ~2.25R
        gain_distance_avg = ((abs(tp1_price - entry_price) * 0.5) + (abs(tp2_price - entry_price) * 0.5))
        reward_to_risk = gain_distance_avg / price_risk_distance

        # 3. Calcul du Risque Cash (Kelly Fractionnaire ou mode legacy)
        if self.risk_mode == 'kelly':
            kelly_res = self.kelly_engine.compute_kelly_risk(
                win_probability=confidence,
                reward_to_risk=reward_to_risk,
                current_capital=self.capital
            )
            if not kelly_res['is_mathematically_viable']:
                logging.info(f"Signal rejeté par Kelly : espérance mathématique négative.")
                return None
            risk_cash = kelly_res['risk_cash']
            risk_pct = kelly_res['recommended_risk_pct']
            sizing_method = f"Quarter-Kelly ({kelly_res['fractional_factor']}x)"
        elif self.risk_mode == 'percentage':
            risk_cash = (self.capital * self.risk_percent) / 100.0
            risk_pct = self.risk_percent
            sizing_method = f"Fixe ({self.risk_percent}%)"
        else:
            risk_cash = min(self.fixed_risk, self.capital * 0.20)
            risk_pct = (risk_cash / self.capital) * 100.0
            sizing_method = f"Fixe ({self.fixed_risk} €)"

        # Formule de Position Sizing : Quantité = Risque_Cash / |Entrée - SL|
        quantity = risk_cash / price_risk_distance
        notional_value = quantity * entry_price
        leverage_needed = notional_value / self.capital
        leverage_recommended = max(1, math.ceil(leverage_needed))

        gain_tp1 = 0.5 * quantity * abs(tp1_price - entry_price)
        gain_tp2 = 0.5 * quantity * abs(tp2_price - entry_price)
        total_projected_profit = gain_tp1 + gain_tp2
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
            'risk_pct': round(risk_pct, 1),
            'leverage_needed': round(leverage_needed, 2),
            'leverage_recommended': leverage_recommended,
            'gain_tp1': round(gain_tp1, 2),
            'gain_tp2': round(gain_tp2, 2),
            'total_projected_profit': round(total_projected_profit, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'pattern': setup['pattern'],
            # Nouvelles métriques quantitatives
            'setup_quality': setup_quality,
            'confidence': confidence,
            'sizing_method': sizing_method,
            'risk_state': ks_status['risk_state'],
            'current_drawdown_pct': ks_status['current_drawdown_pct']
        }
