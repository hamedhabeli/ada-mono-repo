# test_unit.py
import pytest
from z3 import Solver, Int, sat

def test_symbolic_engine_contradiction():
    """تست موتور نمادین: آیا تناقض‌ها را درست تشخیص می‌دهد و هسته متناقض را برمی‌گرداند؟"""
    solver = Solver()
    solver.set(unsat_core=True)
    
    # شبیه‌سازی یک محیط محلی
    local_env = {"Int": Int}
    exec("x, y = Int('x'), Int('y')", {}, local_env)
    x, y = local_env['x'], local_env['y']
    
    # تزریق دو شرط متناقض
    solver.assert_and_track(x > 5, "C_1")
    solver.assert_and_track(x < 3, "C_2")
    
    result = solver.check()
    
    assert result != sat, "Solver should have found a contradiction!"
    
    core = [str(c) for c in solver.unsat_core()]
    assert "C_1" in core and "C_2" in core, "Unsat Core must contain the conflicting constraints"