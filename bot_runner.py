"""
Lanceur Principal du Bot de Trading Quantitatif SMC (Smart Money Concepts).
Surveille en continu les marchés, détecte les anomalies de liquidité FVG/OB,
gère les positions simulées (Paper Trading), envoie les ordres sur Discord
et héberge le Journal de Trading & Bilan de Performance Web en direct.
"""

import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import logging
from datetime import datetime

import config
from market_data import MarketDataProvider
from smc_engine import SMCEngine
from risk_engine import RiskEngine
from discord_notifier import DiscordNotifier
from trade_tracker import tracker
from dashboard_template import render_dashboard_html

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = self.path.split('?')[0]

        if parsed_path in ['/api/stats', '/api/trades']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            analytics = tracker.get_analytics()
            self.wfile.write(json.dumps(analytics, ensure_ascii=False).encode('utf-8'))

        elif parsed_path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "online", "bot": "SMC Quant Bot", "message": "Bot is scanning markets 24/7"}')

        else:
            # Servir le Dashboard Web complet
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html_content = render_dashboard_html()
            self.wfile.write(html_content.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress access logs

def start_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

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

        # Restauration des positions actives depuis le journal si redémarrage
        analytics = tracker.get_analytics()
        for t in analytics.get('trades', []):
            if t['status'] in ['ACTIVE', 'TP1_HIT']:
                self.active_positions[t['symbol']] = {
                    'params': t,
                    'tp1_hit': t.get('tp1_hit', False),
                    'entry_time': t['entry_time']
                }

    def start(self):
        """Boucle principale d'analyse et de trading."""
        print("\n" + "=" * 70)
        print("🤖 DÉMARRAGE DU BOT QUANTITATIF SMC CRYPTO (AVEC JOURNAL WEB)")
        print(f"   Capital alloué   : {self.capital} €")
        print(f"   Risque par trade : {config.RISK_PERCENT}% ({self.risk.calculate_risk_amount()} € max)")
        print(f"   Paires surveillées: {len(config.PAIRS)} paires ({', '.join(config.PAIRS[:5])}...)")
        print(f"   Timeframes       : {config.TIMEFRAME_MACRO} (Macro) & {config.TIMEFRAME_MICRO} (Anomalies)")
        print(f"   Dashboard Web    : Actif sur le port {os.environ.get('PORT', 8080)}")
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
                            # 1. Enregistrement dans le Journal de Trading Tracker
                            tracker.record_new_signal(trade_params)

                            # 2. Envoi sur Discord & Console
                            self.notifier.send_trade_signal(trade_params)

                            # 3. Enregistrement en mémoire
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
                        tracker.update_trade_progress(symbol, 'SL_BE_HIT', curr_price, gain)
                        msg = f"🛡️ Position {symbol} fermée au Breakeven après TP1. Gain final sécurisé : +{gain} €."
                    else:
                        loss = p['risk_cash']
                        self.capital -= loss
                        tracker.update_trade_progress(symbol, 'SL_LOSS_HIT', curr_price, loss)
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
                    tracker.update_trade_progress(symbol, 'TP1_HIT', curr_price, gain)
                    msg = f"🎯 TP1 ATTEINT sur {symbol} à {curr_price}$ ! (+{gain} € sécurisés sur 50%). Stop Loss déplacé au Breakeven ({p['entry_price']}$)."
                    logging.info(msg)
                    self.notifier.send_status_message(f"🎯 TP1 Atteint : {symbol}", msg, color=0x10B981)

                # TP2 final touché
                elif pos['tp1_hit'] and curr_price >= tp2:
                    gain_tp2 = p['gain_tp2']
                    self.capital += gain_tp2
                    total_gain = p['total_projected_profit']
                    tracker.update_trade_progress(symbol, 'TP2_HIT', curr_price, total_gain)
                    msg = f"🚀 TP2 FINAL ATTEINT sur {symbol} à {curr_price}$ ! Gain total du trade : +{total_gain} €. Capital actuel : {self.capital:.2f} €."
                    logging.info(msg)
                    self.notifier.send_status_message(f"🏆 TP2 Final Validé : {symbol}", msg, color=0xF59E0B)
                    del self.active_positions[symbol]

if __name__ == '__main__':
    # Démarre le serveur HTTP du Dashboard Web & Healthcheck
    http_thread = threading.Thread(target=start_health_server, daemon=True)
    http_thread.start()
    logging.info(f"Serveur Web & Journal de Trading en écoute sur le port {os.environ.get('PORT', 8080)} (Render)")

    runner = SMCBotRunner()
    runner.start()
