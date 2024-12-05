from typing import Dict, Literal, ClassVar

from pydantic import BaseModel, Field, model_validator

#TODO optimize this class to follow the DRY principle

class PortfolioWeights(BaseModel):
    Current: Dict[str, float]
    Simulated: Dict[str, float]

class PortfolioWeight(BaseModel):
    Current: Dict[str, float]

    @model_validator(mode='before')
    def adjust_weights(cls, values):
        for key in ['Current', 'Simulated']:
            if key in values:
                total_weight = sum(values[key].values())
                if total_weight > 1:
                    reduction_factor = 1 / total_weight
                    for sub_key in values[key]:
                        values[key][sub_key] *= reduction_factor
        return values


class PortfolioAnalysisRequest(BaseModel):
    weights: PortfolioWeights
    language: Literal["nl", "fr", "en"] = Field(..., description="Language of output")
    # Language mapping
    # Language mapping
    LANGUAGE_MAP: ClassVar[dict[str, str]] = {
        "nl": "Dutch",
        "fr": "French",
        "en": "English",
    }

    @property
    def full_language_name(self) -> str:
        """Returns the full language name based on the language code."""
        return self.LANGUAGE_MAP.get(self.language, "Unknown Language")

    def format_weights(self, include_current: bool = True, include_simulated: bool = True) -> str:
        formatted_weights = []
        if include_current:
            current_weights = ", ".join([f"{k}: {v:.2%}" for k, v in self.weights.Current.items()])
            formatted_weights.append(f"Current: {current_weights}")
        if include_simulated:
            simulated_weights = ", ".join([f"{k}: {v:.2%}" for k, v in self.weights.Simulated.items()])
            formatted_weights.append(f"Simulated: {simulated_weights}")
        return "; ".join(formatted_weights)

class PortfolioInputs(BaseModel):
    weights: PortfolioWeight
    language: Literal["nl", "fr", "en"] = Field(..., description="Language of output")

    LANGUAGE_MAP: ClassVar[dict[str, str]] = {
        "nl": "Dutch",
        "fr": "French",
        "en": "English",
    }

    @property
    def full_language_name(self) -> str:
        """Returns the full language name based on the language code."""
        return self.LANGUAGE_MAP.get(self.language, "Unknown Language")
    
