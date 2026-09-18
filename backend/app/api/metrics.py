"""Prometheus scrape endpoint controlled by runtime configuration."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.observability.metrics import render_metrics


router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    """Expose Prometheus text format only when explicitly enabled."""
    settings = request.app.state.settings
    if not settings.enable_metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    body, content_type = render_metrics()
    return Response(content=body, headers={"Content-Type": content_type})
