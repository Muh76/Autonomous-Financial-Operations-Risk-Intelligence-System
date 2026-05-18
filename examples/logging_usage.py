from app.core.logging import configure_logging, get_logger


def main() -> None:
    configure_logging()
    logger = get_logger(__name__, component="example")
    logger.info(
        "investigation_event_recorded",
        transaction_id="txn_2026_000001",
        risk_score=35,
        escalation_level="none",
    )


if __name__ == "__main__":
    main()
