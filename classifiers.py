import re
from typing import List, Dict, Optional
from decimal import Decimal
from .models import Transaction, TransactionType, TransactionCategory


class TransactionClassifier:
    """
    Classifies transactions into categories for MCA underwriting
    """

    def __init__(self):
        self.credit_categories = {
            'true_revenue': [
                'ACH Credit from customers',
                'Wire transfers from clients', 
                'Check deposits from sales',
                'Credit card deposits',
                'Cash deposits',
                'PAYMENT',
                'DEPOSIT',
                'CREDIT CARD SETTLEMENT',
                'WIRE TRANSFER',
                'ACH CREDIT'
            ],
            'non_true_revenue': [
                'Online Transfer From',  # Internal transfers
                'Reversal',  # Returned items
                'Credit Return',  # Refunds
                'Book Transfer Credit',  # Inter-account
                'Loan proceeds',
                'MCA deposits',
                'TRANSFER FROM',
                'RETURN ITEM',
                'LOAN DEPOSIT',
                'TAX REFUND',
                'INSURANCE CLAIM'
            ]
        }

        self.debit_categories = {
            'mca_payments': {
                'patterns': [
                    r'.*MERCHANT.*CAPITAL.*',
                    r'.*BUSINESS.*ADVANCE.*',
                    r'.*DAILY.*ACH.*',
                    r'.*WORKING.*CAPITAL.*',
                    r'Orig CO Name.*Financial.*',
                    r'.*FUNDING.*CIRCLE.*',
                    r'.*KABBAGE.*',
                    r'.*ONDECK.*',
                    r'.*FORWARD.*FINANCING.*',
                    r'.*RAPID.*ADVANCE.*'
                ],
                'frequency': 'daily',
                'extract': ['lender_name', 'amount', 'date']
            },
            'operating_expenses': [
                'Payroll', 'Rent', 'Utilities', 'Supplies',
                'PAYROLL', 'SALARY', 'WAGE', 'RENT PAYMENT',
                'ELECTRIC', 'GAS', 'WATER', 'INTERNET'
            ],
            'transfers_out': [
                'Online Transfer To', 'Wire Transfer Out',
                'TRANSFER TO', 'WIRE OUT', 'BOOK TRANSFER'
            ]
        }

        self.nsf_patterns = [
            'NSF', 'Non-sufficient funds',
            'Overdraft', 'Return Item',
            'Insufficient Funds', 'OD Fee',
            'OVERDRAFT FEE', 'RETURNED ITEM',
            'INSUFFICIENT'
        ]

    def classify_transaction(self, transaction: Transaction) -> Transaction:
        """
        Classify a single transaction
        """
        desc = transaction.description.upper()
        
        if transaction.transaction_type == TransactionType.CREDIT:
            transaction = self._classify_credit(transaction, desc)
        else:
            transaction = self._classify_debit(transaction, desc)
            
        # Check for NSF
        if self._is_nsf_transaction(transaction, desc):
            transaction.category = TransactionCategory.NON_TRUE_REVENUE
            
        return transaction

    def _classify_credit(self, transaction: Transaction, desc: str) -> Transaction:
        """
        Classify credit transactions (deposits)
        """
        # Check for non-true revenue patterns first
        for pattern in self.credit_categories['non_true_revenue']:
            if pattern.upper() in desc:
                transaction.category = TransactionCategory.NON_TRUE_REVENUE
                transaction.is_true_revenue = False
                return transaction
        
        # Check for true revenue patterns
        for pattern in self.credit_categories['true_revenue']:
            if pattern.upper() in desc:
                transaction.category = TransactionCategory.TRUE_REVENUE
                transaction.is_true_revenue = True
                return transaction
        
        # Default for unmatched credits - assume true revenue unless proven otherwise
        transaction.category = TransactionCategory.TRUE_REVENUE
        transaction.is_true_revenue = True
        return transaction

    def _classify_debit(self, transaction: Transaction, desc: str) -> Transaction:
        """
        Classify debit transactions (withdrawals)
        """
        # Check for MCA payment patterns
        for pattern in self.debit_categories['mca_payments']['patterns']:
            if re.search(pattern, desc, re.IGNORECASE):
                transaction.category = TransactionCategory.MCA_PAYMENT
                transaction.is_mca_payment = True
                transaction.mca_lender = self._extract_lender_name(desc)
                return transaction
        
        # Check for operating expenses
        for expense in self.debit_categories['operating_expenses']:
            if expense.upper() in desc:
                transaction.category = TransactionCategory.OPERATING_EXPENSE
                return transaction
        
        # Check for transfers out
        for transfer in self.debit_categories['transfers_out']:
            if transfer.upper() in desc:
                transaction.category = TransactionCategory.TRANSFER_OUT
                return transaction
        
        # Default classification
        transaction.category = TransactionCategory.OPERATING_EXPENSE
        return transaction

    def _is_nsf_transaction(self, transaction: Transaction, desc: str) -> bool:
        """
        Detect NSF/overdraft transactions
        """
        # Check description patterns
        for pattern in self.nsf_patterns:
            if pattern.upper() in desc:
                return True
        
        # Check if balance went negative
        if transaction.balance < 0:
            return True
            
        # Check for returned items with positive amount (credit back)
        if 'RETURN' in desc and transaction.amount > 0:
            return True
            
        return False

    def _extract_lender_name(self, description: str) -> Optional[str]:
        """
        Extract lender name from MCA payment description
        """
        # Common patterns for extracting lender names
        patterns = [
            r'(.*CAPITAL.*)',
            r'(.*FINANCIAL.*)',
            r'(.*FUNDING.*)',
            r'(.*ADVANCE.*)',
            r'Orig CO Name[:\s]*([A-Z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback - return first few words
        words = description.split()[:3]
        return ' '.join(words) if words else None


class FraudDetector:
    """
    Detect fraudulent patterns in bank statements
    """
    
    def __init__(self):
        self.fraud_indicators = {
            'round_numbers': 'Multiple deposits of exact round amounts',
            'identical_deposits': 'Repeated identical deposit amounts', 
            'unusual_timing': 'Deposits at unusual hours',
            'new_sources': 'Sudden new deposit sources',
            'pattern_breaks': 'Break in established patterns'
        }

    def calculate_thumbprint_score(self, transactions: List[Transaction]) -> tuple[int, List[str]]:
        """
        Calculate fraud score (0-1000, 1000 = highest risk)
        """
        score = 0
        factors = []
        
        # Check for round number pattern
        if self._has_round_number_pattern(transactions):
            score += 150
            factors.append('Round number deposits')
        
        # Check for identical deposits
        if self._has_identical_deposits(transactions):
            score += 200
            factors.append('Repeated identical amounts')
        
        # Check for unusual timing
        if self._has_unusual_timing(transactions):
            score += 100
            factors.append('Unusual deposit timing')
        
        # Check for pattern breaks
        if self._has_pattern_breaks(transactions):
            score += 100
            factors.append('Inconsistent patterns')
        
        return min(score, 1000), factors

    def _has_round_number_pattern(self, transactions: List[Transaction]) -> bool:
        """
        Check for excessive round number deposits
        """
        credits = [t for t in transactions if t.transaction_type == TransactionType.CREDIT]
        if len(credits) < 10:
            return False
            
        round_numbers = sum(1 for t in credits if float(t.amount) % 100 == 0)
        return (round_numbers / len(credits)) > 0.3

    def _has_identical_deposits(self, transactions: List[Transaction]) -> bool:
        """
        Check for repeated identical deposit amounts
        """
        credits = [t for t in transactions if t.transaction_type == TransactionType.CREDIT]
        amounts = [t.amount for t in credits]
        
        from collections import Counter
        amount_counts = Counter(amounts)
        
        # Flag if any amount appears more than 5 times
        return any(count > 5 for count in amount_counts.values())

    def _has_unusual_timing(self, transactions: List[Transaction]) -> bool:
        """
        Check for deposits at unusual times (weekends, holidays)
        """
        # This is a simplified check - in real implementation,
        # you'd check actual transaction timestamps
        weekend_deposits = 0
        total_deposits = 0
        
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.CREDIT:
                total_deposits += 1
                if transaction.date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    weekend_deposits += 1
        
        if total_deposits == 0:
            return False
            
        return (weekend_deposits / total_deposits) > 0.2

    def _has_pattern_breaks(self, transactions: List[Transaction]) -> bool:
        """
        Check for sudden changes in deposit patterns
        """
        # Simplified implementation - check for sudden spikes in amounts
        credits = [t for t in transactions if t.transaction_type == TransactionType.CREDIT]
        if len(credits) < 20:
            return False
            
        amounts = [float(t.amount) for t in credits]
        avg_amount = sum(amounts) / len(amounts)
        
        # Flag if any deposit is more than 5x the average
        return any(amount > avg_amount * 5 for amount in amounts)