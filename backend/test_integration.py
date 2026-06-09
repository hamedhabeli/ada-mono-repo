# test_integration.py
import pytest
from fastapi.testclient import TestClient
from main import app

# استفاده از TestClient برای شبیه‌سازی درخواست‌های HTTP بدون نیاز به روشن کردن سرور
client = TestClient(app)

def test_solve_endpoint_integration():
    """تست یکپارچگی: آیا اندپوینت شروع دیالکتیک به درستی Thread را می‌سازد؟"""
    payload = {
        "thread_id": "test-thread-999",
        "problem": "Find x where x > 10 and x < 5"
    }
    
    response = client.post("/api/v1/solve", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test-thread-999"
    assert data["status"] == "processing_started"

def test_oracle_injection_without_deadlock():
    """تست یکپارچگی: سیستم باید از تزریق اوراکل در زمانی که بن‌بستی وجود ندارد جلوگیری کند"""
    payload = {
        "thread_id": "test-thread-999",
        "meta_axiom": "x is a complex number"
    }
    
    response = client.post("/api/v1/oracle/inject", json=payload)
    
    # چون گراف در حالت توقف (Interrupt) نیست، باید خطای 400 برگرداند
    assert response.status_code == 400
    assert "Not waiting for oracle" in response.json()["detail"]