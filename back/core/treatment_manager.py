"""
Treatment Manager - Handles YAML-based per-market treatment configurations.

Each treatment defines trader composition and settings for a specific market
in the sequence. When a human plays their Nth market, treatment N is applied.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from utils.utils import setup_custom_logger

logger = setup_custom_logger(__name__)

TREATMENTS_FILE = Path("config/treatments.yaml")


@dataclass
class Treatment:
    name: str
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, **self.settings}


class TreatmentManager:
    def __init__(self, file_path: Path = TREATMENTS_FILE):
        self.file_path = file_path
        self.treatments: List[Treatment] = []
        self._ensure_config_dir()
        self._load_from_file()
    
    def _ensure_config_dir(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_from_file(self):
        if not self.file_path.exists():
            logger.info(f"No treatments file at {self.file_path}, using empty config")
            self.treatments = []
            return
        
        try:
            with open(self.file_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            self.treatments = []
            for t in data.get('treatments', []):
                name = t.pop('name', f"Treatment {len(self.treatments) + 1}")
                self.treatments.append(Treatment(name=name, settings=t))
            
            logger.info(f"Loaded {len(self.treatments)} treatments from {self.file_path}")
        except Exception as e:
            logger.error(f"Error loading treatments: {e}")
            self.treatments = []
    
    def _save_to_file(self):
        try:
            data = {
                'treatments': [t.to_dict() for t in self.treatments]
            }
            with open(self.file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved {len(self.treatments)} treatments to {self.file_path}")
        except Exception as e:
            logger.error(f"Error saving treatments: {e}")
            raise
    
    def update_from_yaml(self, yaml_content: str) -> int:
        try:
            data = yaml.safe_load(yaml_content) or {}
            
            self.treatments = []
            for t in data.get('treatments', []):
                name = t.pop('name', f"Treatment {len(self.treatments) + 1}")
                self.treatments.append(Treatment(name=name, settings=t))
            
            self._save_to_file()
            logger.info(f"Updated treatments from YAML: {len(self.treatments)} treatments")
            return len(self.treatments)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML: {e}")
            raise ValueError(f"Invalid YAML: {e}")
    
    def get_treatment_for_market(self, market_index: int) -> Optional[Dict[str, Any]]:
        if not self.treatments:
            return None
        
        if market_index < 0:
            return None
        
        if market_index >= len(self.treatments):
            return self.treatments[-1].settings if self.treatments else None
        
        return self.treatments[market_index].settings
    
    def get_treatment(self, market_index: int) -> Optional[Dict[str, Any]]:
        """Get full treatment info including name for a given market index."""
        if not self.treatments:
            return None
        
        if market_index < 0:
            return None
        
        if market_index >= len(self.treatments):
            return self.treatments[-1].to_dict() if self.treatments else None
        
        return self.treatments[market_index].to_dict()
    
    def get_merged_params(self, market_index: int, base_params: Dict[str, Any]) -> Dict[str, Any]:
        treatment = self.get_treatment_for_market(market_index)
        if not treatment:
            return base_params
        
        merged = base_params.copy()
        merged.update(treatment)
        logger.info(f"Applied treatment {market_index}: {treatment}")
        return merged
    
    def get_all_treatments(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.treatments]
    
    def get_yaml_content(self) -> str:
        if not self.treatments:
            return "treatments: []\n"
        
        data = {'treatments': [t.to_dict() for t in self.treatments]}
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    def set_treatments(self, treatments_list: List[Dict[str, Any]]) -> int:
        """Set treatments from a list of dicts (each dict has 'name' + settings).

        This is the unified way to configure treatments -- no YAML needed.
        """
        self.treatments = []
        for t in treatments_list:
            t = dict(t)  # shallow copy so pop doesn't mutate caller
            name = t.pop('name', f"Treatment {len(self.treatments) + 1}")
            self.treatments.append(Treatment(name=name, settings=t))
        self._save_to_file()
        logger.info(f"Set {len(self.treatments)} treatments from list")
        return len(self.treatments)

    def clear(self):
        self.treatments = []
        self._save_to_file()


treatment_manager = TreatmentManager()
