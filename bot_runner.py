"""
Lanceur Principal du Bot de Trading Quantitatif SMC (Smart Money Concepts).
Surveille en continu les marchés, détecte les anomalies de liquidité FVG/OB,
gère les positions simulées (Paper Trading) et envoie les ordres sur Discord.
"""

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import logging
from datetime import datetime

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "online", "bot": "SMC Quant Bot", "message": "Bot is scanning markets 24/7"}')

    def log_message(self, format, *args):
        pass  # Suppress access logs

def start_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

import config
from market_data import MarketDataProvider
from smc_engine import SMCEngine
from risk_engine import RiskEngine
from discord_notifier import DiscordNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class SMCBotRunner:
    def __init__(self):
        self.provider = MarketDataProvider(exchange_id=config.EXCHANGE_ID, exchange_type=config.EXCHANGE_TYPE)
        self.smc = SMCEngine(atr_multiplier=config.ATR_SL_MULTIPLIER)
        self.risk = RiskEngine(
            initial_capital=config.INITIAL_CAPITAL,
            risk_mode=config.RISK_MODE,
            risk_percent=config.RISK_PERCENT,
            fixed_risk=config.FIXED_RISK_AMOUNT
        )
        self.notifier = DiscordNotifier(webhook_url=config.DISCORD_WEBHOOK_URL)
        
        # Positions actives en mémoire pour le suivi Paper Trading
        self.active_positions = {}
        self.capital = config.INITIAL_CAPITAL

    def start(self):
        """Boucle principale d'analyse et de trading."""
        print("\n" + "=" * 70)
        print("🤖 DÉMARRAGE DU BOT QUANTITATIF SMC CRYPTO")
        print(f"   Capital alloué   : {self.capital} €")
        print(f"   Risque par trade : {config.RISK_PERCENT}% ({self.risk.calculate_risk_amount()} € max)")
        print(f"   Paires surveillées: {', '.join(config.PAIRS)}")
        print(f"   Timeframes       : {config.TIMEFRAME_MACRO} (Macro) & {config.TIMEFRAME_MICRO} (Anomalies)")
        print(f"   Discord Webhook  : {'Configuré ✅' if config.DISCORD_WEBHOOK_URL else 'Mode Console (aucun webhook) ⚠️'}")
        print("=" * 70 + "\n")

        scan_count = 0

        while True:
            try:
                scan_count += 1
                now_str = datetime.now().strftime('%H:%M:%S')
                print(f"[{now_str}] 🔄 Scan #{scan_count} en cours...")

                # 1. Vérification Filtre Parapluie Bitcoin
                btc_dump_pct, btc_price = self.provider.get_btc_macro_status('BTC/USDT')
                if btc_dump_pct <= config.BTC_DUMP_THRESHOLD_1H:
                    logging.warning(f"🚨 ALERTE PARAPLUIE BTC : Chute de {btc_dump_pct:.2f}% en 1H (BTC: {btc_price}$). Aucun Long autorisé.")

                # 2. Gestion des positions ouvertes (Paper Trading)
                self._update_open_positions()

                # 3. Analyse des paires configurées
                for symbol in config.PAIRS:
                    # Ne pas ouvrir un 2ème trade sur la même paire
                    if symbol in self.active_positions:
                        continue

                    df_15m = self.provider.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME_MICRO, limit=60)
                    df_1h = self.provider.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME_MACRO, limit=30)

                    if df_15m is None or df_1h is None:
                        continue

                    # Détection SMC
                    setup = self.smc.detect_setup(symbol, df_1h, df_15m, btc_dump_pct=btc_dump_pct)
                    if setup:
                        # Calcul Risk Management
                        trade_params = self.risk.compute_position_parameters(setup)
                        if trade_params:
                            # Envoi sur Discord & Console
                            self.notifier.send_trade_signal(trade_params)

                            # Enregistrement en mémoire
                            self.active_positions[symbol] = {
                                'params': trade_params,
                                'tp1_hit': False,
                                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }

                time.sleep(config.SCAN_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                print("\nArrêt manuel du bot.")
                break
            except Exception as e:
                logging.error(f"Erreur inattendue dans la boucle principale : {e}")
                time.sleep(15)

    def _update_open_positions(self):
        """Vérifie si les positions ouvertes ont touché TP1, TP2 ou le Stop Loss."""
        for symbol, pos in list(self.active_positions.items()):
            p = pos['params']
            curr_price = self.provider.get_current_price(symbol)
            if not curr_price:
                continue

            direction = p['direction']
            sl = p['sl_price']
            tp1 = p['tp1_price']
            tp2 = p['tp2_price']

            if direction == 'LONG':
                # Stop Loss touché
                if curr_price <= sl:
                    if pos['tp1_hit']:
                        gain = p['gain_tp1']
                        msg = f"🛡️ Position {symbol} fermée au Breakeven après TP1. Gain final sécurisé : +{gain} €."
                    else:
                        loss = p['risk_cash']
                        self.capital -= loss
                        msg = f"🛑 Stop Loss touché sur {symbol} à {curr_price}$. Perte maîtrisée : -{loss} €."

                    logging.info(msg)
                    self.notifier.send_status_message(f"Sortie de position : {symbol}", msg, color=0xEF4444)
                    del self.active_positions[symbol]

                # TP1 touché
                elif not pos['tp1_hit'] and curr_price >= tp1:
                    pos['tp1_hit'] = True
                    p['sl_price'] = p['entry_price'] # SL déplacé au Breakeven
                    gain = p['gain_tp1']
                    self.capital += gain
                    msg = f"🎯 TP1 ATTEINT sur {symbol} à {curr_price}$ ! (+{gain} € sécurisés sur 50%). Stop Loss déplacé au Breakeven ({p['entry_price']}$)."
                    logging.info(msg)
                    self.notifier.send_status_message(f"🎯 TP1 Atteint : {symbol}", msg, color=0x10B981)

                # TP2 final touché
                elif pos['tp1_hit'] and curr_price >= tp2:
                    gain_tp2 = p['gain_tp2']
                    self.capital += gain_tp2
                    total_gain = p['total_projected_profit']
                    msg = f"🚀 TP2 FINAL ATTEINT sur {symbol} à {curr_price}$ ! Gain total du trade : +{total_gain} €. Capital actuel : {self.capital:.2f} €."
                    logging.info(msg)
                    self.notifier.send_status_message(f"🏆 TP2 Final Validé : {symbol}", msg, color=0xF59E0B)
                    del self.active_positions[symbol]

if __name__ == '__main__':
    # Démarre le serveur HTTP pour compatibilité Cloud Render (Free Web Service)
    http_thread = threading.Thread(target=start_health_server, daemon=True)
    http_thread.start()
    logging.info(f"Serveur HTTP de santé en écoute sur le port {os.environ.get('PORT', 8080)} (Render)")

    runner = SMCBotRunner()
    runner.start()
