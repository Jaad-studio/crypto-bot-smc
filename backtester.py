"""
Module de Backtesting Historique Institutionnel.
Simule les règles Smart Money Concepts bar-par-bar sur les données réelles
avec un capital initial de 300 € pour valider mathématiquement l'avantage statistique (Edge).
"""

import pandas as pd
import numpy as np
import logging
from market_data import MarketDataProvider
from smc_engine import SMCEngine
from risk_engine import RiskEngine
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class SMCBacktester:
    def __init__(self, initial_capital=300.0, risk_percent=5.0):
        self.initial_capital = initial_capital
        self.risk_percent = risk_percent
        self.provider = MarketDataProvider(exchange_id=config.EXCHANGE_ID, exchange_type=config.EXCHANGE_TYPE)
        self.smc = SMCEngine(atr_multiplier=config.ATR_SL_MULTIPLIER)

    def run_backtest_for_symbol(self, symbol, limit_candles=1000):
        """
        Exécute le backtest sur un actif donné en simulant l'avancement chronologique.
        """
        logging.info(f"Chargement des données historiques pour {symbol} ({limit_candles} bougies 15m)...")
        df_15m = self.provider.fetch_ohlcv(symbol, timeframe='15m', limit=limit_candles)
        df_1h = self.provider.fetch_ohlcv(symbol, timeframe='1h', limit=min(500, limit_candles // 4))

        if df_15m is None or df_1h is None or len(df_15m) < 100:
            logging.error(f"Données insuffisantes pour backtester {symbol}")
            return None

        capital = self.initial_capital
        trades = []
        active_trade = None
        peak_capital = capital
        max_drawdown = 0.0

        # Simulation pas-à-pas sur les bougies 15m
        for i in range(50, len(df_15m)):
            current_bar = df_15m.iloc[i]
            window_15m = df_15m.iloc[:i+1]
            
            # Timestamp équivalent pour la tendance 1H
            bar_time = current_bar['timestamp']
            window_1h = df_1h[df_1h['timestamp'] <= bar_time]
            if len(window_1h) < 20:
                continue

            # 1. Gestion du trade actif si ouvert
            if active_trade:
                high = current_bar['high']
                low = current_bar['low']
                dir_ = active_trade['direction']
                sl = active_trade['sl']
                tp1 = active_trade['tp1']
                tp2 = active_trade['tp2']
                entry = active_trade['entry']
                risk_cash = active_trade['risk_cash']

                if dir_ == 'LONG':
                    # Vérification Stop Loss
                    if low <= sl:
                        if active_trade['tp1_hit']:
                            # Sortie au Breakeven sur les 50% restants
                            pnl = active_trade['tp1_gain']
                            outcome = 'BE_AFTER_TP1'
                        else:
                            pnl = -risk_cash
                            outcome = 'LOSS'

                        capital += pnl
                        trades.append({
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_time': active_trade['entry_time'],
                            'exit_time': current_bar['datetime'],
                            'entry': entry,
                            'exit': sl,
                            'pnl': round(pnl, 2),
                            'outcome': outcome,
                            'capital_after': round(capital, 2)
                        })
                        active_trade = None

                    # Vérification TP1
                    elif not active_trade['tp1_hit'] and high >= tp1:
                        active_trade['tp1_hit'] = True
                        active_trade['tp1_gain'] = 0.5 * active_trade['quantity'] * (tp1 - entry)
                        # Règle d'or : On remonte le Stop Loss au Breakeven !
                        active_trade['sl'] = entry

                    # Vérification TP2 final
                    elif active_trade['tp1_hit'] and high >= tp2:
                        pnl = active_trade['tp1_gain'] + (0.5 * active_trade['quantity'] * (tp2 - entry))
                        capital += pnl
                        trades.append({
                            'symbol': symbol,
                            'direction': 'LONG',
                            'entry_time': active_trade['entry_time'],
                            'exit_time': current_bar['datetime'],
                            'entry': entry,
                            'exit': tp2,
                            'pnl': round(pnl, 2),
                            'outcome': 'WIN_FULL',
                            'capital_after': round(capital, 2)
                        })
                        active_trade = None

                elif dir_ == 'SHORT':
                    # Vérification Stop Loss Short
                    if high >= sl:
                        if active_trade['tp1_hit']:
                            pnl = active_trade['tp1_gain']
                            outcome = 'BE_AFTER_TP1'
                        else:
                            pnl = -risk_cash
                            outcome = 'LOSS'

                        capital += pnl
                        trades.append({
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_time': active_trade['entry_time'],
                            'exit_time': current_bar['datetime'],
                            'entry': entry,
                            'exit': sl,
                            'pnl': round(pnl, 2),
                            'outcome': outcome,
                            'capital_after': round(capital, 2)
                        })
                        active_trade = None

                    # Vérification TP1 Short
                    elif not active_trade['tp1_hit'] and low <= tp1:
                        active_trade['tp1_hit'] = True
                        active_trade['tp1_gain'] = 0.5 * active_trade['quantity'] * (entry - tp1)
                        active_trade['sl'] = entry

                    # Vérification TP2 Short
                    elif active_trade['tp1_hit'] and low <= tp2:
                        pnl = active_trade['tp1_gain'] + (0.5 * active_trade['quantity'] * (entry - tp2))
                        capital += pnl
                        trades.append({
                            'symbol': symbol,
                            'direction': 'SHORT',
                            'entry_time': active_trade['entry_time'],
                            'exit_time': current_bar['datetime'],
                            'entry': entry,
                            'exit': tp2,
                            'pnl': round(pnl, 2),
                            'outcome': 'WIN_FULL',
                            'capital_after': round(capital, 2)
                        })
                        active_trade = None

                # Suivi Drawdown
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100.0 if peak_capital > 0 else 0
                if dd > max_drawdown:
                    max_drawdown = dd

                continue # On ne prend pas de nouveau trade si un trade est déjà en cours sur cette paire

            # 2. Recherche d'un nouveau setup SMC
            setup = self.smc.detect_setup(symbol, window_1h, window_15m, btc_dump_pct=0.0)
            if setup:
                risk_eng = RiskEngine(initial_capital=capital, risk_mode='percentage', risk_percent=self.risk_percent)
                params = risk_eng.compute_position_parameters(setup)

                if params and params['quantity'] > 0:
                    active_trade = {
                        'symbol': symbol,
                        'direction': params['direction'],
                        'entry': params['entry_price'],
                        'sl': params['sl_price'],
                        'tp1': params['tp1_price'],
                        'tp2': params['tp2_price'],
                        'quantity': params['quantity'],
                        'risk_cash': params['risk_cash'],
                        'tp1_hit': False,
                        'tp1_gain': 0.0,
                        'entry_time': current_bar['datetime']
                    }

        # Synthèse des résultats
        df_trades = pd.DataFrame(trades)
        total_trades = len(df_trades)
        wins = df_trades[df_trades['pnl'] > 0] if total_trades > 0 else pd.DataFrame()
        losses = df_trades[df_trades['pnl'] < 0] if total_trades > 0 else pd.DataFrame()

        win_count = len(wins)
        loss_count = len(losses)
        winrate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        net_profit = capital - self.initial_capital
        roi_pct = (net_profit / self.initial_capital) * 100.0

        report = {
            'symbol': symbol,
            'initial_capital': self.initial_capital,
            'final_capital': round(capital, 2),
            'net_profit': round(net_profit, 2),
            'roi_pct': round(roi_pct, 2),
            'total_trades': total_trades,
            'wins': win_count,
            'losses': loss_count,
            'winrate': round(winrate, 1),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown_pct': round(max_drawdown, 2),
            'trades_history': trades
        }

        return report

    def run_portfolio_backtest(self, symbols=None):
        """Lance le backtest complet sur l'ensemble du portefeuille."""
        if symbols is None:
            symbols = config.PAIRS

        print("\n" + "=" * 70)
        print(f"🔬 LANCEMENT DU BACKTEST HISTORIQUE QUANTITATIF (Capital: {self.initial_capital} €)")
        print(f"   Stratégie : Smart Money Concepts (FVG + Order Blocks + ATR SL + TP1/TP2)")
        print(f"   Risque par trade : {self.risk_percent} %")
        print("=" * 70)

        total_net_pnl = 0.0
        all_results = []

        for sym in symbols:
            res = self.run_backtest_for_symbol(sym, limit_candles=1000)
            if res:
                all_results.append(res)
                total_net_pnl += res['net_profit']
                print(f"\n📊 Résultats pour {sym} :")
                print(f"   - Capital Final  : {res['final_capital']} € ({'+' if res['net_profit']>=0 else ''}{res['net_profit']} € | {res['roi_pct']} %)")
                print(f"   - Total Trades   : {res['total_trades']} (Gagnants : {res['wins']} | Perdants : {res['losses']})")
                print(f"   - Taux de Réussite: {res['winrate']} %")
                print(f"   - Profit Factor  : {res['profit_factor']}")
                print(f"   - Max Drawdown   : {res['max_drawdown_pct']} %")

        print("\n" + "=" * 70)
        print(f"🏆 BILAN GLOBAL DU PORTEFEUILLE SUR LE CAPITAL DE {self.initial_capital} € :")
        print(f"   Gain Total Cumulé : {'+' if total_net_pnl>=0 else ''}{round(total_net_pnl, 2)} €")
        print(f"   Capital Total Théorique : {round(self.initial_capital + total_net_pnl, 2)} €")
        print("=" * 70 + "\n")

        return all_results

if __name__ == '__main__':
    backtester = SMCBacktester(initial_capital=config.INITIAL_CAPITAL, risk_percent=config.RISK_PERCENT)
    backtester.run_portfolio_backtest(['SOL/USDT', 'AVAX/USDT', 'INJ/USDT', 'BTC/USDT'])
