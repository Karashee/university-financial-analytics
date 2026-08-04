"""Unit tests for ORM models and Pydantic schemas."""
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

# Import ORM models
from app.models import (
    Base,
    Role,
    User,
    Department,
    Budget,
    ExpenditureTransaction,
    AnomalyResult,
    ForecastResult,
    BudgetUtilizationReport,
    TrendSummary
)

# Import Pydantic schemas
from app.schemas import (
    UserCreate,
    UserRead,
    Token,
    DepartmentCreate,
    DepartmentRead,
    BudgetCreate,
    BudgetRead,
    TransactionCreate,
    TransactionRead,
    AnomalyResultRead,
    ForecastResultRead,
    BudgetUtilizationReportRead,
    TrendSummaryRead
)


class TestORMModels:
    """Test ORM model instantiation and attribute access."""
    
    def test_role_model(self):
        """Test Role model instantiation."""
        role = Role(id=1, name="Admin", description="Administrator role")
        assert role.id == 1
        assert role.name == "Admin"
        assert role.description == "Administrator role"
    
    def test_user_model(self):
        """Test User model instantiation with UUID."""
        user_id = uuid4()
        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            hashed_password="hashedpw123",
            role_id=1,
            department_id="DEPT01",
            is_active=True
        )
        assert user.id == user_id
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.department_id == "DEPT01"
    
    def test_department_model(self):
        """Test Department model instantiation."""
        dept = Department(
            department_id="DEPT01",
            department_name="Engineering",
            department_type="Technical"
        )
        assert dept.department_id == "DEPT01"
        assert dept.department_name == "Engineering"
        assert dept.department_type == "Technical"
    
    def test_budget_model(self):
        """Test Budget model instantiation."""
        budget = Budget(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            budget_allocation=Decimal("100000.50")
        )
        assert budget.id == 1
        assert budget.department_id == "DEPT01"
        assert budget.fiscal_year == 2024
        assert budget.budget_allocation == Decimal("100000.50")
    
    def test_expenditure_transaction_model(self):
        """Test ExpenditureTransaction model instantiation."""
        transaction = ExpenditureTransaction(
            transaction_id="TXN001",
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=3,
            transaction_date=date(2024, 3, 15),
            transaction_amount=Decimal("5000.00"),
            expenditure_category="Software",
            vendor_category="IT Services",
            monthly_expenditure=Decimal("25000.00"),
            is_anomaly_ground_truth=0,
            anomaly_type_ground_truth="Normal"
        )
        assert transaction.transaction_id == "TXN001"
        assert transaction.department_id == "DEPT01"
        assert transaction.fiscal_year == 2024
        assert transaction.fiscal_month == 3
        assert transaction.transaction_amount == Decimal("5000.00")
        assert transaction.expenditure_category == "Software"
    
    def test_anomaly_result_model(self):
        """Test AnomalyResult model instantiation with UUID."""
        anomaly_id = uuid4()
        anomaly = AnomalyResult(
            id=anomaly_id,
            transaction_id="TXN001",
            anomaly_score=Decimal("0.95"),
            is_anomaly_predicted=True,
            explanation="High expenditure detected",
            model_version="v1.0"
        )
        assert anomaly.id == anomaly_id
        assert anomaly.transaction_id == "TXN001"
        assert anomaly.anomaly_score == Decimal("0.95")
        assert anomaly.is_anomaly_predicted is True
    
    def test_forecast_result_model(self):
        """Test ForecastResult model instantiation with UUID."""
        forecast_id = uuid4()
        forecast = ForecastResult(
            id=forecast_id,
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=4,
            predicted_expenditure=Decimal("30000.00"),
            mae_context=Decimal("1500.00"),
            model_version="v1.0"
        )
        assert forecast.id == forecast_id
        assert forecast.department_id == "DEPT01"
        assert forecast.fiscal_year == 2024
        assert forecast.predicted_expenditure == Decimal("30000.00")
    
    def test_budget_utilization_report_model(self):
        """Test BudgetUtilizationReport model instantiation."""
        report = BudgetUtilizationReport(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=3,
            expenditure_category="Software",
            total_transaction_amount=Decimal("25000.00"),
            monthly_expenditure=Decimal("25000.00"),
            budget_allocation=Decimal("100000.00"),
            utilization_percentage=Decimal("25.0000")
        )
        assert report.id == 1
        assert report.department_id == "DEPT01"
        assert report.utilization_percentage == Decimal("25.0000")
    
    def test_trend_summary_model(self):
        """Test TrendSummary model instantiation."""
        trend = TrendSummary(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            total_annual_expenditure=Decimal("300000.00"),
            avg_monthly_expenditure=Decimal("25000.00"),
            avg_growth_rate=Decimal("0.05"),
            variance_from_historical_avg=Decimal("5000.00")
        )
        assert trend.id == 1
        assert trend.department_id == "DEPT01"
        assert trend.total_annual_expenditure == Decimal("300000.00")


class TestPydanticSchemas:
    """Test Pydantic schema instantiation and model_dump."""
    
    def test_user_create_schema(self):
        """Test UserCreate schema."""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
            role_id=1,
            department_id="DEPT01"
        )
        assert user_data.username == "testuser"
        assert user_data.email == "test@example.com"
        assert user_data.role_id == 1
        dump = user_data.model_dump()
        assert "username" in dump
        assert "password" in dump
    
    def test_user_read_schema(self):
        """Test UserRead schema."""
        user_id = uuid4()
        user_data = UserRead(
            id=user_id,
            username="testuser",
            email="test@example.com",
            role_id=1,
            is_active=True,
            department_id="DEPT01"
        )
        assert user_data.id == user_id
        assert user_data.is_active is True
        dump = user_data.model_dump()
        assert "id" in dump
        assert "username" in dump
    
    def test_token_schema(self):
        """Test Token schema."""
        token = Token(access_token="abc123", token_type="bearer")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"
        dump = token.model_dump()
        assert "access_token" in dump
    
    def test_department_create_schema(self):
        """Test DepartmentCreate schema."""
        dept_data = DepartmentCreate(
            department_id="DEPT01",
            department_name="Engineering",
            department_type="Technical"
        )
        assert dept_data.department_id == "DEPT01"
        dump = dept_data.model_dump()
        assert "department_name" in dump
    
    def test_budget_create_schema(self):
        """Test BudgetCreate schema with Decimal."""
        budget_data = BudgetCreate(
            department_id="DEPT01",
            fiscal_year=2024,
            budget_allocation=Decimal("100000.50")
        )
        assert budget_data.budget_allocation == Decimal("100000.50")
        dump = budget_data.model_dump()
        assert "budget_allocation" in dump
    
    def test_transaction_create_schema(self):
        """Test TransactionCreate schema."""
        txn_data = TransactionCreate(
            transaction_id="TXN001",
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=3,
            transaction_date=date(2024, 3, 15),
            transaction_amount=Decimal("5000.00"),
            expenditure_category="Software",
            vendor_category="IT Services"
        )
        assert txn_data.transaction_id == "TXN001"
        assert txn_data.transaction_amount == Decimal("5000.00")
        dump = txn_data.model_dump()
        assert "transaction_id" in dump
        assert "expenditure_category" in dump
    
    def test_anomaly_result_read_schema(self):
        """Test AnomalyResultRead schema."""
        anomaly_id = uuid4()
        anomaly_data = AnomalyResultRead(
            id=anomaly_id,
            transaction_id="TXN001",
            anomaly_score=Decimal("0.95"),
            is_anomaly_predicted=True,
            explanation="High expenditure",
            model_version="v1.0",
            detected_at=datetime.now()
        )
        assert anomaly_data.id == anomaly_id
        assert anomaly_data.is_anomaly_predicted is True
        dump = anomaly_data.model_dump()
        assert "anomaly_score" in dump
    
    def test_forecast_result_read_schema(self):
        """Test ForecastResultRead schema."""
        forecast_id = uuid4()
        forecast_data = ForecastResultRead(
            id=forecast_id,
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=4,
            predicted_expenditure=Decimal("30000.00"),
            mae_context=Decimal("1500.00"),
            model_version="v1.0",
            generated_at=datetime.now()
        )
        assert forecast_data.predicted_expenditure == Decimal("30000.00")
        dump = forecast_data.model_dump()
        assert "predicted_expenditure" in dump
    
    def test_department_read_schema(self):
        """Test DepartmentRead schema."""
        dept_data = DepartmentRead(
            department_id="DEPT01",
            department_name="Engineering",
            department_type="Technical"
        )
        assert dept_data.department_id == "DEPT01"
        assert dept_data.department_name == "Engineering"
        dump = dept_data.model_dump()
        assert "department_name" in dump
    
    def test_budget_read_schema(self):
        """Test BudgetRead schema with Decimal."""
        budget_data = BudgetRead(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            budget_allocation=Decimal("100000.50")
        )
        assert budget_data.id == 1
        assert budget_data.budget_allocation == Decimal("100000.50")
        dump = budget_data.model_dump()
        assert "budget_allocation" in dump
    
    def test_transaction_read_schema(self):
        """Test TransactionRead schema."""
        txn_data = TransactionRead(
            transaction_id="TXN001",
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=3,
            transaction_date=date(2024, 3, 15),
            transaction_amount=Decimal("5000.00"),
            expenditure_category="Software",
            vendor_category="IT Services",
            monthly_expenditure=Decimal("25000.00"),
            budget_utilization_percentage=Decimal("20.0000"),
            expenditure_variance=None,
            historical_average_expenditure=None,
            expenditure_growth_rate=None,
            is_anomaly_ground_truth=0,
            anomaly_type_ground_truth="Normal",
            created_at=date(2024, 3, 15)
        )
        assert txn_data.transaction_id == "TXN001"
        assert txn_data.transaction_amount == Decimal("5000.00")
        dump = txn_data.model_dump()
        assert "transaction_id" in dump
    
    def test_budget_utilization_report_read_schema(self):
        """Test BudgetUtilizationReportRead schema."""
        report_data = BudgetUtilizationReportRead(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            fiscal_month=3,
            expenditure_category="Software",
            total_transaction_amount=Decimal("25000.00"),
            monthly_expenditure=Decimal("25000.00"),
            budget_allocation=Decimal("100000.00"),
            utilization_percentage=Decimal("25.0000"),
            computed_at=datetime.now()
        )
        assert report_data.id == 1
        assert report_data.utilization_percentage == Decimal("25.0000")
        dump = report_data.model_dump()
        assert "utilization_percentage" in dump
    
    def test_trend_summary_read_schema(self):
        """Test TrendSummaryRead schema."""
        trend_data = TrendSummaryRead(
            id=1,
            department_id="DEPT01",
            fiscal_year=2024,
            total_annual_expenditure=Decimal("300000.00"),
            avg_monthly_expenditure=Decimal("25000.00"),
            avg_growth_rate=Decimal("0.05"),
            variance_from_historical_avg=Decimal("5000.00"),
            computed_at=datetime.now()
        )
        assert trend_data.id == 1
        assert trend_data.total_annual_expenditure == Decimal("300000.00")
        dump = trend_data.model_dump()
        assert "total_annual_expenditure" in dump
