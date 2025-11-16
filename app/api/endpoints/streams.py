from fastapi import APIRouter
from app.services.stremio_service import StremioService
from loguru import logger

router = APIRouter(prefix="/stream")


@router.get("/{type}/{id}.json")
async def get_stream(
    type: str,
    id: str,
):
    """
    Stremio stream endpoint for movies and series.
    """

    return {
        "streams": [
            {
                "name": "Update Catalogs",
                "description": "Update the catalogs for the addon.",
                "url": "https://watchly-eta.vercel.app/catalog/update/",
            }
        ]
    }
