import logging

from .db import service_client

log = logging.getLogger("mediguide.audit")


def audit(actor_id: str | None, action: str, entity: str | None = None, entity_id: str | None = None, **metadata) -> None:
    """Write an audit row. Never put medical content in metadata."""
    try:
        service_client().table("audit_logs").insert(
            {"actor_id": actor_id, "action": action, "entity": entity, "entity_id": entity_id, "metadata": metadata}).execute()
    except Exception as e:  # audit failure must not break the request, but must be visible
        log.warning("audit write failed: %s", type(e).__name__)
