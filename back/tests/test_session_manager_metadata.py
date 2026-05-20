#!/usr/bin/env python3
"""Tests for session metadata written to parameter_history.json."""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import session_manager as session_module
from core.data_models import TradingParameters
from core.session_manager import SessionManager


class FakeTreatmentManager:
    def get_treatment_for_market(self, treatment_index):
        return {"num_noise_traders": 10 + treatment_index}

    def get_merged_params(self, treatment_index, base_params):
        merged = base_params.copy()
        merged["num_noise_traders"] = 20 + treatment_index
        return merged

    def get_treatment(self, treatment_index):
        return {"name": f"Treatment {treatment_index}", "num_noise_traders": 10 + treatment_index}


async def _run_lab_market_start_logs_lab_treatment_group(monkeypatch):
    records = []
    monkeypatch.setattr(session_module, "treatment_manager", FakeTreatmentManager())
    monkeypatch.setattr(
        session_module.parameter_logger,
        "log_market_start",
        lambda **kwargs: records.append(kwargs),
    )

    manager = SessionManager()
    params = TradingParameters(predefined_goals=[0, 10], num_noise_traders=1)

    manager.user_treatment_groups["LAB_T2_P1"] = 1
    manager.user_treatment_groups["LAB_T2_P2"] = 1
    manager.user_group_indices["LAB_T2_P1"] = 0
    manager.user_group_indices["LAB_T2_P2"] = 1

    session_1, _, _, _ = await manager.join_session("LAB_T2_P1", params)
    session_2, _, _, _ = await manager.join_session("LAB_T2_P2", params)
    assert session_1 == session_2 == "T1_M0"

    await manager.start_trading_session("LAB_T2_P1")

    assert len(records) == 1
    assert records[0]["session_id"] == "T1_M0"
    assert records[0]["treatment_index"] == 1
    assert records[0]["treatment_name"] == "Treatment 1"
    assert records[0]["parameters"]["num_noise_traders"] == 11


def test_lab_market_start_logs_lab_treatment_group(monkeypatch):
    asyncio.run(_run_lab_market_start_logs_lab_treatment_group(monkeypatch))
