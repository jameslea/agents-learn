"""Smoke test and latency probe for the configured LLM provider.

Examples:
    python3 scripts/test_llm_provider.py
    python3 scripts/test_llm_provider.py --provider minimax --runs 3
    python3 scripts/test_llm_provider.py --provider deepseek --model deepseek-v4-flash --runs 3
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import statistics
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from openai import APIConnectionError, AuthenticationError, BadRequestError, PermissionDeniedError

from common.llm_factory import build_llm, resolve_provider_config


LOGGER = logging.getLogger("llm_provider_test")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test the configured LLM provider and report latency.")
    parser.add_argument("--provider", help="Override LLM_PROVIDER, e.g. minimax/deepseek/openai/custom.")
    parser.add_argument("--model", help="Override provider model name.")
    parser.add_argument("--runs", type=int, default=1, help="Number of requests to run. Must be >= 1.")
    parser.add_argument("--temperature", type=float, default=0.1, help="Request temperature.")
    parser.add_argument("--prompt", default="请只回复 OK", help="Prompt used for the smoke test.")
    return parser.parse_args()


def log_provider_config(provider: str | None, model: str | None) -> None:
    provider_config = resolve_provider_config(provider=provider, model_name=model)
    LOGGER.info("provider=%s", provider_config.name)
    LOGGER.info("model=%s", provider_config.model)
    LOGGER.info("base_url=%s", provider_config.base_url)
    LOGGER.info("has_api_key=%s", bool(provider_config.api_key))
    LOGGER.info("supports_json_mode=%s", provider_config.supports_json_mode)

    if not provider_config.api_key:
        raise RuntimeError("API key is missing.")


def run_once(args: argparse.Namespace, run_index: int) -> float:
    LOGGER.info("run=%d start", run_index)
    start = time.perf_counter()
    response = build_llm(
        provider=args.provider,
        model_name=args.model,
        temperature=args.temperature,
    ).invoke(args.prompt)
    elapsed = time.perf_counter() - start
    LOGGER.info("run=%d elapsed=%.3fs response=%s", run_index, elapsed, response.content)
    return elapsed


def main() -> int:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    configure_logging()
    args = parse_args()
    if args.runs < 1:
        LOGGER.error("--runs must be >= 1")
        return 2

    load_dotenv(override=True)

    try:
        log_provider_config(args.provider, args.model)
        elapsed_values = [run_once(args, index) for index in range(1, args.runs + 1)]
    except AuthenticationError as exc:
        LOGGER.error("AUTH_ERROR: %s", exc)
        return 3
    except PermissionDeniedError as exc:
        LOGGER.error("PERMISSION_ERROR: %s", exc)
        return 4
    except BadRequestError as exc:
        LOGGER.error("BAD_REQUEST: %s", exc)
        return 5
    except APIConnectionError as exc:
        LOGGER.error("CONNECTION_ERROR: %s", exc)
        return 6
    except Exception as exc:
        LOGGER.error("UNKNOWN_ERROR: %s: %s", type(exc).__name__, exc)
        return 1

    LOGGER.info(
        "summary runs=%d min=%.3fs max=%.3fs mean=%.3fs",
        len(elapsed_values),
        min(elapsed_values),
        max(elapsed_values),
        statistics.mean(elapsed_values),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
