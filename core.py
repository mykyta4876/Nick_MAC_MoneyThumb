import time
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import date
from .models import MoneyThumbResponse, BankAccount
from .ocr_engine import BankStatementOCR
from .classifiers import TransactionClassifier, FraudDetector
from .analyzers import (
    MCADetection, DailyBalanceCalculator, CashFlowAnalysis,
    MonthlyStatsCalculator, UnderwritingMetricsCalculator
)


class MoneyThumbSystem:
    """
    Main MoneyThumb system orchestrating all components
    """

    def __init__(self):
        self.ocr_engine = BankStatementOCR()
        self.classifier = TransactionClassifier()
        self.fraud_detector = FraudDetector()
        self.mca_detector = MCADetection()
        self.balance_calculator = DailyBalanceCalculator()
        self.cashflow_analyzer = CashFlowAnalysis()
        self.monthly_calculator = MonthlyStatsCalculator()
        self.metrics_calculator = UnderwritingMetricsCalculator()

    def process_bank_statement(self, pdf_path: str) -> MoneyThumbResponse:
        """
        Complete processing pipeline for a bank statement
        """
        start_time = time.time()
        
        # 1. OCR Processing
        ocr_result = self.ocr_engine.process_statement(pdf_path)
        account = ocr_result['account']
        raw_transactions = ocr_result['transactions']
        base_confidence = ocr_result['confidence_score']
        
        if not raw_transactions:
            return self._empty_response(account, time.time() - start_time)
        
        # 2. Transaction Classification
        classified_transactions = []
        for transaction in raw_transactions:
            classified_transaction = self.classifier.classify_transaction(transaction)
            classified_transactions.append(classified_transaction)
        
        # 3. MCA Position Detection
        mca_positions = self.mca_detector.detect_positions(classified_transactions)
        
        # 4. Monthly Statistics Calculation
        monthly_summaries = self._calculate_monthly_summaries(classified_transactions)
        
        # 5. Underwriting Metrics
        metrics = self.metrics_calculator.calculate_metrics(
            monthly_summaries, classified_transactions, mca_positions
        )
        
        # 6. Fraud Detection
        fraud_score, fraud_factors = self.fraud_detector.calculate_thumbprint_score(
            classified_transactions
        )
        metrics.fraud_score = fraud_score
        
        # 7. Cash Flow Analysis
        cash_flow = self._calculate_overall_cashflow(monthly_summaries, mca_positions)
        
        # 8. Final confidence score
        final_confidence = self._calculate_final_confidence(
            base_confidence, classified_transactions, fraud_score
        )
        
        processing_time = time.time() - start_time
        
        return MoneyThumbResponse(
            account=account,
            transactions=classified_transactions,
            monthly_summaries=monthly_summaries,
            mca_positions=mca_positions,
            metrics=metrics,
            cash_flow=cash_flow,
            confidence_score=final_confidence,
            processing_time=processing_time
        )

    def _calculate_monthly_summaries(self, transactions):
        """
        Calculate monthly summaries for the statement period
        """
        if not transactions:
            return []
        
        # Get unique months from transactions
        months = set()
        for transaction in transactions:
            month_str = transaction.date.strftime('%Y-%m')
            months.add(month_str)
        
        monthly_summaries = []
        for month in sorted(months):
            summary = self.monthly_calculator.calculate_monthly_stats(transactions, month)
            monthly_summaries.append(summary)
        
        return monthly_summaries

    def _calculate_overall_cashflow(self, monthly_summaries, mca_positions):
        """
        Calculate overall cash flow metrics
        """
        if not monthly_summaries:
            return self.cashflow_analyzer.analyze_monthly_cashflow({})
        
        # Aggregate data from all months
        total_deposits = sum(m.total_deposits for m in monthly_summaries)
        total_true_revenue = sum(m.true_revenue for m in monthly_summaries)
        
        # Estimate operating expenses (simplified)
        operating_expenses = total_true_revenue * Decimal('0.7')  # Assume 70% of revenue
        
        # Calculate MCA burden
        monthly_mca_payments = []
        for position in mca_positions:
            # Estimate monthly payment (daily * 20 business days)
            monthly_payment = position.daily_payment * 20
            monthly_mca_payments.append(monthly_payment)
        
        month_data = {
            'all_deposits': [total_deposits],
            'all_withdrawals': [operating_expenses],
            'true_revenue': total_true_revenue,
            'operating_expenses': operating_expenses,
            'mca_payments': monthly_mca_payments
        }
        
        return self.cashflow_analyzer.analyze_monthly_cashflow(month_data)

    def _calculate_final_confidence(self, base_confidence: float, 
                                  transactions, fraud_score: int) -> float:
        """
        Calculate final confidence score considering all factors
        """
        confidence = base_confidence
        
        # Reduce confidence for high fraud scores
        if fraud_score > 500:
            confidence -= 0.3
        elif fraud_score > 200:
            confidence -= 0.1
        
        # Reduce confidence if too few transactions
        if len(transactions) < 20:
            confidence -= 0.2
        
        # Boost confidence if we have good transaction variety
        transaction_types = set(t.category for t in transactions if t.category)
        if len(transaction_types) >= 3:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))

    def _empty_response(self, account: BankAccount, processing_time: float) -> MoneyThumbResponse:
        """
        Return empty response when no transactions found
        """
        from .models import CashFlowMetrics, UnderwritingMetrics
        
        empty_metrics = UnderwritingMetrics(
            average_monthly_revenue=Decimal('0'),
            revenue_stability=0.0,
            days_cash_on_hand=0.0,
            mca_payment_ratio=0.0,
            deposit_frequency=0.0,
            nsf_rate=0.0,
            negative_day_rate=0.0,
            fraud_score=0
        )
        
        empty_cashflow = CashFlowMetrics(
            gross_cash_in=Decimal('0'),
            gross_cash_out=Decimal('0'),
            net_cash_flow=Decimal('0'),
            true_cash_flow=Decimal('0'),
            mca_burden=Decimal('0'),
            free_cash_flow=Decimal('0')
        )
        
        return MoneyThumbResponse(
            account=account,
            transactions=[],
            monthly_summaries=[],
            mca_positions=[],
            metrics=empty_metrics,
            cash_flow=empty_cashflow,
            confidence_score=0.0,
            processing_time=processing_time
        )

    def generate_json_report(self, response: MoneyThumbResponse) -> Dict:
        """
        Generate JSON report in MoneyThumb API format
        """
        return {
            "account": {
                "bank": response.account.bank_name,
                "account_last4": response.account.account_number.split('*')[-1],
                "statement_period": {
                    "start": response.account.statement_start.isoformat(),
                    "end": response.account.statement_end.isoformat()
                }
            },
            "metrics": {
                "average_monthly_revenue": float(response.metrics.average_monthly_revenue),
                "true_revenue_total": float(sum(m.true_revenue for m in response.monthly_summaries)),
                "gross_deposits": float(sum(m.total_deposits for m in response.monthly_summaries)),
                "mca_positions_detected": len(response.mca_positions),
                "total_mca_payments": float(sum(pos.daily_payment * 20 for pos in response.mca_positions)),
                "days_negative": sum(m.days_negative for m in response.monthly_summaries),
                "nsf_count": len([t for t in response.transactions if 'NSF' in t.description.upper()]),
                "fraud_score": response.metrics.fraud_score
            },
            "mca_positions": [
                {
                    "lender": pos.lender_name,
                    "daily_payment": float(pos.daily_payment),
                    "position": pos.position_number
                }
                for pos in response.mca_positions
            ],
            "monthly_summary": [
                {
                    "month": m.month,
                    "true_revenue": float(m.true_revenue),
                    "gross_deposits": float(m.total_deposits),
                    "ending_balance": float(m.ending_balance),
                    "days_negative": m.days_negative
                }
                for m in response.monthly_summaries
            ],
            "confidence_score": response.confidence_score,
            "processing_time": response.processing_time
        }