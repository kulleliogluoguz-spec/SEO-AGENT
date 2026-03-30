"""
Training / Adaptation Layer — Dataset scaffolding and fine-tuning pipeline stubs.

Staged approach:
- Stage 1: Prompt + routing + tools (current)
- Stage 2: Retrieval + examples (few-shot injection)
- Stage 3: LoRA adapters (domain specialization)
- Stage 4: SFT (supervised fine-tuning with curated data)
- Stage 5: DPO (preference learning from accepted/rejected pairs)
- Stage 6: GRPO/RL (reward-modeled training if justified)

This module provides:
- Dataset schemas for all training data types
- Data collection hooks for the platform
- Export utilities for training pipelines
- Adapter management stubs
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DatasetType(str, Enum):
    SFT = "sft"                        # Supervised fine-tuning pairs
    PREFERENCE = "preference"           # DPO/RLHF preference pairs
    CLASSIFICATION = "classification"   # Label classification examples
    RECOMMENDATION = "recommendation"   # Recommendation-evidence pairs
    CONTENT = "content"                 # Content quality examples
    EVALUATION = "evaluation"           # Eval gold-standard examples


class DataQuality(str, Enum):
    GOLD = "gold"          # Human-verified, high quality
    SILVER = "silver"      # Programmatically filtered, good quality
    BRONZE = "bronze"      # Raw collection, unverified
    REJECTED = "rejected"  # Explicitly rejected by human


# ─── Dataset Schemas ──────────────────────────────────────────────


@dataclass
class SFTExample:
    """Supervised fine-tuning example (instruction-response pair)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    input_context: str = ""
    output: str = ""
    system_prompt: str = ""
    category: str = ""          # e.g. "seo_audit", "recommendation", "content"
    quality: DataQuality = DataQuality.BRONZE
    source: str = ""            # Where this came from
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_training_format(self) -> dict:
        """Convert to standard training format."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        user_content = self.instruction
        if self.input_context:
            user_content += f"\n\nContext:\n{self.input_context}"
        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages, "category": self.category, "quality": self.quality.value}


@dataclass
class PreferenceExample:
    """DPO preference pair (chosen vs rejected)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    input_context: str = ""
    chosen_output: str = ""     # Preferred/accepted response
    rejected_output: str = ""   # Rejected/worse response
    category: str = ""
    rejection_reason: str = ""  # Why the rejected output was worse
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_training_format(self) -> dict:
        return {
            "prompt": self.instruction,
            "chosen": self.chosen_output,
            "rejected": self.rejected_output,
            "category": self.category,
        }


@dataclass
class RecommendationTrainingExample:
    """Recommendation-evidence training pair."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    site_context: dict[str, Any] = field(default_factory=dict)
    analysis_data: dict[str, Any] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""           # "implemented", "approved", "rejected", "deferred"
    impact_data: dict[str, Any] = field(default_factory=dict)  # Post-implementation metrics
    quality: DataQuality = DataQuality.BRONZE
    created_at: float = field(default_factory=time.time)


@dataclass
class ContentTrainingExample:
    """Content quality training example."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_type: str = ""      # "blog_post", "landing_page", "social_post"
    input_brief: str = ""
    generated_content: str = ""
    edited_content: str = ""    # Human-edited version
    approval_status: str = ""   # "approved", "rejected", "revised"
    quality_score: float = 0.0  # Human-assigned quality score
    edit_distance: float = 0.0  # How much was changed
    channel: str = ""           # "web", "linkedin", "twitter"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ─── Dataset Manager ──────────────────────────────────────────────


class DatasetManager:
    """
    Manages training datasets with collection, storage, and export.

    In production, datasets would be stored in the database or a
    dedicated data store. Currently in-memory with export utilities.
    """

    def __init__(self) -> None:
        self._sft_examples: list[SFTExample] = []
        self._preference_examples: list[PreferenceExample] = []
        self._recommendation_examples: list[RecommendationTrainingExample] = []
        self._content_examples: list[ContentTrainingExample] = []

    # ── Collection Hooks ──────────────────────────────────────────

    def record_sft_example(
        self,
        instruction: str,
        output: str,
        category: str = "",
        quality: DataQuality = DataQuality.BRONZE,
        **kwargs: Any,
    ) -> str:
        """Record a supervised fine-tuning example from platform usage."""
        example = SFTExample(
            instruction=instruction,
            output=output,
            category=category,
            quality=quality,
            source="platform_usage",
            **kwargs,
        )
        self._sft_examples.append(example)
        return example.id

    def record_preference(
        self,
        instruction: str,
        chosen: str,
        rejected: str,
        category: str = "",
        rejection_reason: str = "",
    ) -> str:
        """Record when a user accepts one output and rejects another."""
        example = PreferenceExample(
            instruction=instruction,
            chosen_output=chosen,
            rejected_output=rejected,
            category=category,
            rejection_reason=rejection_reason,
            source="user_feedback",
        )
        self._preference_examples.append(example)
        return example.id

    def record_recommendation_outcome(
        self,
        site_context: dict,
        analysis_data: dict,
        recommendation: dict,
        outcome: str,
        impact_data: dict | None = None,
    ) -> str:
        """Record recommendation approval/rejection and eventual impact."""
        example = RecommendationTrainingExample(
            site_context=site_context,
            analysis_data=analysis_data,
            recommendation=recommendation,
            outcome=outcome,
            impact_data=impact_data or {},
            quality=DataQuality.SILVER if outcome == "implemented" else DataQuality.BRONZE,
        )
        self._recommendation_examples.append(example)
        return example.id

    def record_content_edit(
        self,
        content_type: str,
        generated: str,
        edited: str,
        approval_status: str,
        quality_score: float = 0.0,
        channel: str = "web",
    ) -> str:
        """Record when a user edits AI-generated content."""
        # Calculate edit distance ratio
        edit_dist = self._simple_edit_ratio(generated, edited)
        example = ContentTrainingExample(
            content_type=content_type,
            generated_content=generated,
            edited_content=edited,
            approval_status=approval_status,
            quality_score=quality_score,
            edit_distance=edit_dist,
            channel=channel,
        )
        self._content_examples.append(example)
        return example.id

    # ── Export Utilities ───────────────────────────────────────────

    def export_sft_dataset(
        self,
        min_quality: DataQuality = DataQuality.BRONZE,
        category: str = "",
    ) -> list[dict]:
        """Export SFT examples in training format."""
        quality_order = {DataQuality.GOLD: 3, DataQuality.SILVER: 2, DataQuality.BRONZE: 1, DataQuality.REJECTED: 0}
        min_level = quality_order.get(min_quality, 0)

        examples = [
            ex for ex in self._sft_examples
            if quality_order.get(ex.quality, 0) >= min_level
            and (not category or ex.category == category)
        ]
        return [ex.to_training_format() for ex in examples]

    def export_preference_dataset(self, category: str = "") -> list[dict]:
        """Export preference pairs in DPO training format."""
        examples = [
            ex for ex in self._preference_examples
            if not category or ex.category == category
        ]
        return [ex.to_training_format() for ex in examples]

    def export_to_jsonl(self, dataset_type: DatasetType, filepath: str, **filters: Any) -> int:
        """Export dataset to JSONL file for training pipelines."""
        if dataset_type == DatasetType.SFT:
            data = self.export_sft_dataset(**filters)
        elif dataset_type == DatasetType.PREFERENCE:
            data = self.export_preference_dataset(**filters)
        else:
            data = []

        with open(filepath, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        logger.info(f"Exported {len(data)} examples to {filepath}")
        return len(data)

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "sft_examples": len(self._sft_examples),
            "preference_examples": len(self._preference_examples),
            "recommendation_examples": len(self._recommendation_examples),
            "content_examples": len(self._content_examples),
            "sft_by_quality": {
                q.value: sum(1 for ex in self._sft_examples if ex.quality == q)
                for q in DataQuality
            },
            "sft_by_category": self._count_by_field(self._sft_examples, "category"),
            "recommendation_by_outcome": self._count_by_field(self._recommendation_examples, "outcome"),
            "content_by_status": self._count_by_field(self._content_examples, "approval_status"),
        }

    @staticmethod
    def _count_by_field(items: list, field_name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items:
            val = getattr(item, field_name, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts

    @staticmethod
    def _simple_edit_ratio(a: str, b: str) -> float:
        """Simple character-level edit distance ratio."""
        if not a and not b:
            return 0.0
        if not a or not b:
            return 1.0
        common = sum(1 for ca, cb in zip(a, b) if ca == cb)
        return 1.0 - (common / max(len(a), len(b)))


# ─── Adapter Manager (Stubs) ─────────────────────────────────────


@dataclass
class LoRAAdapter:
    """A LoRA adapter configuration."""
    id: str
    name: str
    base_model: str
    adapter_path: str = ""
    rank: int = 16
    alpha: int = 32
    target_modules: list[str] = field(default_factory=lambda: ["q_proj", "v_proj"])
    trained_on: str = ""
    quality_score: float = 0.0
    active: bool = False
    created_at: float = field(default_factory=time.time)


class AdapterManager:
    """
    Manages LoRA adapters for model specialization.

    This is a stub for future fine-tuning integration.
    In production, adapters would be loaded into vLLM or merged into models.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, LoRAAdapter] = {}

    def register(self, adapter: LoRAAdapter) -> None:
        self._adapters[adapter.id] = adapter

    def list_adapters(self) -> list[dict]:
        return [
            {
                "id": a.id,
                "name": a.name,
                "base_model": a.base_model,
                "rank": a.rank,
                "active": a.active,
                "quality_score": a.quality_score,
            }
            for a in self._adapters.values()
        ]

    def activate(self, adapter_id: str) -> bool:
        if adapter_id in self._adapters:
            self._adapters[adapter_id].active = True
            return True
        return False

    def deactivate(self, adapter_id: str) -> bool:
        if adapter_id in self._adapters:
            self._adapters[adapter_id].active = False
            return True
        return False


# Singletons
_dataset_manager: Optional[DatasetManager] = None
_adapter_manager: Optional[AdapterManager] = None


def get_dataset_manager() -> DatasetManager:
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager()
    return _dataset_manager


def get_adapter_manager() -> AdapterManager:
    global _adapter_manager
    if _adapter_manager is None:
        _adapter_manager = AdapterManager()
    return _adapter_manager
