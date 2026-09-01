/* === Advanced Filters + Network Overflow — Progressive Disclosure (Interactivity 9.7→9.9) === */
(function() {
    // Board independence filter state (new dimension)
    window._activeBoardFilter = null; // { mode: 'high'|'mid'|'low' }

    function applyBoardFilter(companies) {
        if (!window._activeBoardFilter) return companies;
        var mode = window._activeBoardFilter.mode;
        return companies.filter(function(c) {
            var bi = c.board_independence;
            var pct = bi ? bi.independence_pct : null;
            if (pct == null) {
                if (mode === 'high') return false;
                if (mode === 'mid') return false;
                return true;
            }
            if (mode === 'high') return pct >= 80;
            if (mode === 'mid') return pct >= 60 && pct < 80;
            if (mode === 'low') return pct < 60;
            return true;
        });
    }
    window._applyBoardFilter = applyBoardFilter;

    function triggerTableRefresh() {
        if (typeof window._refreshTable === 'function') {
            window._refreshTable();
            return;
        }
        if (window.compData && window.compData.companies && typeof window._sp500RenderTable === 'function') {
            window._sp500RenderTable(window.compData.companies);
            return;
        }
        // DOM post-filter fallback for board
        if (window._activeBoardFilter) {
            var tbody = document.getElementById('comp-tbody');
            if (tbody) {
                var mode = window._activeBoardFilter.mode;
                Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function(tr) {
                    var tickerCell = tr.querySelector('td:nth-child(2)');
                    var ticker = tickerCell ? tickerCell.textContent.trim() : (tr.dataset.ticker || '');
                    var comp = window.compData && window.compData.companies ? window.compData.companies.find(function(c){return c.ticker===ticker;}) : null;
                    if (!comp) return;
                    var bi = comp.board_independence;
                    var pct = bi ? bi.independence_pct : null;
                    var keep = true;
                    if (pct == null) {
                        if (mode === 'high' || mode === 'mid') keep = false;
                    } else {
                        if (mode === 'high') keep = pct >= 80;
                        else if (mode === 'mid') keep = pct >= 60 && pct < 80;
                        else if (mode === 'low') keep = pct < 60;
                    }
                    tr.style.display = keep ? '' : 'none';
                });
            }
        }
    }

    function updateAfBadge() {
        var count = 0;
        var parts = [];
        var selects = ['af-pay-band','af-sop-tier','af-tenure','af-gov','af-board','af-gender','af-conc','af-vol'];
        selects.forEach(function(id){
            var el = document.getElementById(id);
            if (el && el.value) {
                count++;
                var label = el.options[el.selectedIndex].text;
                parts.push(label);
                el.classList.add('af-active');
            } else if (el) {
                el.classList.remove('af-active');
            }
        });
        var badge = document.getElementById('af-count-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count ? 'inline-flex' : 'none';
        }
        var summary = document.getElementById('af-active-summary');
        if (summary) {
            summary.textContent = count ? count + ' active: ' + parts.join(' · ') : '';
        }
        var toggle = document.getElementById('advanced-filters-toggle');
        if (toggle) {
            if (count) toggle.classList.add('has-active');
            else toggle.classList.remove('has-active');
        }
    }

    function clearAdvancedFilters() {
        ['af-pay-band','af-sop-tier','af-tenure','af-gov','af-board','af-gender','af-conc','af-vol'].forEach(function(id){
            var el = document.getElementById(id);
            if (el) el.value = '';
        });
        if (window._activeDistFilter && window._activeDistFilter._isAfPay) window._activeDistFilter = null;
        else if (window._activeDistFilter && document.getElementById('af-pay-band') && !document.getElementById('af-pay-band').value) {
            // If pay band was the dist filter, clear it
            var payVal = document.getElementById('af-pay-band') ? document.getElementById('af-pay-band').value : '';
            if (!payVal && window._activeDistFilter) {
                // Only clear if it was set via AF (heuristic: check label contains 'M')
                if (window._activeDistFilter.label && window._activeDistFilter.label.indexOf('M') >= 0) window._activeDistFilter = null;
            }
        }
        if (window._activeSopFilter) window._activeSopFilter = null;
        if (window._activeTenureQuartile && window._activeTenureQuartile._isAf) window._activeTenureQuartile = null;
        if (window._activeGovGrade) window._activeGovGrade = null;
        if (window._activeBoardFilter) window._activeBoardFilter = null;
        if (window._activeGenderFilter) window._activeGenderFilter = null;
        if (window._activeConcTier && window._activeConcTier._isAf) window._activeConcTier = null;
        if (window._activeVolatilityBucket && window._activeVolatilityBucket._isAf) window._activeVolatilityBucket = null;

        // Remove chips created by AF
        ['dist-filter-chip','sop-filter-chip','tenure-filter-chip','gov-filter-chip','board-filter-chip','gender-filter-chip','conc-filter-chip','volatility-filter-chip'].forEach(function(cid){
            var chip = document.getElementById(cid);
            if (chip && chip.dataset && chip.dataset.af === '1') {
                if (chip.parentNode) chip.parentNode.removeChild(chip);
            } else if (cid === 'board-filter-chip') {
                var bc = document.getElementById('board-filter-chip');
                if (bc && bc.parentNode) bc.parentNode.removeChild(bc);
            }
        });

        updateAfBadge();
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData && typeof renderTable === 'function') {
            try { renderTable(window.compData.companies); } catch(e){}
        } else if (window._sp500RenderTable && window.compData) {
            window._sp500RenderTable(window.compData.companies);
        }
        if (typeof announce === 'function') announce('Advanced filters cleared');
    }

    // Wire Advanced Filters toggle
    var afToggle = document.getElementById('advanced-filters-toggle');
    var afPanel = document.getElementById('advanced-filters-panel');
    if (afToggle && afPanel) {
        afToggle.addEventListener('click', function(){
            var expanded = afToggle.getAttribute('aria-expanded') === 'true';
            afToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
            afPanel.hidden = expanded;
            if (!expanded) {
                var firstSel = afPanel.querySelector('select');
                if (firstSel) setTimeout(function(){ firstSel.focus(); }, 80);
            }
            if (typeof announce === 'function') announce(expanded ? 'Advanced filters collapsed' : 'Advanced filters expanded');
        });
    }

    // Wire Network overflow toggle
    var netToggle = document.getElementById('network-overflow-toggle');
    var netMenu = document.getElementById('network-overflow-menu');
    if (netToggle && netMenu) {
        netToggle.addEventListener('click', function(e){
            e.stopPropagation();
            var expanded = netToggle.getAttribute('aria-expanded') === 'true';
            netToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
            netMenu.hidden = expanded;
            if (typeof announce === 'function') announce(expanded ? 'More views collapsed' : 'More views expanded');
        });
        document.addEventListener('click', function(e){
            if (!netMenu.hidden && !netMenu.contains(e.target) && e.target !== netToggle && !netToggle.contains(e.target)) {
                netMenu.hidden = true;
                netToggle.setAttribute('aria-expanded','false');
            }
        });
        document.addEventListener('keydown', function(e){
            if (e.key === 'Escape' && !netMenu.hidden) {
                netMenu.hidden = true;
                netToggle.setAttribute('aria-expanded','false');
                netToggle.focus();
            }
        });
    }

    // Advanced filter handlers
    function handlePayBand(val) {
        if (!val) {
            if (window._activeDistFilter && window._activeDistFilter._isAfPay) window._activeDistFilter = null;
            var chip = document.getElementById('dist-filter-chip');
            if (chip && chip.dataset && chip.dataset.af === '1') chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseInt(parts[0],10);
        var max = parts[1] === '9999999999' ? Infinity : parseInt(parts[1],10);
        window._activeDistFilter = { min: min, max: max, label: '$' + (min/1000000) + 'M–$' + (max===Infinity?'∞':(max/1000000)+'M'), _isAfPay: true, sector: null };
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
        var existing = document.getElementById('dist-filter-chip');
        if (!existing) {
            var chip = document.createElement('span');
            chip.className = 'chip active';
            chip.id = 'dist-filter-chip';
            chip.dataset.af = '1';
            chip.textContent = 'Pay: ' + (min/1000000) + '–' + (max===Infinity?'∞':(max/1000000)) + 'M ✕';
            chip.title = 'Click to clear pay band filter';
            chip.onclick = function(){ document.getElementById('af-pay-band').value=''; handlePayBand(''); updateAfBadge(); };
            var summaryBar = document.getElementById('table-summary-bar');
            if (summaryBar) summaryBar.appendChild(chip);
        } else {
            existing.textContent = 'Pay: ' + (min/1000000) + '–' + (max===Infinity?'∞':(max/1000000)) + 'M ✕';
        }
    }

    function handleSopTier(val) {
        if (!val) {
            if (window._activeSopFilter) window._activeSopFilter = null;
            var chip = document.getElementById('sop-filter-chip');
            if (chip) chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parseFloat(parts[1]);
        if (max === 101) max = Infinity;
        window._activeSopFilter = { min: min, max: max, label: 'SoP ' + min + '–' + (max===Infinity?'∞':max) + '%', _isAf: true };
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
        var existing = document.getElementById('sop-filter-chip');
        if (!existing) {
            var chip = document.createElement('span');
            chip.className = 'chip active';
            chip.id = 'sop-filter-chip';
            chip.dataset.af = '1';
            chip.textContent = 'SoP: ' + min + '–' + (max===Infinity?'100+':max) + '% ✕';
            chip.title = 'Click to clear SoP filter';
            chip.onclick = function(){ document.getElementById('af-sop-tier').value=''; handleSopTier(''); updateAfBadge(); };
            var summaryBar = document.getElementById('table-summary-bar');
            if (summaryBar) summaryBar.appendChild(chip);
        } else {
            existing.textContent = 'SoP: ' + min + '–' + (max===Infinity?'100+':max) + '% ✕';
        }
    }

    function handleTenure(val) {
        if (!val) {
            if (window._activeTenureQuartile) window._activeTenureQuartile = null;
            var chip = document.getElementById('tenure-filter-chip');
            if (chip) chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parts[1] === '999' ? Infinity : parseFloat(parts[1]);
        var labelMap = { '0-3':'New (<3 yrs)', '3-10':'Mid (3–10 yrs)', '10-20':'Established (10–20 yrs)', '20-999':'Veteran 20+ yrs' };
        window._activeTenureQuartile = { min: min, max: max, tag: labelMap[val] || val, label: labelMap[val] || val, _isAf: true };
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
    }

    function handleGov(val) {
        if (!val) {
            if (window._activeGovGrade) window._activeGovGrade = null;
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var gradeMap = {
            'A': { min: 80, max: 100, grade: 'A' },
            'B': { min: 65, max: 79.999, grade: 'B' },
            'C': { min: 50, max: 64.999, grade: 'C' },
            'D': { min: 35, max: 49.999, grade: 'D' },
            'F': { min: 0, max: 34.999, grade: 'F' }
        };
        window._activeGovGrade = gradeMap[val];
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
    }

    function handleBoard(val) {
        if (!val) {
            window._activeBoardFilter = null;
            var chip = document.getElementById('board-filter-chip');
            if (chip) chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else triggerTableRefresh();
            return;
        }
        window._activeBoardFilter = { mode: val };
        var labelMap = { high: 'Board ≥80%', mid: 'Board 60–80%', low: 'Board <60%' };
        var existing = document.getElementById('board-filter-chip');
        if (!existing) {
            var chip = document.createElement('span');
            chip.className = 'chip active';
            chip.id = 'board-filter-chip';
            chip.dataset.af = '1';
            chip.textContent = (labelMap[val] || val) + ' ✕';
            chip.title = 'Click to clear board independence filter';
            chip.onclick = function(){ document.getElementById('af-board').value=''; handleBoard(''); updateAfBadge(); };
            var summaryBar = document.getElementById('table-summary-bar');
            if (summaryBar) summaryBar.appendChild(chip);
        } else {
            existing.textContent = (labelMap[val] || val) + ' ✕';
        }
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else triggerTableRefresh();
    }

    function handleGender(val) {
        if (!val) {
            if (window._activeGenderFilter) {
                if (window.filterByGender) window.filterByGender(window._activeGenderFilter);
                else window._activeGenderFilter = null;
            }
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        if (window._activeGenderFilter !== val) {
            if (window.filterByGender) window.filterByGender(val);
            else window._activeGenderFilter = val;
        }
    }

    function handleConc(val) {
        if (!val) {
            if (window._activeConcTier) window._activeConcTier = null;
            var chip = document.getElementById('conc-filter-chip');
            if (chip && chip.dataset && chip.dataset.af === '1') chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parts[1] === '100' ? Infinity : parseFloat(parts[1]);
        var tagMap = { '0-30':'Low <30%', '30-40':'30–40%', '40-50':'40–50%', '50-60':'50–60%', '60-100':'High 60%+' };
        window._activeConcTier = { min: min, max: max, tag: tagMap[val] || val, label: tagMap[val] || val, _isAf: true };
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
    }

    function handleVol(val) {
        if (!val) {
            if (window._activeVolatilityBucket) window._activeVolatilityBucket = null;
            var chip = document.getElementById('volatility-filter-chip');
            if (chip && chip.dataset && chip.dataset.af === '1') chip.parentNode.removeChild(chip);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parts[1] === '999' ? Infinity : parseFloat(parts[1]);
        var labelMap = { '0-10':'Stable <10%', '10-25':'Moderate 10–25%', '25-50':'Volatile 25–50%', '50-999':'Highly volatile 50%+' };
        window._activeVolatilityBucket = { min: min, max: max, label: labelMap[val] || val, _isAf: true };
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
    }

    // Wire selects
    var payEl = document.getElementById('af-pay-band');
    if (payEl) payEl.addEventListener('change', function(){ handlePayBand(this.value); updateAfBadge(); });
    var sopEl = document.getElementById('af-sop-tier');
    if (sopEl) sopEl.addEventListener('change', function(){ handleSopTier(this.value); updateAfBadge(); });
    var tenEl = document.getElementById('af-tenure');
    if (tenEl) tenEl.addEventListener('change', function(){ handleTenure(this.value); updateAfBadge(); });
    var govEl = document.getElementById('af-gov');
    if (govEl) govEl.addEventListener('change', function(){ handleGov(this.value); updateAfBadge(); });
    var boardEl = document.getElementById('af-board');
    if (boardEl) boardEl.addEventListener('change', function(){ handleBoard(this.value); updateAfBadge(); });
    var genderEl = document.getElementById('af-gender');
    if (genderEl) genderEl.addEventListener('change', function(){ handleGender(this.value); updateAfBadge(); });
    var concEl = document.getElementById('af-conc');
    if (concEl) concEl.addEventListener('change', function(){ handleConc(this.value); updateAfBadge(); });
    var volEl = document.getElementById('af-vol');
    if (volEl) volEl.addEventListener('change', function(){ handleVol(this.value); updateAfBadge(); });

    var clearBtn = document.getElementById('af-clear-btn');
    if (clearBtn) clearBtn.addEventListener('click', function(){ clearAdvancedFilters(); });

    // Extend _refreshTable to include board filter DOM post-process
    var _originalRefresh = window._refreshTable;
    window._refreshTable = function() {
        if (_originalRefresh) {
            try { _originalRefresh(); } catch(e) {}
        } else if (window.compData && typeof renderTable === 'function') {
            try { renderTable(window.compData.companies); } catch(e) {}
        }
        if (window._activeBoardFilter) {
            var tbody = document.getElementById('comp-tbody');
            if (tbody && window.compData && window.compData.companies) {
                var mode = window._activeBoardFilter.mode;
                var lookup = {};
                window.compData.companies.forEach(function(c){ lookup[c.ticker]=c; });
                Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function(tr){
                    var tickerCell = tr.querySelector('td:nth-child(2)');
                    var ticker = tickerCell ? tickerCell.textContent.trim() : (tr.dataset.ticker || '');
                    var comp = lookup[ticker];
                    if (!comp) return;
                    var bi = comp.board_independence;
                    var pct = bi ? bi.independence_pct : null;
                    var keep = true;
                    if (pct == null) {
                        if (mode === 'high' || mode === 'mid') keep = false;
                    } else {
                        if (mode === 'high') keep = pct >= 80;
                        else if (mode === 'mid') keep = pct >= 60 && pct < 80;
                        else if (mode === 'low') keep = pct < 60;
                    }
                    if (!keep) tr.style.display = 'none';
                    else tr.style.display = '';
                });
            }
        }
        updateAfBadge();
    };

    window._sp500RenderTable = function(companies) {
        if (typeof renderTable === 'function') {
            try {
                var filtered = companies;
                if (window._activeBoardFilter) filtered = applyBoardFilter(filtered);
                renderTable(filtered);
                return;
            } catch(e) {}
        }
    };

    document.addEventListener('DOMContentLoaded', function(){ updateAfBadge(); });
    setTimeout(updateAfBadge, 600);

    document.addEventListener('keydown', function(e){
        if (e.key === 'Escape') {
            var panel = document.getElementById('advanced-filters-panel');
            var toggle = document.getElementById('advanced-filters-toggle');
            if (panel && !panel.hidden && panel.contains(document.activeElement)) {
                panel.hidden = true;
                if (toggle) {
                    toggle.setAttribute('aria-expanded','false');
                    toggle.focus();
                }
                if (typeof announce === 'function') announce('Advanced filters collapsed');
                e.preventDefault();
            }
        }
    });
})();
