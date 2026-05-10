"""Per-model OpenRouter pricing in USD per million tokens.

Source-of-truth is OpenRouter's pricing page; these are conservative ceilings
used for budget tracking. The exact dollars-and-cents accounting can be
reconciled against OpenRouter's `usage` field later if needed.
"""
from decimal import Decimal

# (input_per_million, output_per_million) in USD
PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "anthropic/claude-haiku-4-5": (Decimal("0.80"), Decimal("4.00")),
    "anthropic/claude-sonnet-4-6": (Decimal("3.00"), Decimal("15.00")),
    "anthropic/claude-opus-4-7": (Decimal("15.00"), Decimal("75.00")),
    "openai/gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "openai/gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "google/gemini-2.5-flash": (Decimal("0.10"), Decimal("0.40")),
}

_FALLBACK = (Decimal("5.00"), Decimal("15.00"))


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    in_rate, out_rate = PRICING.get(model, _FALLBACK)
    cost = (Decimal(prompt_tokens) * in_rate + Decimal(completion_tokens) * out_rate) / Decimal(1_000_000)
    # Round to 4 decimal places to match the column precision.
    return cost.quantize(Decimal("0.0001"))
