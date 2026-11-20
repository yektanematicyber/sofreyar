import logging
import os
import uuid

logger = logging.getLogger("safreyar.llm.telemetry")


def get_model_pricing() -> tuple[float, float]:
    """Returns (input_price_per_million, output_price_per_million) in USD."""
    try:
        input_price = float(os.getenv("LLM_PRICE_INPUT_PER_MILLION", "3.0"))
        output_price = float(os.getenv("LLM_PRICE_OUTPUT_PER_MILLION", "15.0"))
        return input_price, output_price
    except (ValueError, TypeError):
        return 3.0, 15.0


def log_llm_telemetry(
    user_id: int | None,
    request_id: str | None,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    status: str,
    retry_required: bool = False,
    from_cache: bool = False,
    is_fake: bool = False,
) -> dict:
    """Logs token consumption, estimated costs, and latency without leaking private content."""
    req_id = request_id or str(uuid.uuid4())
    total_tokens = input_tokens + output_tokens

    if is_fake or from_cache:
        estimated_cost_usd = 0.0
    else:
        input_price, output_price = get_model_pricing()
        estimated_cost_usd = round(
            (input_tokens * input_price + output_tokens * output_price) / 1_000_000.0,
            6,
        )

    telemetry_data = {
        "request_id": req_id,
        "user_id": user_id,
        "model": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "retry_required": retry_required,
        "from_cache": from_cache,
        "is_fake": is_fake,
    }

    logger.info(
        "LLM Telemetry | req_id=%s user_id=%s model=%s in_tokens=%d out_tokens=%d total_tokens=%d "
        "est_cost_usd=$%.6f latency_ms=%.2f status=%s retry=%s cache=%s",
        req_id,
        user_id,
        model_name,
        input_tokens,
        output_tokens,
        total_tokens,
        estimated_cost_usd,
        latency_ms,
        status,
        retry_required,
        from_cache,
    )

    return telemetry_data
