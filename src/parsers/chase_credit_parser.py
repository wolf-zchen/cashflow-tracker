"""
Parser for Chase credit card CSV files.
"""
import pandas as pd
from pathlib import Path
from typing import List
import json

from .base_parser import BaseParser
from ..models import Transaction


class ChaseCreditParser(BaseParser):
    """Parser for Chase credit card CSV files"""
    
    EXPECTED_COLUMNS = [
        'Transaction Date', 'Post Date', 'Description', 
        'Category', 'Type', 'Amount', 'Memo'
    ]
    
    def __init__(self):
        super().__init__(institution='Chase', account_type='credit_card')

    def get_account_name(self, file_path: Path) -> str:
        import re
        stem = file_path.stem
        match = re.search(r'[Cc]hase(\d{4})', stem)
        if match:
            return f"Chase Credit *{match.group(1)}"
        return "Chase Credit Card"

    def detect(self, file_path: Path) -> bool:
        """Detect if this is a Chase credit card CSV"""
        try:
            df = pd.read_csv(file_path, nrows=0)
            columns = df.columns.tolist()
            return all(col in columns for col in self.EXPECTED_COLUMNS)
        except:
            return False
    
    def parse(self, file_path: Path, account_name: str) -> List[Transaction]:
        """Parse Chase credit card CSV"""
        df = pd.read_csv(file_path)
        transactions = []
        
        for _, row in df.iterrows():
            # Skip if all values are NaN
            if row.isna().all():
                continue
            
            # Parse date (use Transaction Date as primary)
            date = self._parse_date(row['Transaction Date'])
            
            # Parse amount (Chase credit cards: positive = expense, negative = credit/refund)
            amount = self._parse_amount(row['Amount'])
            # Normalize: expenses should be negative
            if amount > 0:
                amount = -amount
            
            # Create transaction
            transaction = Transaction(
                date=date,
                description=row['Description'],
                amount=amount,
                account_name=account_name,
                account_type=self.account_type,
                institution=self.institution,
                category=row['Category'] if pd.notna(row['Category']) else 'Uncategorized',
                raw_data=json.dumps(row.to_dict()),
                notes=row['Memo'] if pd.notna(row['Memo']) else None
            )
            
            transactions.append(transaction)
        
        return transactions
