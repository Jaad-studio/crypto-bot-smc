"""
Module de Notification Discord Webhook Enrichi (Quantitative Alert Engine).
Envoie des alertes JSON stylisées (Embeds) prêtes à exécuter avec :
- Métriques quantitatives (Régime, Setup Quality, Confiance)
- Dimensionnement de Kelly fractionnaire
- Statut du Kill-Switch déterministe
- Bilan nocturne de calibration (Brier Score)
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def send_trade_signal(self, trade_params: Dict[str, Any], regime_info: Optional[Dict[str, Any]] = None):
        """
        Envoie un signal d'entrée institutionnel vers Discord avec couches quantitatives.
        """
        direction = trade_params['direction']
        is_long = direction == 'LONG'
        color = 0x10B981 if is_long else 0xEF4444
        symbol = trade_params['symbol']
        entry = trade_params['entry_price']
        sl = trade_params['sl_price']
        tp1 = trade_params['tp1_price']
        tp2 = trade_params['tp2_price']
        quantity = trade_params['quantity']
        risk_cash = trade_params['risk_cash']
        notional = trade_params['notional_value']
        pattern = trade_params['pattern']

        setup_quality = trade_params.get('setup_quality', 2.0)
        confidence = trade_params.get('confidence', 0.80)
        confidence_pct = round(confidence * 100, 1)
        sizing_method = trade_params.get('sizing_method', 'Quarter-Kelly (0.25x)')
        risk_state = trade_params.get('risk_state', 'SAFE').upper()
        drawdown_pct = trade_params.get('current_drawdown_pct', 0.0)

        regime_str = "TRENDING"
        if regime_info:
            regime_str = str(regime_info.get('regime', 'trending')).upper()

        stars = "⭐️" * int(min(3, max(1, round(setup_quality))))

        # Explication en français simple et vulgarisée
        if is_long:
            instruction_title = "💡 CE QUE LE BOT TE CONSEILLE DE FAIRE :"
            instruction_text = (
                f"1. **ACHÈTE** `{symbol}` sur Binance au prix de **`{entry} $`** (avec environ **`{notional} $`**).\n"
                f"2. **METS TA SÉCURITÉ (Stop Loss) :** Si le cours baisse sous **`{sl} $`**, coupe tout (perte limitée à **`-{risk_cash} €`**).\n"
                f"3. **PRENDS TES BÉNÉFICES (Étape 1) :** Quand le prix monte à **`{tp1} $`**, vends la moitié (50%) pour empocher **`+{trade_params['gain_tp1']} €`**.\n"
                f"4. **PASSE EN RISQUE ZÉRO (Breakeven) :** Dès que l'étape 1 est validée, remonte ton Stop Loss à **`{entry} $`** (ton prix d'achat) : impossible de perdre le moindre centime !\n"
                f"5. **OBJECTIF FINAL (Étape 2) :** Vends le reste quand le prix touche **`{tp2} $`** pour empocher **`+{trade_params['gain_tp2']} €`** de plus (Gain total : **`+{trade_params['total_projected_profit']} €`**)."
            )
        else:
            instruction_title = "💡 CE QUE LE BOT TE CONSEILLE DE FAIRE (POSITION SHORT) :"
            instruction_text = (
                f"1. **VENDS (SHORT)** `{symbol}` à **`{entry} $`** en pariant sur la baisse.\n"
                f"2. **METS TA SÉCURITÉ (Stop Loss) :** Si le cours remonte au-dessus de **`{sl} $`**, coupe la position (perte max: **`-{risk_cash} €`**).\n"
                f"3. **SÉCURISE TES GAINS (Étape 1) :** Dès que le prix descend à **`{tp1} $`**, rachète la moitié pour empocher **`+{trade_params['gain_tp1']} €`**.\n"
                f"4. **PASSE EN RISQUE ZÉRO :** Déplace aussitôt ton Stop Loss au prix de départ (**`{entry} $`**).\n"
                f"5. **OBJECTIF FINAL (Étape 2) :** Rachète les 50% restants quand le prix chute à **`{tp2} $`** (Gain total : **`+{trade_params['total_projected_profit']} €`**)."
            )

        embed = {
            "title": f"🟢 SIGNAL ACHAT INSTITUTIONNEL : {symbol}",
            "description": (
                f"**Modèle :** Smart Money Concepts `{pattern}`\n"
                f"**Régime Macro :** `{regime_str}` | **État du Risque :** `{risk_state}`"
            ),
            "color": color,
            "fields": [
                {
                    "name": "🎯 Prix d'Entrée (Limit)",
                    "value": f"**{entry} $**",
                    "inline": True
                },
                {
                    "name": "🛑 Stop Loss (Strict)",
                    "value": f"**{sl} $** (-{risk_cash} €)",
                    "inline": True
                },
                {
                    "name": "💰 TP1 (50% + Breakeven)",
                    "value": f"**{tp1} $** (+{trade_params['gain_tp1']} €)",
                    "inline": True
                },
                {
                    "name": "🚀 TP2 (Objectif Final)",
                    "value": f"**{tp2} $** (+{trade_params['total_projected_profit']} €)",
                    "inline": True
                },
                {
                    "name": "📊 Score IA & Calibration",
                    "value": f"{stars} **{setup_quality}/3.0** (Confiance: **{confidence_pct}%**)",
                    "inline": True
                },
                {
                    "name": "📐 Taille Recommandée (Kelly)",
                    "value": f"{sizing_method}\n**{risk_cash} €** risqués",
                    "inline": True
                },
                {
                    "name": instruction_title,
                    "value": instruction_text,
                    "inline": False
                }
            ],
            "footer": {
                "text": "Antigravity Quant Architecture • Risk-First Trading Loop",
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        self._print_terminal_banner(trade_params)

        if not self.webhook_url:
            logging.warning("Aucun Webhook Discord configuré. Alerte affichée en console uniquement.")
            return False

        try:
            payload = {"embeds": [embed]}
            res = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return res.status_code in [200, 204]
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi vers Discord : {e}")
            return False

    def send_kill_switch_alert(self, reason: str, drawdown_pct: float, capital: float):
        """Alerte rouge d'urgence si le Kill-Switch déterministe se déclenche."""
        embed = {
            "title": "🚨 VERROUILLAGE D'URGENCE (KILL-SWITCH DÉCLENCHÉ)",
            "description": (
                f"**Le système a bloqué l'ouverture de tout nouvel ordre.**\n\n"
                f"**Raison :** {reason}\n"
                f"**Drawdown Actuel :** `{drawdown_pct}%` (Plafond infranchissable: 15%)\n"
                f"**Capital restant :** `{capital:.2f} €`"
            ),
            "color": 0xFF0000,
            "footer": {"text": "Protection Déterministe du Capital • Intervention Manuelle Requise"},
            "timestamp": datetime.utcnow().isoformat()
        }
        self._send_raw_embed(embed)

    def send_overnight_review(self, metrics: Dict[str, Any]):
        """Envoie le bilan nocturne de calibration Brier Score sur Discord."""
        if metrics.get('status') != 'success':
            return

        embed = {
            "title": "🌙 Bilan Nocturne & Calibration Statistique (Brier Score)",
            "description": f"Revue automatique des performances et de la calibration du modèle.",
            "color": 0x6366F1,
            "fields": [
                {
                    "name": "🎯 Brier Score (Calibration)",
                    "value": f"**`{metrics['brier_score']}`**\n*{metrics['calibration_grade']}*",
                    "inline": True
                },
                {
                    "name": "📈 Win Rate (Taux Réussite)",
                    "value": f"**{metrics['win_rate_pct']}%** ({metrics['wins']}W / {metrics['losses']}L)",
                    "inline": True
                },
                {
                    "name": "💰 PnL Net Total",
                    "value": f"**{metrics['total_pnl_eur']:+.2f} €**",
                    "inline": True
                },
                {
                    "name": "⚖️ Profit Factor",
                    "value": f"**{metrics['profit_factor']}**",
                    "inline": True
                },
                {
                    "name": "📊 Gains vs Pertes Moyens",
                    "value": f"+{metrics['avg_gain_eur']} € / -{metrics['avg_loss_eur']} €",
                    "inline": True
                },
                {
                    "name": "🔬 Volume d'échantillons",
                    "value": f"{metrics['total_trades_analyzed']} trades clôturés",
                    "inline": True
                }
            ],
            "footer": {"text": "Auto-Correction Nocturne • Compound Loop"},
            "timestamp": datetime.utcnow().isoformat()
        }
        self._send_raw_embed(embed)

    def send_status_message(self, title, message, color=0x3B82F6):
        """Envoie un message informatif (breakeven, sortie, alerte)."""
        embed = {
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._send_raw_embed(embed)

    def _send_raw_embed(self, embed_dict):
        if not self.webhook_url:
            logging.info(f"[DISCORD] {embed_dict.get('title')}: {embed_dict.get('description')}")
            return False
        try:
            res = requests.post(self.webhook_url, json={"embeds": [embed_dict]}, timeout=10)
            return res.status_code in [200, 204]
        except Exception as e:
            logging.error(f"Erreur envoi Discord : {e}")
            return False

    def _print_terminal_banner(self, p):
        print("\n" + "=" * 65)
        print(f"🚨 [NOUVEAU SIGNAL DÉTECTÉ] {p['direction']} sur {p['symbol']}")
        print(f"   Score & Confiance   : {p.get('setup_quality', 2.0)}/3.0 ({round(p.get('confidence', 0.8)*100, 1)}%)")
        print(f"   Prix Entrée (Limit) : {p['entry_price']} $")
        print(f"   Stop Loss           : {p['sl_price']} $ (Perte max : -{p['risk_cash']} €)")
        print(f"   Take Profit 1       : {p['tp1_price']} $ (Sécurise 50% + SL à Breakeven)")
        print(f"   Take Profit 2       : {p['tp2_price']} $ (Objectif final : +{p['total_projected_profit']} €)")
        print(f"   Sizing (Kelly 0.25x): {p['risk_cash']} € risqués ({p.get('notional_value')} $ notionnel)")
        print("   ---")
        print(f"   💡 CONSEIL SIMPLE :")
        if p['direction'] == 'LONG':
            print(f"   1. Achète {p['symbol']} à {p['entry_price']}$")
            print(f"   2. Mets le Stop Loss à {p['sl_price']}$")
            print(f"   3. Dès que ça atteint {p['tp1_price']}$, vends 50% et monte ton SL à {p['entry_price']}$ (risque 0)")
            print(f"   4. Vends le reste quand ça atteint {p['tp2_price']}$ !")
        else:
            print(f"   1. Vends (Short) {p['symbol']} à {p['entry_price']}$")
            print(f"   2. Mets le Stop Loss à {p['sl_price']}$")
            print(f"   3. Dès que ça descend à {p['tp1_price']}$, rachète 50% et passe ton SL à {p['entry_price']}$")
            print(f"   4. Rachète le reste quand ça descend à {p['tp2_price']}$ !")
        print("=" * 65 + "\n", flush=True)
