"""Prometheus scrape endpoint controlled by runtime configuration."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.observability.metrics import render_metrics


router = APIRouter(tags=["System / Observability"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description=(
        "Return Prometheus text exposition when ENABLE_METRICS is enabled; "
        "otherwise return 404. The endpoint never includes business identifiers."
    ),
)
def metrics(request: Request) -> Response:
    """Expose Prometheus text format only when explicitly enabled."""
    settings = request.app.state.settings
    if not settings.enable_metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    body, content_type = render_metrics()
    return Response(content=body, headers={"Content-Type": content_type})
