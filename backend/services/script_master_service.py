"""
Script Master Service
Reads 5paisa NSE/BSE scripmaster CSV and provides symbol → scrip-code lookups.

CSV columns (from 5paisa portal):
  Exch, ExchType, ScripCode, Name, Expiry, ScripType, StrikeRate,
  FullName, TickSize, LotSize, QtyLimit, Multiplier, SymbolRoot,
  BOCOAllowed, ISIN, ScripData, Series
"""

import os
import csv
from typing import Dict, Any, List, Optional

# Path to the scripmaster CSV file (plain CSV despite .gz extension)
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'ScripMaster_all.csv.gz')

# In-memory store: scrip_code → row dict
_scrip_map: Dict[int, Dict[str, Any]] = {}

# Equity-only indexes  (ExchType == "C" and Series in {EQ, BE, BZ, SM, …})
# name_index:       uppercase_name       → scrip_code
# symbol_root_index: uppercase_symbolroot → scrip_code
_name_index: Dict[str, int] = {}
_symbol_root_index: Dict[str, int] = {}

_loaded = False


def _load_csv():
    global _scrip_map, _name_index, _symbol_root_index, _loaded
    if _loaded:
        return

    csv_path = os.path.abspath(CSV_PATH)
    if not os.path.exists(csv_path):
        print(f"[SCRIP] WARNING: CSV not found at: {csv_path}")
        print("   Please upload the CSV from 5paisa to backend/data/")
        return

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    exch        = row.get('Exch', '').strip()
                    exch_type   = row.get('ExchType', '').strip()
                    scrip_code  = int(row.get('ScripCode', 0))
                    name        = row.get('Name', '').strip()
                    full_name   = row.get('FullName', name).strip()
                    series      = row.get('Series', '').strip()
                    isin        = row.get('ISIN', '').strip()
                    symbol_root = row.get('SymbolRoot', '').strip()

                    if not scrip_code or not name:
                        continue

                    entry = {
                        'scripCode':  scrip_code,
                        'name':       name,
                        'fullName':   full_name,
                        'exchange':   exch,
                        'exchType':   exch_type,
                        'series':     series,
                        'isin':       isin,
                        'symbolRoot': symbol_root,
                    }

                    # Build equity-priority index (ExchType == "C")
                    name_upper = name.upper()
                    root_upper = symbol_root.upper() if symbol_root else ''
                    is_equity  = (exch_type == 'C')

                    # _scrip_map: equity entries take priority
                    existing = _scrip_map.get(scrip_code)
                    if not existing or is_equity:
                        _scrip_map[scrip_code] = entry

                    if is_equity:
                        # Equity entry — always overwrite (preferred)
                        _name_index[name_upper] = scrip_code
                        if root_upper:
                            _symbol_root_index[root_upper] = scrip_code
                    else:
                        # Non-equity — store only if no equity entry yet
                        if name_upper not in _name_index:
                            _name_index[name_upper] = scrip_code
                        if root_upper and root_upper not in _symbol_root_index:
                            _symbol_root_index[root_upper] = scrip_code

                except (ValueError, KeyError):
                    continue

        _loaded = True
        print(f"[SCRIP] Loaded {len(_scrip_map)} scripts from CSV")

    except Exception as e:
        print(f"[SCRIP] ERROR: Failed to load CSV: {e}")


def _ensure_loaded():
    if not _loaded:
        _load_csv()


# ─────────────────────────────────────────────────────────────────────────────

class ScriptMasterService:
    """Provides symbol/name → scrip code lookup using the 5paisa scripmaster CSV."""

    def search_stock(self, query: str, exchange: str = 'N', exchange_type: str = 'C') -> List[Dict]:
        """
        Search for stocks whose Name, FullName, or SymbolRoot contains the
        query string. Filters by exchange + exchange type.  Returns up to 10.
        """
        _ensure_loaded()
        query_upper = query.upper().strip()

        results = []
        for sc, entry in _scrip_map.items():
            if entry.get('exchange') and entry['exchange'] != exchange:
                continue
            if entry.get('exchType') and entry['exchType'] != exchange_type:
                continue

            name      = entry.get('name', '').upper()
            full_name = entry.get('fullName', '').upper()
            sym_root  = entry.get('symbolRoot', '').upper()

            if query_upper in name or query_upper in full_name or query_upper in sym_root:
                results.append({
                    'scripCode':  sc,
                    'name':       entry['name'],
                    'fullName':   entry['fullName'],
                    'exchange':   entry['exchange'],
                    'series':     entry['series'],
                    'isin':       entry['isin'],
                    'symbolRoot': entry.get('symbolRoot', ''),
                })
                if len(results) >= 10:
                    break

        return results

    def get_scrip_code(self, symbol: str, exchange: str = 'N') -> Optional[int]:
        """
        Get the scrip code for an exact symbol match (e.g. 'RELIANCE').
        Priority: SymbolRoot index → Name index → linear scan (equity, matching exchange).
        """
        _ensure_loaded()
        symbol_upper = symbol.upper().strip()

        # 1) SymbolRoot index (most reliable for ticker symbols)
        if symbol_upper in _symbol_root_index:
            return _symbol_root_index[symbol_upper]

        # 2) Name index
        if symbol_upper in _name_index:
            return _name_index[symbol_upper]

        # 3) Fallback: linear scan for equity match on this exchange
        for sc, entry in _scrip_map.items():
            if entry.get('exchange', '') != exchange:
                continue
            if entry.get('exchType', '') != 'C':
                continue
            if entry.get('name', '').upper() == symbol_upper:
                return sc
            if entry.get('symbolRoot', '').upper() == symbol_upper:
                return sc

        return None

    def get_stock_details(self, scrip_code: int) -> Optional[Dict]:
        """Return CSV metadata for a given scrip code."""
        _ensure_loaded()
        return _scrip_map.get(scrip_code)

    def is_loaded(self) -> bool:
        return _loaded

    def get_stats(self) -> Dict:
        return {"loaded": _loaded, "total_scripts": len(_scrip_map)}


script_master_service = ScriptMasterService()
