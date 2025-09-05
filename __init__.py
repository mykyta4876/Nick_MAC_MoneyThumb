"""
MoneyThumb - Advanced Bank Statement Analysis System

A comprehensive system for extracting, analyzing, and scoring bank statements
for MCA (Merchant Cash Advance) underwriting purposes.

Features:
- OCR processing of bank statement PDFs
- Transaction classification (true revenue vs non-true revenue)
- MCA position detection from ACH patterns
- Cash flow analysis and projections
- Fraud detection (Thumbprint scoring)
- Comprehensive underwriting metrics

Usage:
    from moneythumb import MoneyThumbSystem
    
    system = MoneyThumbSystem()
    result = system.process_bank_statement('statement.pdf')
    print(result.metrics.average_monthly_revenue)
"""

from .core import MoneyThumbSystem
from .models import (
    Transaction, BankAccount, MCAPosition, MonthlyStats,
    CashFlowMetrics, UnderwritingMetrics, MoneyThumbResponse,
    TransactionType, TransactionCategory
)
from .classifiers import TransactionClassifier, FraudDetector
from .analyzers import (
    MCADetection, DailyBalanceCalculator, CashFlowAnalysis,
    MonthlyStatsCalculator, UnderwritingMetricsCalculator
)
from .ocr_engine import BankStatementOCR

__version__ = "1.0.0"
__author__ = "MoneyThumb Development Team"
__email__ = "dev@moneythumb.com"

__all__ = [
    'MoneyThumbSystem',
    'Transaction',
    'BankAccount', 
    'MCAPosition',
    'MonthlyStats',
    'CashFlowMetrics',
    'UnderwritingMetrics',
    'MoneyThumbResponse',
    'TransactionType',
    'TransactionCategory',
    'TransactionClassifier',
    'FraudDetector',
    'MCADetection',
    'DailyBalanceCalculator',
    'CashFlowAnalysis',
    'MonthlyStatsCalculator',
    'UnderwritingMetricsCalculator',
    'BankStatementOCR'
] 