"""
Module de Notification Discord Webhook Ultra-Clair & Pédagogique.
Formate tous les messages dans un français simple, direct et sans jargon,
pensé pour être lu et compris en 3 secondes sur l'application mobile Discord.
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
        Envoie un signal d'achat/vente ultra-lisible avec instructions pas à pas.
        """
        direction = trade_params['direction']
        is_long = direction == 'LONG'
        symbol = trade_params['symbol']
        crypto_name = symbol.split('/')[0]
        entry = trade_params['entry_price']
        sl = trade_params['sl_price']
        tp1 = trade_params['tp1_price']
        tp2 = trade_params['tp2_price']
        risk_cash = trade_params['risk_cash']
        notional = trade_params['notional_value']
        confidence_pct = round(trade_params.get('confidence', 0.80) * 100, 1)

        action_word = "ACHETER" if is_long else "VENDRE (PARIER À LA BAISSE)"
        color = 0x10B981 if is_long else 0xEF4444

        description = (
            f"🔔 **Opportunité détectée par l'algorithme**\n"
            f"Confiance estimée : **{confidence_pct}%**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 **CE QUE TU DOIS FAIRE SUR BINANCE :**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**1️⃣ ÉTAPE 1 : ENTRER EN POSITION**\n"
            f"• Action : **{action_word} `{crypto_name}`**\n"
            f"• Prix conseillé : **`{entry} $`** (ou au prix actuel)\n"
            f"• Montant à mettre : environ **`{notional} $`**\n\n"
            f"**2️⃣ ÉTAPE 2 : METTRE LA SÉCURITÉ (STOP LOSS)**\n"
            f"• Si le prix touche **`{sl} $`**, vends tout.\n"
            f"• *Ta perte sera bloquée à maximum **`-{risk_cash} €`**.*\n\n"
            f"**3️⃣ ÉTAPE 3 : ENCAISSER LE PREMIER BÉNÉFICE**\n"
            f"• Dès que le prix atteint **`{tp1} $`**, vends la moitié (50%).\n"
            f"• *Tu empoches immédiatement **`+{trade_params['gain_tp1']} €`**.*\n"
            f"• *Puis remonte ta sécurité au prix d'achat (**`{entry} $`**) : ton trade devient 100% gratuit sans aucun risque !*\n\n"
            f"**4️⃣ ÉTAPE 4 : OBJECTIF FINAL**\n"
            f"• Vends les 50% restants quand le cours touche **`{tp2} $`**.\n"
            f"• *Gain total dans ta poche : **`+{trade_params['total_projected_profit']} €`**.*"
        )

        embed = {
            "title": f"{'🟢' if is_long else '🔴'} CONSEIL DU BOT : {action_word} {symbol}",
            "description": description,
            "color": color,
            "footer": {
                "text": "Trade assisté • Respecte toujours la sécurité (Stop Loss)",
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        self._print_terminal_banner(trade_params)
        return self._send_raw_embed(embed)

    def send_tp1_hit(self, symbol: str, current_price: float, gain: float, is_long: bool = True):
        """Notification très claire du 1er objectif atteint."""
        crypto_name = symbol.split('/')[0]
        embed = {
            "title": f"💰 1er OBJECTIF VALIDÉ : {crypto_name} (+{gain:.2f} €)",
            "description": (
                f"Le cours vient d'atteindre **`{current_price} $`** comme prévu !\n\n"
                f"✅ **Ce qui s'est passé :**\n"
                f"• Tu as sécurisé la moitié de tes gains (**`+{gain:.2f} €`** déjà dans la poche).\n"
                f"• La sécurité a été déplacée au prix d'achat : **tu ne peux plus perdre le moindre centime sur ce trade (Risque Zéro)**.\n\n"
                f"👉 **Ce que tu dois faire :**\n"
                f"Rien du tout ! Laisse courir les 50% restants vers l'objectif final."
            ),
            "color": 0x10B981,
            "footer": {"text": "Objectif 1/2 validé • Position désormais sans risque"},
            "timestamp": datetime.utcnow().isoformat()
        }
        return self._send_raw_embed(embed)

    def send_tp2_hit(self, symbol: str, current_price: float, total_gain: float, capital: float, is_long: bool = True):
        """Notification très claire du trade 100% réussi."""
        crypto_name = symbol.split('/')[0]
        embed = {
            "title": f"🎉 TRADE 100% GAGNÉ : {crypto_name} (+{total_gain:.2f} €)",
            "description": (
                f"L'objectif final a été atteint à **`{current_price} $`** !\n\n"
                f"🏆 **Bilan du trade :**\n"
                f"• Gain total empoché : **`+{total_gain:.2f} €`** net.\n"
                f"• Nouveau capital total : **`{capital:.2f} €`**.\n\n"
                f"👉 **Ce que tu dois faire :**\n"
                f"Rien, le trade est totalement terminé et fermé avec succès. En attente du prochain signal !"
            ),
            "color": 0xF59E0B,
            "footer": {"text": "Succès complet • Capital sécurisé"},
            "timestamp": datetime.utcnow().isoformat()
        }
        return self._send_raw_embed(embed)

    def send_stop_loss_hit(self, symbol: str, current_price: float, loss: float, be_hit: bool = False):
        """Notification claire si la position est coupée."""
        crypto_name = symbol.split('/')[0]
        if be_hit:
            embed = {
                "title": f"🛡️ Trade Clôturé au Breakeven : {crypto_name}",
                "description": (
                    f"Le cours est revenu au niveau d'achat initial à **`{current_price} $`**.\n\n"
                    f"✅ **Bilan :**\n"
                    f"Grâce à la sécurité remontée après le premier objectif, **tu ne perds rien du tout** et tu as conservé les gains de la première étape !"
                ),
                "color": 0x3B82F6,
                "footer": {"text": "Protection du capital activée"},
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            embed = {
                "title": f"🛑 Sécurité Activée (Stop Loss) : {crypto_name} (-{loss:.2f} €)",
                "description": (
                    f"Le marché a tourné dans le mauvais sens et a touché la sécurité à **`{current_price} $`**.\n\n"
                    f"🛡️ **Ce qui s'est passé :**\n"
                    f"Le bot a coupé le trade automatiquement pour t'éviter une grosse chute.\n"
                    f"Perte strictement maîtrisée : **`-{loss:.2f} €`**.\n\n"
                    f"👉 **Ce que tu dois faire :**\n"
                    f"Rien, la perte fait partie normale du trading. Le système attend un nouveau setup propre pour repartir."
                ),
                "color": 0xEF4444,
                "footer": {"text": "Perte sous contrôle • Capital protégé"},
                "timestamp": datetime.utcnow().isoformat()
            }
        return self._send_raw_embed(embed)

    def send_kill_switch_alert(self, reason: str, drawdown_pct: float, capital: float):
        """Alerte rouge d'urgence si le Kill-Switch déterministe se déclenche."""
        embed = {
            "title": "🚨 VERROUILLAGE D'URGENCE (SÉCURITÉ MAXIMALE)",
            "description": (
                f"**Le bot a stoppé toutes les nouvelles prises de position.**\n\n"
                f"**Pourquoi ?**\n{reason}\n\n"
                f"**Capital actuel :** `{capital:.2f} €` (Baisse récente : `{drawdown_pct}%`)\n\n"
                f"👉 **Ce que ça veut dire :**\n"
                f"Le marché est trop dangereux ou a atteint la limite de perte autorisée. Le bot refuse d'ouvrir d'autres trades pour ne pas mettre ton compte en danger."
            ),
            "color": 0xFF0000,
            "footer": {"text": "Garde-fou automatique activé"},
            "timestamp": datetime.utcnow().isoformat()
        }
        self._send_raw_embed(embed)

    def send_overnight_review(self, metrics: Dict[str, Any]):
        """Envoie le bilan nocturne dans un format clair."""
        if metrics.get('status') != 'success':
            return

        embed = {
            "title": "🌙 Bilan du Soir : Vos Performances",
            "description": (
                f"Voici le résumé des trades analysés aujourd'hui :\n\n"
                f"• **Trades gagnants :** {metrics['wins']} / {metrics['total_trades_analyzed']} (Taux de réussite : **{metrics['win_rate_pct']}%**)\n"
                f"• **Bénéfice Net Total :** **`{metrics['total_pnl_eur']:+.2f} €`**\n"
                f"• **Qualité des prédictions (Brier Score) :** `{metrics['brier_score']}` (*{metrics['calibration_grade']}*)"
            ),
            "color": 0x6366F1,
            "footer": {"text": "Bilan automatique 24/7"},
            "timestamp": datetime.utcnow().isoformat()
        }
        self._send_raw_embed(embed)

    def send_status_message(self, title, message, color=0x3B82F6):
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
        print(f"🚨 [NOUVEAU SIGNAL] {p['direction']} sur {p['symbol']}")
        print(f"   Prix Entrée (Limit) : {p['entry_price']} $")
        print(f"   Stop Loss           : {p['sl_price']} $ (Perte max : -{p['risk_cash']} €)")
        print(f"   Take Profit 1       : {p['tp1_price']} $ (+{p.get('gain_tp1')} €)")
        print(f"   Take Profit 2       : {p['tp2_price']} $ (+{p['total_projected_profit']} €)")
        print("=" * 65 + "\n", flush=True)
