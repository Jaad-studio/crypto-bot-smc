"""
Module de Notification Discord Webhook.
Envoie des alertes JSON stylisées (Embeds) prêtes à exécuter.
"""

import requests
import json
import logging
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def send_trade_signal(self, trade_params):
        """
        Envoie un signal d'entrée institutionnel vers Discord.
        """
        direction = trade_params['direction']
        is_long = direction == 'LONG'
        color = 0x10B981 if is_long else 0xEF4444 # Vert pour Long, Rouge pour Short
        icon = "🟢" if is_long else "🔴"

        symbol = trade_params['symbol']
        entry = trade_params['entry_price']
        sl = trade_params['sl_price']
        tp1 = trade_params['tp1_price']
        tp2 = trade_params['tp2_price']
        quantity = trade_params['quantity']
        risk_cash = trade_params['risk_cash']
        notional = trade_params['notional_value']
        lev = trade_params['leverage_recommended']
        profit = trade_params['total_projected_profit']
        pattern = trade_params['pattern']

        embed = {
            "title": f"{icon} SIGNAL ALGORITHMIQUE : {direction} SUR {symbol}",
            "description": f"**Zone institutionnelle détectée :** `{pattern}`\n**Exécution recommandée :** Ordre Limit (Maker 0% frais)",
            "color": color,
            "fields": [
                {
                    "name": "🎯 Entrée Maker (Limit)",
                    "value": f"`{entry}`",
                    "inline": True
                },
                {
                    "name": "🛑 Stop Loss",
                    "value": f"`{sl}`",
                    "inline": True
                },
                {
                    "name": "📊 Risque Max Perte",
                    "value": f"**-{risk_cash} €** (Risque maîtrisé)",
                    "inline": True
                },
                {
                    "name": "💰 TP1 (Vendre 50% + Breakeven)",
                    "value": f"`{tp1}` (+{trade_params['gain_tp1']} €)",
                    "inline": True
                },
                {
                    "name": "🚀 TP2 (Final Runner 50%)",
                    "value": f"`{tp2}` (+{trade_params['gain_tp2']} €)",
                    "inline": True
                },
                {
                    "name": "🏆 Profit Total Projeté",
                    "value": f"**+{profit} €** (R:R {trade_params['risk_reward_ratio']}x)",
                    "inline": True
                },
                {
                    "name": "📦 Position Sizing (Capital 300 €)",
                    "value": f"Quantité : `{quantity}` {symbol.split('/')[0]}\nValeur notionnelle : `{notional} $`\nLevier suggéré : `x{lev}`",
                    "inline": False
                }
            ],
            "footer": {
                "text": "SMC Quant Bot • Discipline & Risk Management",
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Terminal Fallback
        self._print_terminal_banner(trade_params)

        if not self.webhook_url:
            logging.warning("Aucun Webhook Discord configuré. Alerte affichée dans la console uniquement.")
            return False

        try:
            payload = {"embeds": [embed]}
            res = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if res.status_code in [200, 204]:
                logging.info(f"Signal {direction} pour {symbol} transmis avec succès sur Discord.")
                return True
            else:
                logging.error(f"Erreur Discord (Status {res.status_code}) : {res.text}")
                return False
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi vers Discord : {e}")
            return False

    def send_status_message(self, title, message, color=0x3B82F6):
        """Envoie un message informatif (breakeven, sortie, alerte)."""
        if not self.webhook_url:
            logging.info(f"[DISCORD INFO] {title} : {message}")
            return

        try:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            requests.post(self.webhook_url, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Erreur envoi status Discord : {e}")

    def _print_terminal_banner(self, p):
        print("\n" + "=" * 65)
        print(f"🚨 [NOUVEAU SIGNAL DÉTECTÉ] {p['direction']} sur {p['symbol']}")
        print(f"   Prix Entrée (Limit) : {p['entry_price']}")
        print(f"   Stop Loss           : {p['sl_price']} (Perte max : -{p['risk_cash']} €)")
        print(f"   Take Profit 1       : {p['tp1_price']} (Sécurise 50% + SL à Breakeven)")
        print(f"   Take Profit 2       : {p['tp2_price']} (Objectif final : +{p['total_projected_profit']} €)")
        print(f"   Taille Position     : {p['quantity']} (Valeur : {p['notional_value']} $ | Levier : x{p['leverage_recommended']})")
        print("=" * 65 + "\n")
