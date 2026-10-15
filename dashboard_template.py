"""
Générateur du Dashboard Web & Journal de Trading SMC Quant.
Interface moderne dark-mode réactive accessible sur mobile et ordinateur.
"""

def render_dashboard_html():
    return """<!DOCTYPE html>
<html lang="fr" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>SMC Quant Bot • Journal & Bilan de Trading</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Font Awesome / Lucide Icons CDN -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: {
              50: '#f0fdf4',
              500: '#10b981',
              600: '#059669',
            }
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #0B0F19;
      color: #E2E8F0;
    }
    .glass-card {
      background: rgba(17, 24, 39, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .badge-long {
      background: rgba(16, 185, 129, 0.15);
      color: #34D399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-short {
      background: rgba(239, 68, 68, 0.15);
      color: #F87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: rgba(15, 23, 42, 0.6);
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: rgba(100, 116, 139, 0.5);
      border-radius: 9999px;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col font-sans antialiased selection:bg-emerald-500 selection:text-white">

  <!-- Top Bar -->
  <header class="border-b border-slate-800 bg-[#0E1322]/90 backdrop-blur-md sticky top-0 z-30">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <i class="fa-solid fa-chart-line text-white text-lg"></i>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base sm:text-lg font-bold text-white tracking-tight">SMC Quant Bot</h1>
            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              24/7 Cloud
            </span>
          </div>
          <p class="text-xs text-slate-400 hidden sm:block">Journal des Alertes & Compte-rendu de Performance</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <button onclick="refreshData()" class="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition-all flex items-center gap-2 active:scale-95">
          <i id="refresh-icon" class="fa-solid fa-arrows-rotate text-emerald-400"></i>
          <span class="hidden sm:inline">Actualiser</span>
        </button>
        <a href="https://discord.com" target="_blank" class="px-3 py-1.5 rounded-lg bg-[#5865F2]/20 hover:bg-[#5865F2]/30 text-xs font-semibold text-[#8EA1E1] border border-[#5865F2]/30 flex items-center gap-1.5 transition-all">
          <i class="fa-brands fa-discord"></i>
          <span class="hidden sm:inline">Discord</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 w-full flex-1 space-y-6">

    <!-- KPI Section: "Si j'avais suivi à chaque mouvement..." -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      
      <!-- Capital Actuel -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Capital Théorique</span>
          <i class="fa-solid fa-wallet text-emerald-400 text-sm"></i>
        </div>
        <div>
          <div id="stat-capital" class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white font-mono tracking-tight">300.00 €</div>
          <div class="flex items-center gap-1.5 mt-1">
            <span id="stat-pnl-pct" class="text-xs font-bold text-emerald-400 font-mono">+0.0%</span>
            <span class="text-[11px] text-slate-500">depuis 300 €</span>
          </div>
        </div>
      </div>

      <!-- Gain Net Cumulé -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Gain Net Cumulé</span>
          <i class="fa-solid fa-money-bill-trend-up text-emerald-400 text-sm"></i>
        </div>
        <div>
          <div id="stat-pnl-eur" class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-emerald-400 font-mono tracking-tight">+0.00 €</div>
          <p class="text-[11px] text-slate-400 mt-1">Si chaque ordre a été exécuté</p>
        </div>
      </div>

      <!-- Taux de Réussite (Juste vs Faux) -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Taux de Réussite</span>
          <i class="fa-solid fa-bullseye text-teal-400 text-sm"></i>
        </div>
        <div>
          <div id="stat-winrate" class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white font-mono tracking-tight">0.0%</div>
          <div class="flex items-center gap-2 mt-1 text-[11px]">
            <span class="text-emerald-400 font-semibold"><span id="stat-wins">0</span> Justes ✅</span>
            <span class="text-slate-600">•</span>
            <span class="text-rose-400 font-semibold"><span id="stat-losses">0</span> Faux ❌</span>
          </div>
        </div>
      </div>

      <!-- Signaux Actifs -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
          <span>Positions en cours</span>
          <i class="fa-solid fa-hourglass-half text-amber-400 text-sm"></i>
        </div>
        <div>
          <div id="stat-active" class="text-xl sm:text-2xl lg:text-3xl font-extrabold text-amber-400 font-mono tracking-tight">0</div>
          <p class="text-[11px] text-slate-400 mt-1">Sur 22 paires surveillées</p>
        </div>
      </div>

    </div>

    <!-- Monthly Report Cards & Filter -->
    <div class="glass-card rounded-2xl p-4 sm:p-6 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h2 class="text-base sm:text-lg font-bold text-white flex items-center gap-2">
            <i class="fa-regular fa-calendar-days text-emerald-400"></i>
            Compte-rendu Mensuel & Bilan
          </h2>
          <p class="text-xs text-slate-400">Sélectionnez un mois pour voir le détail de ce que le bot vous a conseillé</p>
        </div>

        <!-- Month Filter Tabs -->
        <div id="months-tabs" class="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 custom-scrollbar">
          <button onclick="filterByMonth('ALL')" class="month-tab px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-white shadow-sm transition-all" data-month="ALL">
            Tous les mois
          </button>
        </div>
      </div>

      <!-- Monthly Summary Highlight -->
      <div id="month-highlight" class="bg-slate-900/60 rounded-xl p-3 sm:p-4 border border-slate-800/80 flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <i class="fa-solid fa-calendar-check"></i>
          </div>
          <div>
            <div id="highlight-month-name" class="text-sm font-bold text-white">Bilan Global Cumulé</div>
            <div id="highlight-trades-count" class="text-xs text-slate-400">0 alertes enregistrées</div>
          </div>
        </div>

        <div class="flex items-center gap-4 sm:gap-6 font-mono">
          <div>
            <span class="text-[10px] uppercase text-slate-500 block">Réussite</span>
            <span id="highlight-winrate" class="text-sm font-bold text-white">0%</span>
          </div>
          <div>
            <span class="text-[10px] uppercase text-slate-500 block">Gain / Perte</span>
            <span id="highlight-pnl" class="text-sm sm:text-base font-bold text-emerald-400">+0.00 €</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Trades Journal Section -->
    <div class="glass-card rounded-2xl overflow-hidden space-y-0">
      
      <!-- Table Header / Filters -->
      <div class="p-4 sm:p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/30">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-list-check text-emerald-400"></i>
            Journal Détaillé des Alertes
          </h3>
          <p class="text-xs text-slate-400">Historique pas-à-pas : ce qu'il a dit de faire vs le résultat marché</p>
        </div>

        <!-- Status Filter Buttons -->
        <div class="flex items-center gap-1.5 overflow-x-auto custom-scrollbar">
          <button onclick="filterByStatus('ALL')" class="status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 text-slate-200 border border-slate-700" data-status="ALL">Tous</button>
          <button onclick="filterByStatus('WIN')" class="status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-400 hover:text-slate-200" data-status="WIN">✅ Justes</button>
          <button onclick="filterByStatus('LOSS')" class="status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-400 hover:text-slate-200" data-status="LOSS">❌ Faux</button>
          <button onclick="filterByStatus('ACTIVE')" class="status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-400 hover:text-slate-200" data-status="ACTIVE">🔄 En cours</button>
        </div>
      </div>

      <!-- Trade List Container -->
      <div id="trades-container" class="divide-y divide-slate-800/80">
        <!-- Rendered dynamically -->
        <div class="p-12 text-center text-slate-500 text-xs">
          <i class="fa-solid fa-circle-notch fa-spin text-lg mb-2 text-emerald-400"></i>
          <p>Chargement des alertes...</p>
        </div>
      </div>

    </div>

  </main>

  <!-- Footer -->
  <footer class="mt-auto border-t border-slate-800/80 py-4 text-center text-xs text-slate-500">
    <div class="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
      <p>SMC Quant Algorithm • Suivi automatisé en direct</p>
      <p class="text-[11px] text-slate-600">Actualisation automatique toutes les 30 secondes</p>
    </div>
  </footer>

  <!-- Script logic -->
  <script>
    let globalData = null;
    let selectedMonth = 'ALL';
    let selectedStatus = 'ALL';

    async function loadData() {
      try {
        const res = await fetch('/api/stats');
        if (res.ok) {
          globalData = await res.json();
          renderUI();
        }
      } catch (err) {
        console.error('Erreur chargement stats:', err);
      }
    }

    function refreshData() {
      const icon = document.getElementById('refresh-icon');
      if (icon) icon.classList.add('fa-spin');
      loadData().finally(() => {
        setTimeout(() => {
          if (icon) icon.classList.remove('fa-spin');
        }, 500);
      });
    }

    function filterByMonth(m) {
      selectedMonth = m;
      document.querySelectorAll('.month-tab').forEach(b => {
        if (b.dataset.month === m) {
          b.className = 'month-tab px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-white shadow-sm transition-all';
        } else {
          b.className = 'month-tab px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800/90 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-all';
        }
      });
      renderUI();
    }

    function filterByStatus(s) {
      selectedStatus = s;
      document.querySelectorAll('.status-filter-btn').forEach(b => {
        if (b.dataset.status === s) {
          b.className = 'status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-800 text-white border border-slate-700';
        } else {
          b.className = 'status-filter-btn px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-400 hover:text-slate-200';
        }
      });
      renderUI();
    }

    function renderUI() {
      if (!globalData) return;

      // 1. Top KPIs
      const pnl = globalData.total_pnl_eur;
      const isPositive = pnl >= 0;
      document.getElementById('stat-capital').textContent = globalData.current_capital.toFixed(2) + ' €';
      
      const pnlPctEl = document.getElementById('stat-pnl-pct');
      pnlPctEl.textContent = (isPositive ? '+' : '') + globalData.total_pnl_pct.toFixed(1) + '%';
      pnlPctEl.className = 'text-xs font-bold font-mono ' + (isPositive ? 'text-emerald-400' : 'text-rose-400');

      const pnlEurEl = document.getElementById('stat-pnl-eur');
      pnlEurEl.textContent = (isPositive ? '+' : '') + pnl.toFixed(2) + ' €';
      pnlEurEl.className = 'text-xl sm:text-2xl lg:text-3xl font-extrabold font-mono tracking-tight ' + (isPositive ? 'text-emerald-400' : 'text-rose-400');

      document.getElementById('stat-winrate').textContent = globalData.winrate.toFixed(1) + '%';
      document.getElementById('stat-wins').textContent = globalData.wins_count;
      document.getElementById('stat-losses').textContent = globalData.losses_count;
      document.getElementById('stat-active').textContent = globalData.active_signals_count;

      // 2. Render Months Tabs if not already populated
      const monthsContainer = document.getElementById('months-tabs');
      const currentTabs = Array.from(monthsContainer.querySelectorAll('.month-tab')).map(b => b.dataset.month);
      
      globalData.monthly_breakdown.forEach(mb => {
        if (!currentTabs.includes(mb.month)) {
          const btn = document.createElement('button');
          btn.dataset.month = mb.month;
          btn.onclick = () => filterByMonth(mb.month);
          btn.className = 'month-tab px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800/90 text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-all whitespace-nowrap';
          btn.textContent = mb.month;
          monthsContainer.appendChild(btn);
        }
      });

      // 3. Update Monthly Highlight
      let filteredMonthly = null;
      if (selectedMonth === 'ALL') {
        document.getElementById('highlight-month-name').textContent = 'Bilan Global (Tous les mois)';
        document.getElementById('highlight-trades-count').textContent = globalData.total_signals + ' alertes au total (' + globalData.closed_signals_count + ' clôturées)';
        document.getElementById('highlight-winrate').textContent = globalData.winrate.toFixed(1) + '%';
        const hlPnl = document.getElementById('highlight-pnl');
        hlPnl.textContent = (isPositive ? '+' : '') + pnl.toFixed(2) + ' €';
        hlPnl.className = 'text-sm sm:text-base font-bold font-mono ' + (isPositive ? 'text-emerald-400' : 'text-rose-400');
      } else {
        filteredMonthly = globalData.monthly_breakdown.find(m => m.month === selectedMonth);
        if (filteredMonthly) {
          const mPnl = filteredMonthly.pnl_eur;
          const mPos = mPnl >= 0;
          document.getElementById('highlight-month-name').textContent = 'Bilan de ' + filteredMonthly.month;
          document.getElementById('highlight-trades-count').textContent = filteredMonthly.total_trades + ' alertes (' + filteredMonthly.wins + ' gagnées, ' + filteredMonthly.losses + ' perdues)';
          document.getElementById('highlight-winrate').textContent = filteredMonthly.winrate.toFixed(1) + '%';
          const hlPnl = document.getElementById('highlight-pnl');
          hlPnl.textContent = (mPos ? '+' : '') + mPnl.toFixed(2) + ' €';
          hlPnl.className = 'text-sm sm:text-base font-bold font-mono ' + (mPos ? 'text-emerald-400' : 'text-rose-400');
        }
      }

      // 4. Filter & Render Trades
      const container = document.getElementById('trades-container');
      container.innerHTML = '';

      let trades = globalData.trades || [];

      // Filter by Month
      if (selectedMonth !== 'ALL') {
        trades = trades.filter(t => t.month === selectedMonth);
      }

      // Filter by Status
      if (selectedStatus === 'WIN') {
        trades = trades.filter(t => t.status === 'WIN_TP2' || t.status === 'CLOSED_BE' || t.pnl_eur > 0);
      } else if (selectedStatus === 'LOSS') {
        trades = trades.filter(t => t.status === 'CLOSED_LOSS');
      } else if (selectedStatus === 'ACTIVE') {
        trades = trades.filter(t => t.status === 'ACTIVE' || t.status === 'TP1_HIT');
      }

      if (trades.length === 0) {
        container.innerHTML = `
          <div class="py-16 text-center text-slate-500">
            <i class="fa-solid fa-inbox text-3xl mb-3 text-slate-600 block"></i>
            <p class="font-medium text-sm">Aucune alerte enregistrée pour ces critères.</p>
            <p class="text-xs text-slate-600 mt-1">Le bot analyse les 22 paires 24h/24 et enregistrera ici chaque signal.</p>
          </div>
        `;
        return;
      }

      trades.forEach(t => {
        const isWin = t.status === 'WIN_TP2' || t.status === 'CLOSED_BE' || t.pnl_eur > 0;
        const isLoss = t.status === 'CLOSED_LOSS';
        const isActive = t.status === 'ACTIVE' || t.status === 'TP1_HIT';

        let outcomeBadge = '';
        let pnlColor = 'text-slate-400';
        let pnlText = '0.00 €';

        if (isActive) {
          if (t.status === 'TP1_HIT') {
            outcomeBadge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">🎯 TP1 Atteint (+'+t.pnl_eur.toFixed(2)+' €)</span>';
            pnlColor = 'text-emerald-400';
            pnlText = '+' + t.pnl_eur.toFixed(2) + ' € (sécurisé)';
          } else {
            outcomeBadge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse"><i class="fa-solid fa-spinner fa-spin text-[10px]"></i> En Cours</span>';
            pnlColor = 'text-amber-400';
            pnlText = 'En cours...';
          }
        } else if (isWin) {
          outcomeBadge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✅ JUSTE ('+t.outcome+')</span>';
          pnlColor = 'text-emerald-400';
          pnlText = '+' + t.pnl_eur.toFixed(2) + ' €';
        } else if (isLoss) {
          outcomeBadge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">❌ FAUX (Stop Loss)</span>';
          pnlColor = 'text-rose-400';
          pnlText = '-' + Math.abs(t.pnl_eur).toFixed(2) + ' €';
        }

        const isLong = t.direction === 'LONG';
        const dirBadge = isLong 
          ? '<span class="px-2 py-0.5 rounded text-[11px] font-bold badge-long">LONG ↗</span>'
          : '<span class="px-2 py-0.5 rounded text-[11px] font-bold badge-short">SHORT ↘</span>';

        const row = document.createElement('div');
        row.className = 'p-4 sm:p-5 hover:bg-slate-800/30 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-4';
        row.innerHTML = `
          <!-- Left: Crypto Info & Ce que le bot a dit -->
          <div class="space-y-2 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-base font-bold text-white tracking-wide">${t.symbol}</span>
              ${dirBadge}
              <span class="text-xs text-slate-500 font-mono">• ${t.entry_time}</span>
              <div class="ml-auto lg:hidden">${outcomeBadge}</div>
            </div>

            <!-- Ce que le bot a conseillé de faire -->
            <div class="bg-slate-900/80 rounded-xl p-3 border border-slate-800/80 text-xs space-y-1.5">
              <div class="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                <i class="fa-solid fa-bullhorn text-emerald-400"></i>
                <span>Ordre conseillé :</span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                <div class="bg-slate-800/60 p-1.5 rounded">
                  <span class="text-slate-500 block text-[10px]">Entrée Limit</span>
                  <span class="text-white font-bold">${t.entry_price}$</span>
                </div>
                <div class="bg-slate-800/60 p-1.5 rounded">
                  <span class="text-slate-500 block text-[10px]">Stop Loss</span>
                  <span class="text-rose-400 font-bold">${t.sl_price}$</span>
                </div>
                <div class="bg-slate-800/60 p-1.5 rounded">
                  <span class="text-slate-500 block text-[10px]">Take Profit 1</span>
                  <span class="text-emerald-400 font-bold">${t.tp1_price}$</span>
                </div>
                <div class="bg-slate-800/60 p-1.5 rounded">
                  <span class="text-slate-500 block text-[10px]">Take Profit 2</span>
                  <span class="text-amber-400 font-bold">${t.tp2_price}$</span>
                </div>
              </div>
              <p class="text-slate-400 text-[11px] pt-1 italic">
                <i class="fa-solid fa-circle-info text-slate-500 mr-1"></i>${t.notes}
              </p>
            </div>
          </div>

          <!-- Right: Outcome & PnL if followed -->
          <div class="flex items-center justify-between lg:justify-end gap-6 pt-2 lg:pt-0 border-t border-slate-800/60 lg:border-t-0 font-mono">
            <div class="hidden lg:block text-right">
              ${outcomeBadge}
              <div class="text-[11px] text-slate-500 mt-1">
                ${t.exit_time ? 'Sortie : ' + t.exit_time : 'En cours de surveillance'}
              </div>
            </div>

            <div class="text-right pl-4 border-l border-slate-800">
              <span class="text-[10px] uppercase text-slate-500 block font-sans">Si tu avais suivi</span>
              <span class="text-lg sm:text-xl font-extrabold ${pnlColor}">${pnlText}</span>
              <span class="text-[10px] text-slate-500 block font-sans">sur ce trade</span>
            </div>
          </div>
        `;
        container.appendChild(row);
      });
    }

    // Auto load & auto refresh every 30s
    loadData();
    setInterval(loadData, 30000);
  </script>
</body>
</html>"""
