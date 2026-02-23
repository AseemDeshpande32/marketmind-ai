"""
Script Master Service - Search and map stock names to scrip codes
"""
import csv
import os
from typing import List, Dict, Optional


class ScriptMasterService:
    """Service for searching stocks in Script Master"""
    
    def __init__(self):
        self.script_master_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'scripmaster-csv-format.csv'
        )
        self.cache = None
        
    def load_script_master(self) -> List[Dict]:
        """Load and cache the script master CSV"""
        if self.cache is not None:
            return self.cache
            
        scripts = []
        try:
            with open(self.script_master_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scripts.append(row)
            
            self.cache = scripts
            print(f"✅ Loaded {len(scripts)} scripts from Script Master")
            return scripts
            
        except FileNotFoundError:
            print(f"❌ Script Master file not found at: {self.script_master_path}")
            return []
        except Exception as e:
            print(f"❌ Error loading Script Master: {e}")
            return []
    
    def search_stock(self, query: str, exchange: str = "N", exchange_type: str = "C") -> List[Dict]:
        """
        Search for stocks by name
        
        Args:
            query: Stock name to search (e.g., "RELIANCE", "TCS")
            exchange: N=NSE, B=BSE, ALL=both NSE+BSE (default: N)
            exchange_type: C=Cash, D=Derivative (default: C)
            
        Returns:
            List of matching stocks with scrip code and details
        """
        scripts = self.load_script_master()
        query_upper = query.upper().strip()
        
        # Only allow NSE and BSE (filter out MCX, NCDEX, etc.)
        allowed_exchanges = ['N', 'B']
        
        results = []
        for script in scripts:
            script_exch = script.get('Exch', '')
            script_exch_type = script.get('ExchType', '')
            
            # Only allow NSE/BSE exchanges
            if script_exch not in allowed_exchanges:
                continue
            
            # Filter by exchange type (Cash only by default)
            if script_exch_type != exchange_type:
                continue
            
            # If specific exchange requested, filter by it
            if exchange != 'ALL' and script_exch != exchange:
                continue
            
            # Search in Name and FullName
            name = script.get('Name', '').upper()
            full_name = script.get('FullName', '').upper()
            
            # Exact match or contains query
            if query_upper == name or query_upper in name or query_upper in full_name:
                results.append({
                    'scripCode': int(script.get('Scripcode', 0)),
                    'name': script.get('Name', ''),
                    'fullName': script.get('FullName', ''),
                    'exchange': script.get('Exch', ''),
                    'exchangeType': script.get('ExchType', ''),
                    'series': script.get('Series', ''),
                    'isin': script.get('ISIN', ''),
                })
        
        # Sort by relevance (exact matches first)
        results.sort(key=lambda x: 0 if x['name'].upper() == query_upper else 1)
        
        return results
    
    def get_scrip_code(self, symbol: str, exchange: str = "N") -> Optional[int]:
        """
        Get scrip code for a stock symbol
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            exchange: N=NSE, B=BSE
            
        Returns:
            Scrip code or None if not found
        """
        results = self.search_stock(symbol, exchange, "C")
        
        # Return first exact match
        for result in results:
            if result['name'].upper() == symbol.upper():
                return result['scripCode']
        
        # Return first partial match if no exact match
        if results:
            return results[0]['scripCode']
        
        return None
    
    def get_stock_details(self, scrip_code: int) -> Optional[Dict]:
        """
        Get stock details by scrip code
        
        Args:
            scrip_code: Scrip code (e.g., 1660)
            
        Returns:
            Stock details or None if not found
        """
        scripts = self.load_script_master()
        
        for script in scripts:
            if int(script.get('Scripcode', 0)) == scrip_code:
                return {
                    'scripCode': scrip_code,
                    'name': script.get('Name', ''),
                    'fullName': script.get('FullName', ''),
                    'exchange': script.get('Exch', ''),
                    'exchangeType': script.get('ExchType', ''),
                    'series': script.get('Series', ''),
                    'isin': script.get('ISIN', ''),
                }
        
        return None


# Singleton instance
script_master_service = ScriptMasterService()
