"""
Lanceur Principal du Bot de Trading Quantitatif SMC (Smart Money Concepts).
Intègre l'architecture quantitative institutionnelle :
- Détection de Régime Macro (Trending, Mean-Reverting, High-Vol, Crisis)
- Risk Layer Déterministe & Hard Kill-Switch (Max Drawdown 15%)
- Dimensionnement Statistique Fractionnaire de Kelly (0.25x Kelly)
- Filtrage par Setup Quality (>= 2 / 3) et Confiance calibrée (>= 80%)
- Revue Nocturne & Calibration de Brier Score automatique
- Alertes enrichies sur Discord et Dashboard Web
"""

import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import logging
from datetime import datetime, date

import config
from market_data import MarketDataProvider
from smc_engine import SMCEngine
from risk_engine import RiskEngine
from regime_detector import MarketRegimeDetector
from overnight_review import OvernightReviewEngine
from discord_notifier import DiscordNotifier
from trade_tracker import tracker
from dashboard_template import render_dashboard_html

# Instances globales pour l'API HTTP
review_engine = OvernightReviewEngine()
latest_regime_info = {"regime": "initializing", "allow_trading": True}

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

        elif parsed_path == '/api/review':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            metrics = review_engine.compute_calibration_metrics()
            self.wfile.write(json.dumps(metrics, ensure_ascii=False).encode('utf-8'))

        elif parsed_path == '/api/regime':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(latest_regime_info, ensure_ascii=False).encode('utf-8'))

        elif parsed_path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "online", "bot": "SMC Quant Bot (Institutionnel)", "risk_layer": "deterministic"}')

        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html_content = render_dashboard_html()
            self.wfile.write(html_content.encode('utf-8'))

    def log_message(self, format, *args):
        pass

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
        self.smc = SMCEngine(atr_multiplier=config.ATR_SL_MULTIPLIER, allow_short=getattr(config, 'ALLOW_SHORT', False))
        
        # Risk Layer Déterministe
        self.risk = RiskEngine(
            initial_capital=config.INITIAL_CAPITAL,
            risk_mode=getattr(config, 'RISK_MODE', 'kelly'),
            risk_percent=getattr(config, 'RISK_PERCENT', 5.0),
            fixed_risk=getattr(config, 'FIXED_RISK_AMOUNT', 15.0),
            max_drawdown_pct=getattr(config, 'MAX_DRAWDOWN_LIMIT_PCT', 15.0),
            max_daily_loss_pct=getattr(config, 'MAX_DAILY_LOSS_LIMIT_PCT', 5.0),
            min_setup_quality=getattr(config, 'MIN_SETUP_QUALITY', 2.0),
            min_confidence=getattr(config, 'MIN_CONFIDENCE', 0.80)
        )

        self.regime_detector = MarketRegimeDetector(
            provider=self.provider,
            btc_crisis_threshold=getattr(config, 'BTC_DUMP_THRESHOLD_1H', -1.8)
        )
        self.notifier = DiscordNotifier(webhook_url=config.DISCORD_WEBHOOK_URL)
        self.review = review_engine

        # Positions actives en mémoire
        self.active_positions = {}
        self.capital = config.INITIAL_CAPITAL
        self.last_review_date = None

        # Restauration des positions actives depuis le journal
        analytics = tracker.get_analytics()
        for t in analytics.get('trades', []):
            if t['status'] in ['ACTIVE', 'TP1_HIT']:
                self.active_positions[t['symbol']] = {
                    'params': t,
                    'tp1_hit': t.get('tp1_hit', False),
                    'entry_time': t['entry_time']
                }

    def start(self):
        """Boucle principale d'analyse et d'exécution quantitative."""
        global latest_regime_info
        print("\n" + "=" * 75)
        print("🤖 DÉMARRAGE DU BOT QUANTITATIF SMC (ARCHITECTURE INSTITUTIONNELLE)")
        print(f"   Capital alloué       : {self.capital} €")
        print(f"   Mode Sizing          : {getattr(config, 'RISK_MODE', 'kelly').upper()} (Quarter-Kelly 0.25x)")
        print(f"   Garde-Fou Kill-Switch: Max Drawdown {config.MAX_DRAWDOWN_LIMIT_PCT}% (Déterministe)")
        print(f"   Filtres de Signal    : Qualité >= {config.MIN_SETUP_QUALITY}/3.0 & Confiance >= {int(config.MIN_CONFIDENCE*100)}%")
        print(f"   Paires surveillées   : {len(config.PAIRS)} paires ({', '.join(config.PAIRS[:4])}...)")
        print(f"   Dashboard Web        : Actif sur le port {os.environ.get('PORT', 8080)}")
        print(f"   Discord Webhook      : {'Configuré ✅' if config.DISCORD_WEBHOOK_URL else 'Mode Console ⚠️'}")
        print("=" * 75 + "\n")

        scan_count = 0

        while True:
            try:
                scan_count += 1
                now = datetime.now()
                now_str = now.strftime('%H:%M:%S')
                print(f"[{now_str}] 🔄 Scan #{scan_count} en cours...", flush=True)

                # 1. Mise à jour de la revue nocturne quotidienne (23h00 UTC ou après minuit)
                today = date.today()
                if self.last_review_date != today and now.hour >= 23:
                    self._run_overnight_review(today)

                # 2. Gestion des positions ouvertes (Paper Trading)
                self._update_open_positions()

                # 3. Évaluation du Régime Macro
                regime_snapshot = self.regime_detector.evaluate_regime('BTC/USDT')
                latest_regime_info = {
                    'regime': regime_snapshot.regime,
                    'allow_trading': regime_snapshot.allow_trading,
                    'btc_change_1h': regime_snapshot.btc_1h_change_pct,
                    'btc_price': regime_snapshot.btc_price,
                    'volatility_ratio': regime_snapshot.volatility_ratio,
                    'risk_state': regime_snapshot.risk_state,
                    'reason': regime_snapshot.reason
                }

                print(
                    f"[{now_str}] 🌐 Régime Macro : {regime_snapshot.regime.upper()} "
                    f"(BTC: {regime_snapshot.btc_price}$ | 1H: {regime_snapshot.btc_1h_change_pct:+.2f}% | "
                    f"Vol: {regime_snapshot.volatility_ratio:.2f}x) -> État Risque: {regime_snapshot.risk_state.upper()}",
                    flush=True
                )

                # 4. Vérification Hard Kill-Switch
                ks_status = self.risk.check_kill_switch()
                if not ks_status['is_armed_and_safe']:
                    logging.critical(f"🛑 [KILL-SWITCH ACTIF] {ks_status['reason']}. Nouvelles positions gelées.")
                    time.sleep(config.SCAN_INTERVAL_SECONDS)
                    continue

                # 5. Filtrage selon le Régime de Marché
                if not regime_snapshot.allow_trading:
                    logging.warning(
                        f"⚠️ [RÉGIME {regime_snapshot.regime.upper()}] Trading suspendu : {regime_snapshot.reason}"
                    )
                    time.sleep(config.SCAN_INTERVAL_SECONDS)
                    continue

                # 6. Analyse des Paires
                new_signals_count = 0
                for symbol in config.PAIRS:
                    if symbol in self.active_positions:
                        continue

                    df_15m = self.provider.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME_MICRO, limit=60)
                    df_1h = self.provider.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME_MACRO, limit=30)

                    if df_15m is None or df_1h is None:
                        continue

                    # Détection SMC avec scoring
                    setup = self.smc.detect_setup(
                        symbol,
                        df_1h,
                        df_15m,
                        btc_dump_pct=regime_snapshot.btc_1h_change_pct
                    )

                    if setup:
                        # Filtrage & Sizing via Risk Layer Déterministe
                        trade_params = self.risk.compute_position_parameters(setup)
                        if trade_params:
                            new_signals_count += 1
                            # Normalisation types natifs Python
                            clean_params = {}
                            for k, v in trade_params.items():
                                clean_params[k] = v.item() if hasattr(v, 'item') else v
                            trade_params = clean_params

                            # 1. Enregistrement Journal de Trading
                            tracker.record_new_signal(trade_params)

                            # 2. Notification Discord Enrichie
                            self.notifier.send_trade_signal(trade_params, latest_regime_info)

                            # 3. Suivi en mémoire
                            self.active_positions[symbol] = {
                                'params': trade_params,
                                'tp1_hit': False,
                                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }

                finish_str = datetime.now().strftime('%H:%M:%S')
                print(
                    f"[{finish_str}] ✅ Scan #{scan_count} terminé : {len(config.PAIRS)} paires analysées | "
                    f"Nouveaux signaux: {new_signals_count} | Positions actives: {len(self.active_positions)}. "
                    f"En veille ({config.SCAN_INTERVAL_SECONDS}s)...",
                    flush=True
                )
                time.sleep(config.SCAN_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                print("\nArrêt manuel du bot.")
                break
            except Exception as e:
                logging.error(f"Erreur inattendue dans la boucle principale : {e}")
                time.sleep(15)

    def _run_overnight_review(self, today):
        """Exécute la revue nocturne et transmet la calibration Brier Score sur Discord."""
        try:
            metrics = self.review.compute_calibration_metrics()
            if metrics.get('status') == 'success':
                logging.info(f"🌙 Revue nocturne calculée : Brier Score {metrics['brier_score']} ({metrics['calibration_grade']})")
                self.notifier.send_overnight_review(metrics)
            self.last_review_date = today
        except Exception as e:
            logging.error(f"Erreur lors de la revue nocturne : {e}")

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
                        self.capital += gain
                        self.risk.update_capital(self.capital)
                        tracker.update_trade_progress(symbol, 'SL_BE_HIT', curr_price, gain)
                        self.notifier.send_stop_loss_hit(symbol, curr_price, gain, be_hit=True)
                    else:
                        loss = p['risk_cash']
                        self.capital -= loss
                        self.risk.update_capital(self.capital)
                        tracker.update_trade_progress(symbol, 'SL_LOSS_HIT', curr_price, -loss)
                        self.notifier.send_stop_loss_hit(symbol, curr_price, loss, be_hit=False)
                    del self.active_positions[symbol]

                # TP1 touché
                elif not pos['tp1_hit'] and curr_price >= tp1:
                    pos['tp1_hit'] = True
                    p['sl_price'] = p['entry_price']
                    gain = p['gain_tp1']
                    self.capital += gain
                    self.risk.update_capital(self.capital)
                    tracker.update_trade_progress(symbol, 'TP1_HIT', curr_price, gain)
                    self.notifier.send_tp1_hit(symbol, curr_price, gain, is_long=True)

                # TP2 final touché
                elif pos['tp1_hit'] and curr_price >= tp2:
                    gain_tp2 = p['gain_tp2']
                    self.capital += gain_tp2
                    self.risk.update_capital(self.capital)
                    total_gain = p['total_projected_profit']
                    tracker.update_trade_progress(symbol, 'TP2_HIT', curr_price, total_gain)
                    self.notifier.send_tp2_hit(symbol, curr_price, total_gain, self.capital, is_long=True)
                    del self.active_positions[symbol]

            elif direction == 'SHORT':
                # Stop Loss touché (prix monte)
                if curr_price >= sl:
                    if pos['tp1_hit']:
                        gain = p['gain_tp1']
                        self.capital += gain
                        self.risk.update_capital(self.capital)
                        tracker.update_trade_progress(symbol, 'SL_BE_HIT', curr_price, gain)
                        self.notifier.send_stop_loss_hit(symbol, curr_price, gain, be_hit=True)
                    else:
                        loss = p['risk_cash']
                        self.capital -= loss
                        self.risk.update_capital(self.capital)
                        tracker.update_trade_progress(symbol, 'SL_LOSS_HIT', curr_price, -loss)
                        self.notifier.send_stop_loss_hit(symbol, curr_price, loss, be_hit=False)
                    del self.active_positions[symbol]

                # TP1 touché (prix baisse)
                elif not pos['tp1_hit'] and curr_price <= tp1:
                    pos['tp1_hit'] = True
                    p['sl_price'] = p['entry_price']
                    gain = p['gain_tp1']
                    self.capital += gain
                    self.risk.update_capital(self.capital)
                    tracker.update_trade_progress(symbol, 'TP1_HIT', curr_price, gain)
                    self.notifier.send_tp1_hit(symbol, curr_price, gain, is_long=False)

                # TP2 final touché (prix baisse)
                elif pos['tp1_hit'] and curr_price <= tp2:
                    gain_tp2 = p['gain_tp2']
                    self.capital += gain_tp2
                    self.risk.update_capital(self.capital)
                    total_gain = p['total_projected_profit']
                    tracker.update_trade_progress(symbol, 'TP2_HIT', curr_price, total_gain)
                    self.notifier.send_tp2_hit(symbol, curr_price, total_gain, self.capital, is_long=False)
                    del self.active_positions[symbol]

if __name__ == '__main__':
    http_thread = threading.Thread(target=start_health_server, daemon=True)
    http_thread.start()
    logging.info(f"Serveur Web & API de Calibration sur le port {os.environ.get('PORT', 8080)}")

    runner = SMCBotRunner()
    runner.start()
