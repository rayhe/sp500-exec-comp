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

    // Collapsible filter categories — progressive disclosure
    var AF_GROUPS = {
        comp: ['af-pay-band', 'af-conc', 'af-vol'],
        gov:  ['af-sop-tier', 'af-gov', 'af-board'],
        lead: ['af-tenure', 'af-gender']
    };
    function restoreAfGroupState() {
        document.querySelectorAll('.af-cat').forEach(function(details){
            var cat = details.getAttribute('data-cat');
            try {
                var stored = localStorage.getItem('sp500_afcat_' + cat);
                if (stored === 'open') details.open = true;
                else if (stored === 'closed') details.open = false;
            } catch(e) {}
        });
    }
    document.querySelectorAll('.af-cat').forEach(function(details){
        details.addEventListener('toggle', function(){
            try { localStorage.setItem('sp500_afcat_' + details.getAttribute('data-cat'), details.open ? 'open' : 'closed'); } catch(e) {}
        });
    });
    function updateAfGroupBadges() {
        var counts = { comp: 0, gov: 0, lead: 0 };
        Object.keys(AF_GROUPS).forEach(function(g){
            AF_GROUPS[g].forEach(function(id){
                var el = document.getElementById(id);
                if (el && el.value) counts[g]++;
            });
        });
        Object.keys(counts).forEach(function(g){
            var badge = document.getElementById('af-cat-count-' + g);
            if (badge) {
                badge.textContent = counts[g];
                badge.style.display = counts[g] ? 'inline-flex' : 'none';
            }
            // Auto-open any category holding an active filter so the active
            // control stays visible; never force-close on clear.
            if (counts[g] > 0) {
                var details = document.querySelector('.af-cat[data-cat="' + g + '"]');
                if (details && !details.open) details.open = true;
            }
        });
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
        updateAfGroupBadges();
    }

    // 329th review: a chart-origin volatility filter (histogram bar click /
    // keyboard activate in charts.js) overwrites an AF-origin bucket without
    // touching the af-vol select, so the select kept showing the old AF value
    // and the badge kept counting it while the table filtered on the chart
    // bucket -- and after dismissing the chart chip, the panel still claimed
    // an active filter that was no longer filtering. Chart handlers call
    // this helper (window-guarded) after setting a chart-origin bucket. It
    // clears the select WITHOUT dispatching 'change': handleVol('') would
    // null the just-set chart bucket, so the badge is refreshed directly
    // instead. Clearing unconditionally is correct: after a chart click the
    // active bucket is chart-origin by definition, never AF-origin.
    window._clearAfVolSelect = function() {
        var sel = document.getElementById('af-vol');
        if (sel) sel.value = '';
        updateAfBadge();
    };

    // 331st review: chart-origin setters and chip-dismiss handlers in
    // app.js also call this helper with the single select whose state
    // they overwrite/null (pay-band, sop-tier, tenure, gov, gender,
    // conc), closing the same panel-sync gap on the chart path that
    // the 329th vol fix closed for volatility alone.
    // 330th review: reset paths in app.js (resetAllFilters,
    // insightResetAndSort, sortTableByKey) null AF-origin filter state
    // (338th review: findCompanyInTable is a fourth such caller, for
    // the 4 AF dims it nulls; 339th review: the global Escape-key
    // clear-all path is a fifth such caller, for the same 4 AF dims;
    // 344th review: resetAllFilters is the exception -- it nulls
    // _activeBoardFilter too, so it passes 'af-board' as well.)
    // without touching the af-* selects, so the panel kept showing the
    // old value and the badge kept counting a filter that no longer
    // filtered -- the panel-side mirror of the 326th chip bug. Callers
    // pass exactly the selects whose state they nulled. Board is
    // excluded from every caller except resetAllFilters: none of the
    // other paths nulls _activeBoardFilter, so for them the af-board
    // select and its badge count stay truthful. Like _clearAfVolSelect, this sets .value directly
    // WITHOUT dispatching 'change': the handlers would re-null
    // already-nulled state and trigger extra table refreshes. The badge
    // (plus summary, toggle class, and group badges) is refreshed
    // directly via updateAfBadge().
    window._clearAfSelects = function(ids) {
        (ids || []).forEach(function(id){
            var el = document.getElementById(id);
            if (el) el.value = '';
        });
        updateAfBadge();
    };

    function clearAdvancedFilters() {
        ['af-pay-band','af-sop-tier','af-tenure','af-gov','af-board','af-gender','af-conc','af-vol'].forEach(function(id){
            var el = document.getElementById(id);
            if (el) el.value = '';
        });
        // 336th review: AF Clear nulls the dist filter ONLY when it is
        // AF-origin (_isAfPay). The old else-branch sniffed the label
        // for 'M' to guess AF-origin, but chart-origin dist labels are
        // '$X.XM' too (histogram/sector clicks), so Clear silently
        // killed chart filters from an AF-scoped button -- inconsistent
        // with chart-origin tenure/conc/vol, which survive Clear (their
        // state is nulled only for _isAf values). Origin is already
        // tracked cleanly (_isAfPay is set only by handlePayBand), so
        // the heuristic was redundant as well as wrong. A surviving
        // chart dist chip is re-rendered by _updateDistFilterIndicator
        // below (335th), so chip and state agree either way.
        // 337th review: closes the 336th run's remaining asymmetry the
        // same way, not with a label sniff. SoP already carried _isAf
        // (handleSopTier sets it; the chart setter and URL restore do
        // not), so Clear now gates on it. Gov gains a copied _isAf flag
        // in handleGov (a copy, not the shared gradeMap object). Gender
        // state is a bare 'F'/'M' string with no object to hang a flag
        // on, so it gains a parallel window._isAfGender boolean written
        // by filterByGender (fromAf) and the URL restore (false: a
        // restored filter is not AF-origin). Board has no chart setter
        // and is still nulled unconditionally, correctly. Surviving
        // chart gov/gender/sop chips are re-rendered by the indicator
        // calls below (334th/335th), so chip and state agree either way.
        if (window._activeDistFilter && window._activeDistFilter._isAfPay) window._activeDistFilter = null;
        if (window._activeSopFilter && window._activeSopFilter._isAf) window._activeSopFilter = null;
        if (window._activeTenureQuartile && window._activeTenureQuartile._isAf) window._activeTenureQuartile = null;
        if (window._activeGovGrade && window._activeGovGrade._isAf) window._activeGovGrade = null;
        if (window._activeBoardFilter) window._activeBoardFilter = null;
        if (window._activeGenderFilter && window._isAfGender) { window._activeGenderFilter = null; window._isAfGender = false; }
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
        // 327th review: the volatility chip is app.js-owned (not dataset.af),
        // so the loop above skips it; the indicator removes it once state is
        // nulled (state was cleared above for _isAf buckets).
        if (typeof window._updateVolatilityFilterIndicator === 'function') window._updateVolatilityFilterIndicator();
        // 334th review: same app.js-owned-chip class for gender, tenure,
        // gov and conc -- their chips are not dataset.af either, so the
        // loop above skips them while their state was just nulled
        // (gender/gov unconditionally, tenure/conc for _isAf values),
        // leaving stale chips after AF Clear. The indicators remove
        // chips whose state is null and re-render ones whose state
        // survived (chart-origin tenure/conc), so calling them here is
        // idempotent for the surviving filters.
        if (typeof window._updateGenderFilterIndicator === 'function') window._updateGenderFilterIndicator();
        if (typeof window._updateTenureFilterIndicator === 'function') window._updateTenureFilterIndicator();
        if (typeof window._updateGovFilterIndicator === 'function') window._updateGovFilterIndicator();
        if (typeof window._updateConcFilterIndicator === 'function') window._updateConcFilterIndicator();
        // 335th review: same app.js-owned-chip class for dist and sop --
        // the AF pay-band / SoP handlers reuse the app.js chip id and
        // only overwrite its textContent (never setting dataset.af),
        // so when an AF value is set over a chart-origin chip the Clear
        // loop skips it while state is nulled, leaving a stale chip.
        // The indicators remove chips whose state is null and re-render
        // ones whose state survived, so calling them here is idempotent.
        if (typeof window._updateDistFilterIndicator === 'function') window._updateDistFilterIndicator();
        if (typeof window._updateSopFilterIndicator === 'function') window._updateSopFilterIndicator();

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
            // 335th review: same collision as AF Clear -- when an AF
            // pay band was set over a chart-origin dist chip, the chip
            // carries no dataset.af, so the removal above skips it
            // while state was just nulled. The indicator removes it
            // (mirrors the handleVol('') pattern from the 327th review).
            if (typeof window._updateDistFilterIndicator === 'function') window._updateDistFilterIndicator();
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
            // 334th review: the tenure chip is app.js-owned (not
            // dataset.af), so refresh the indicator -- it removes the
            // chip now that state is null, instead of leaving a stale
            // chip like the pre-327th volatility path did.
            if (typeof window._updateTenureFilterIndicator === 'function') window._updateTenureFilterIndicator();
            // 353rd review: AF clear must clear the bar highlight too.
            if (typeof window.highlightTenureBucket === 'function') window.highlightTenureBucket(null, null);
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parts[1] === '999' ? Infinity : parseFloat(parts[1]);
        var labelMap = { '0-3':'New (<3 yrs)', '3-10':'Mid (3–10 yrs)', '10-20':'Established (10–20 yrs)', '20-999':'Veteran 20+ yrs' };
        window._activeTenureQuartile = { min: min, max: max, tag: labelMap[val] || val, label: labelMap[val] || val, _isAf: true };
        // 334th review: refresh the app.js-owned chip so an AF-origin
        // value replaces (not hides behind) a stale chart-origin tag.
        if (typeof window._updateTenureFilterIndicator === 'function') window._updateTenureFilterIndicator();
        // 353rd review: the AF tenure bands match the chart brackets
        // exactly, so highlight the matching bracket like the
        // chart-origin setter does (unlike gov/vol, no band mismatch).
        if (typeof window.highlightTenureBucket === 'function') window.highlightTenureBucket(min, max);
        if (typeof window._refreshTable === 'function') window._refreshTable();
        else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
    }

    function handleGov(val) {
        if (!val) {
            if (window._activeGovGrade) window._activeGovGrade = null;
            // 334th review: same app.js-owned-chip refresh as tenure --
            // the gov chip is not dataset.af, so only the indicator
            // removes it once state is null.
            if (typeof window._updateGovFilterIndicator === 'function') window._updateGovFilterIndicator();
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
        // 337th review: copy (do NOT assign the shared gradeMap object)
        // and stamp _isAf, so AF Clear can preserve chart-origin grades
        // the way it already preserves chart-origin tenure/conc/vol/
        // dist. Assigning gradeMap[val] directly would alias the shared
        // map entry, so stamping a flag on it would pollute every later
        // AF gov selection; the copy keeps the flag on this selection
        // only. The chart setter (filterByGovGrade) and URL restore
        // build flag-less objects, so they read as chart-origin.
        var g = gradeMap[val];
        window._activeGovGrade = { min: g.min, max: g.max, grade: g.grade, _isAf: true };
        // 334th review: refresh the app.js-owned chip so an AF-origin
        // grade replaces (not hides behind) a stale chart-origin tag.
        if (typeof window._updateGovFilterIndicator === 'function') window._updateGovFilterIndicator();
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
                // 331st review: pass fromAf so filterByGender skips its
                // chart-origin af-gender clear (the select is already '').
                if (window.filterByGender) window.filterByGender(window._activeGenderFilter, true);
                else window._activeGenderFilter = null;
            }
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        if (window._activeGenderFilter !== val) {
            // 331st review: pass fromAf so filterByGender skips its
            // chart-origin af-gender clear, which would wipe this value.
            if (window.filterByGender) window.filterByGender(val, true);
            else window._activeGenderFilter = val;
        }
    }

    function handleConc(val) {
        if (!val) {
            if (window._activeConcTier) window._activeConcTier = null;
            var chip = document.getElementById('conc-filter-chip');
            if (chip && chip.dataset && chip.dataset.af === '1') chip.parentNode.removeChild(chip);
            // 335th review: the conc chip is app.js-owned (no
            // dataset.af), so the removal above skips it while state
            // was just nulled -- the 334th review fixed this shape for
            // AF Clear only, not for this individual-clear path. The
            // indicator removes the chip now that state is null.
            if (typeof window._updateConcFilterIndicator === 'function') window._updateConcFilterIndicator();
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
            if (typeof window._updateVolatilityFilterIndicator === 'function') window._updateVolatilityFilterIndicator();
            if (typeof window._refreshTable === 'function') window._refreshTable();
            else if (window.compData) { try { renderTable(window.compData.companies); } catch(e){} }
            return;
        }
        var parts = val.split('-');
        var min = parseFloat(parts[0]);
        var max = parts[1] === '999' ? Infinity : parseFloat(parts[1]);
        var labelMap = { '0-10':'Stable <10%', '10-25':'Moderate 10–25%', '25-50':'Volatile 25–50%', '50-999':'Highly volatile 50%+' };
        window._activeVolatilityBucket = { min: min, max: max, label: labelMap[val] || val, _isAf: true };
        if (typeof window._updateVolatilityFilterIndicator === 'function') window._updateVolatilityFilterIndicator();
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

    // Live company list for AF refreshes. app.js keeps the dataset in a
    // top-level `let compData` (never a window property), so the old
    // `window.compData` branches below never fired and _refreshTable()
    // silently re-rendered nothing: AF select changes updated state and
    // the badge but left the table rows untouched until an unrelated
    // action re-rendered. charts.js exposes the same list as
    // window._chartData.companies (the list every other cross-file
    // renderTable call site passes), so fall back to it; keep the
    // window.compData branch first for any future loader that sets it.
    function getAFCompanies() {
        if (window.compData && window.compData.companies) return window.compData.companies;
        if (window._chartData && window._chartData.companies) return window._chartData.companies;
        return null;
    }

    // Extend _refreshTable to include board filter DOM post-process
    var _originalRefresh = window._refreshTable;
    window._refreshTable = function() {
        var afCompanies = getAFCompanies();
        if (_originalRefresh) {
            try { _originalRefresh(); } catch(e) {}
        } else if (afCompanies && typeof renderTable === 'function') {
            try { renderTable(afCompanies); } catch(e) {}
        }
        if (window._activeBoardFilter) {
            var tbody = document.getElementById('comp-tbody');
            if (tbody && afCompanies) {
                var mode = window._activeBoardFilter.mode;
                var lookup = {};
                afCompanies.forEach(function(c){ lookup[c.ticker]=c; });
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

    restoreAfGroupState();
    document.addEventListener('DOMContentLoaded', function(){ restoreAfGroupState(); updateAfBadge(); });
    setTimeout(function(){ restoreAfGroupState(); updateAfBadge(); }, 600);

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
