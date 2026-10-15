"""
Module de Suivi & Journalisation des Trades pour le Bot SMC Crypto.
Enregistre chaque signal émis, suit l'évolution des positions simulées
et calcule le compte-rendu de performance mensuel (Winrate, PnL en euros, etc.).
"""

import json
import os
import threading
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'trades_history.json')
_lock = threading.Lock()

class TradeTracker:
    def __init__(self, initial_capital=300.0):
        self.initial_capital = initial_capital
        self._load_history()

    def _load_history(self):
        with _lock:
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.trades = data.get('trades', [])
                except Exception:
                    self.trades = []
            else:
                self.trades = []
                self._save_history_unlocked()

    def _save_history_unlocked(self):
        data = {
            'initial_capital': self.initial_capital,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trades': self.trades
        }
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_new_signal(self, trade_params):
        """Enregistre un nouveau signal d'achat/vente détecté par l'algorithme."""
        symbol = trade_params['symbol']
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        month_str = now.strftime('%Y-%m')

        with _lock:
            # Vérifier si un trade actif existe déjà pour ce symbole
            for t in self.trades:
                if t['symbol'] == symbol and t['status'] == 'ACTIVE':
                    return t['id']

            trade_id = f"tr_{int(now.timestamp())}_{symbol.split('/')[0]}"
            new_trade = {
                'id': trade_id,
                'symbol': symbol,
                'direction': trade_params['direction'],
                'entry_price': trade_params['entry_price'],
                'sl_price': trade_params['sl_price'],
                'tp1_price': trade_params['tp1_price'],
                'tp2_price': trade_params['tp2_price'],
                'quantity': trade_params['quantity'],
                'risk_cash': trade_params['risk_cash'],
                'gain_tp1': trade_params['gain_tp1'],
                'gain_tp2': trade_params['gain_tp2'],
                'total_projected_profit': trade_params['total_projected_profit'],
                'leverage_recommended': trade_params.get('leverage_recommended', 1),
                'pattern': trade_params['pattern'],
                'entry_time': now_str,
                'month': month_str,
                'status': 'ACTIVE', # ACTIVE, WIN_TP1, WIN_TP2, CLOSED_BE, CLOSED_LOSS
                'outcome': 'EN COURS', # JUSTE (+X €), FAUX (-X €), EN COURS
                'exit_time': None,
                'exit_price': None,
                'pnl_eur': 0.0,
                'tp1_hit': False,
                'notes': f"Ordre d'entrée recommandé à {trade_params['entry_price']}$ sur zone institutionnelle {trade_params['pattern']}."
            }

            self.trades.insert(0, new_trade)
            self._save_history_unlocked()
            return trade_id

    def update_trade_progress(self, symbol, event_type, current_price, gain_loss_amount):
        """
        Met à jour le statut d'un trade :
        - 'TP1_HIT' : TP1 touché (+X € sécurisés, SL déplacé à BE)
        - 'TP2_HIT' : TP2 touché (+total gain, trade clôturé gagnant)
        - 'SL_BE_HIT' : Sorti au Breakeven après TP1
        - 'SL_LOSS_HIT' : Stop Loss touché (-15 € perte maîtrisée)
        """
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with _lock:
            for t in self.trades:
                if t['symbol'] == symbol and t['status'] in ['ACTIVE', 'TP1_HIT']:
                    if event_type == 'TP1_HIT':
                        t['status'] = 'TP1_HIT'
                        t['tp1_hit'] = True
                        t['pnl_eur'] = round(gain_loss_amount, 2)
                        t['outcome'] = f"TP1 SÉCURISÉ (+{gain_loss_amount:.2f} €)"
                        t['notes'] = f"TP1 atteint à {current_price}$ (+{gain_loss_amount:.2f} € sur 50%). Stop Loss déplacé au prix d'entrée (Breakeven)."

                    elif event_type == 'TP2_HIT':
                        t['status'] = 'WIN_TP2'
                        t['exit_time'] = now_str
                        t['exit_price'] = current_price
                        t['pnl_eur'] = round(gain_loss_amount, 2)
                        t['outcome'] = 'JUSTE (100% GAGNÉ)'
                        t['notes'] = f"TP2 Final atteint à {current_price}$ ! Gain total encaissé : +{gain_loss_amount:.2f} €."

                    elif event_type == 'SL_BE_HIT':
                        t['status'] = 'CLOSED_BE'
                        t['exit_time'] = now_str
                        t['exit_price'] = current_price
                        t['pnl_eur'] = round(gain_loss_amount, 2) # gain TP1 conservé
                        t['outcome'] = 'JUSTE (SÉCURISÉ AU BREAKEVEN)'
                        t['notes'] = f"Fermé au Breakeven après TP1. Gain final conservé : +{gain_loss_amount:.2f} €."

                    elif event_type == 'SL_LOSS_HIT':
                        t['status'] = 'CLOSED_LOSS'
                        t['exit_time'] = now_str
                        t['exit_price'] = current_price
                        t['pnl_eur'] = round(-abs(gain_loss_amount), 2)
                        t['outcome'] = 'FAUX (STOP LOSS)'
                        t['notes'] = f"Stop Loss touché à {current_price}$. Perte coupée proprement à -{abs(gain_loss_amount):.2f} €."

                    self._save_history_unlocked()
                    break

    def get_analytics(self):
        """Calcule les statistiques globales et mensuelles."""
        with _lock:
            trades = list(self.trades)

        total_signals = len(trades)
        closed_trades = [t for t in trades if t['status'] not in ['ACTIVE', 'TP1_HIT']]
        active_trades = [t for t in trades if t['status'] in ['ACTIVE', 'TP1_HIT']]

        total_pnl = sum(t['pnl_eur'] for t in trades)
        current_capital = self.initial_capital + total_pnl

        wins = [t for t in closed_trades if t['pnl_eur'] > 0]
        losses = [t for t in closed_trades if t['pnl_eur'] < 0]
        bes = [t for t in closed_trades if t['pnl_eur'] == 0]

        win_count = len(wins)
        loss_count = len(losses)
        decisive_trades = win_count + loss_count
        winrate = round((win_count / decisive_trades * 100.0), 1) if decisive_trades > 0 else 0.0

        # Ventilation par mois
        months = {}
        for t in trades:
            m = t.get('month', 'Autre')
            if m not in months:
                months[m] = {
                    'month': m,
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'pnl_eur': 0.0,
                }
            months[m]['total_trades'] += 1
            if t['status'] in ['WIN_TP2', 'CLOSED_BE'] or t['pnl_eur'] > 0:
                months[m]['wins'] += 1
            elif t['status'] == 'CLOSED_LOSS':
                months[m]['losses'] += 1
            months[m]['pnl_eur'] += t['pnl_eur']

        # Formatage du breakdown mensuel
        monthly_list = []
        for m_key in sorted(months.keys(), reverse=True):
            m_data = months[m_key]
            m_decisive = m_data['wins'] + m_data['losses']
            m_winrate = round((m_data['wins'] / m_decisive * 100.0), 1) if m_decisive > 0 else 0.0
            monthly_list.append({
                'month': m_key,
                'total_trades': m_data['total_trades'],
                'wins': m_data['wins'],
                'losses': m_data['losses'],
                'pnl_eur': round(m_data['pnl_eur'], 2),
                'winrate': m_winrate
            })

        return {
            'initial_capital': self.initial_capital,
            'current_capital': round(current_capital, 2),
            'total_pnl_eur': round(total_pnl, 2),
            'total_pnl_pct': round((total_pnl / self.initial_capital) * 100.0, 1),
            'total_signals': total_signals,
            'active_signals_count': len(active_trades),
            'closed_signals_count': len(closed_trades),
            'wins_count': win_count,
            'losses_count': loss_count,
            'winrate': winrate,
            'monthly_breakdown': monthly_list,
            'trades': trades
        }

# Instance globale
tracker = TradeTracker()
