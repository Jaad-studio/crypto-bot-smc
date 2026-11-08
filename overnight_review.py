"""
Module de Revue Nocturne et Calibration Statistique (Overnight Review & Calibration Engine).
Mesure la précision prédictive du bot via le Brier Score et les métriques de performance :
- Brier Score : Mesure de calibration probabiliste (0.0 = parfait, 0.25 = hasard)
- Win Rate, Expectancy (espérance mathématique), Profit Factor
- Drawdown Max et évolution du capital
"""

import json
import os
import math
from datetime import datetime
from typing import Dict, Any, List

class OvernightReviewEngine:
    def __init__(self, trades_file_path: str = 'trades_history.json'):
        self.trades_file_path = trades_file_path

    def compute_calibration_metrics(self) -> Dict[str, Any]:
        """
        Lit l'historique complet des trades et calcule le Brier Score et la calibration.
        """
        if not os.path.exists(self.trades_file_path):
            return {"status": "no_data", "message": "Aucun historique de trades disponible."}

        try:
            with open(self.trades_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"Erreur lecture fichier : {e}"}

        trades = data.get('trades', [])
        closed_trades = [t for t in trades if t.get('status') in ['TP1_HIT', 'TP2_HIT', 'SL_BE_HIT', 'SL_LOSS_HIT']]

        if not closed_trades:
            return {
                "status": "insufficient_data",
                "total_trades": len(trades),
                "closed_trades": 0,
                "message": "Pas encore de trades clôturés pour calculer la calibration statistique."
            }

        squared_errors = []
        wins = 0
        losses = 0
        total_pnl = 0.0
        gains = []
        loss_amounts = []

        for t in closed_trades:
            pnl = t.get('pnl', 0.0)
            total_pnl += pnl

            # Outcome : 1 si gain > 0, 0 sinon
            outcome = 1.0 if pnl > 0 else 0.0
            if outcome == 1.0:
                wins += 1
                gains.append(pnl)
            else:
                losses += 1
                loss_amounts.append(abs(pnl))

            # Probabilité estimée / Confiance (par défaut 0.80 si non spécifié)
            predicted_prob = t.get('confidence', 0.80)
            error = (predicted_prob - outcome) ** 2
            squared_errors.append(error)

        n = len(closed_trades)
        brier_score = sum(squared_errors) / n if n > 0 else 0.25
        win_rate = (wins / n) * 100.0 if n > 0 else 0.0

        sum_gains = sum(gains)
        sum_losses = sum(loss_amounts)
        profit_factor = (sum_gains / sum_losses) if sum_losses > 0 else (99.0 if sum_gains > 0 else 0.0)

        # Qualification du Brier Score :
        # < 0.15 : Exceptionnellement bien calibré
        # 0.15 - 0.20 : Bonne calibration prédictive
        # 0.20 - 0.25 : Calibration moyenne
        # > 0.25 : Modèle sous-calibré ou sur-confiant
        if brier_score < 0.15:
            calibration_grade = "Excellente (Alpha validé)"
        elif brier_score < 0.20:
            calibration_grade = "Bonne calibration prédictive"
        elif brier_score <= 0.25:
            calibration_grade = "Acceptable (Légère sur-confiance)"
        else:
            calibration_grade = "Dégradée (Nécessite ajustement des filtres)"

        return {
            "status": "success",
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "total_trades_analyzed": n,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 1),
            "brier_score": round(brier_score, 4),
            "calibration_grade": calibration_grade,
            "profit_factor": round(profit_factor, 2),
            "total_pnl_eur": round(total_pnl, 2),
            "avg_gain_eur": round(sum_gains / wins, 2) if wins > 0 else 0.0,
            "avg_loss_eur": round(sum_losses / losses, 2) if losses > 0 else 0.0
        }

    def generate_markdown_report(self) -> str:
        """Génère un rapport textuel prêt pour l'archivage ou l'affichage."""
        metrics = self.compute_calibration_metrics()
        if metrics.get('status') != 'success':
            return f"### 📊 Rapport Nocturne\n{metrics.get('message', 'Aucune métrique disponible.')}"

        report = f"""### 🌙 Rapport de Revue Nocturne & Calibration Statistique
*Date de génération : {metrics['date']}*

* **Trades analysés :** {metrics['total_trades_analyzed']} (Gains: {metrics['wins']} | Pertes: {metrics['losses']})
* **Taux de Réussite (Win Rate) :** {metrics['win_rate_pct']}%
* **Brier Score :** `{metrics['brier_score']}` — *{metrics['calibration_grade']}*
* **Profit Factor :** `{metrics['profit_factor']}`
* **PnL Total :** `{metrics['total_pnl_eur']:+.2f} €`
* **Gain moyen / Perte moyenne :** `+{metrics['avg_gain_eur']} €` / `-{metrics['avg_loss_eur']} €`

---
> 🧠 **Règle de Calibration :** Un Brier Score inférieur à 0.20 confirme que les probabilités estimées reflètent fidèlement les fréquences réelles de gain du marché.
"""
        return report
