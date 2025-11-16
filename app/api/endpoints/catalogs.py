from fastapi import APIRouter, HTTPException, Response
from loguru import logger
from app.services.recommendation_service import RecommendationService
from app.services.stremio_service import StremioService

router = APIRouter(prefix="/catalog")

recommendation_service = RecommendationService()


@router.get("/{type}/{id}.json")
async def get_catalog(
    type: str,
    id: str,
    response: Response,
):
    """
    Stremio catalog endpoint for movies and series.
    Returns recommendations based on user's Stremio library.

    Args:
        type: 'movie' or 'series'
        id: Catalog ID (e.g., 'watchly.rec')
    """
    logger.info(f"Fetching catalog for {type} with id {id}")

    if type not in ["movie", "series"]:
        logger.warning(f"Invalid type: {type}")
        raise HTTPException(
            status_code=400, detail="Invalid type. Use 'movie' or 'series'"
        )

    if id not in ["watchly.rec"] and not id.startswith("tt"):
        logger.warning(f"Invalid id: {id}")
        raise HTTPException(status_code=400, detail="Invalid id. Use 'watchly.rec'")

    # if id starts with tt, then return recommendations for that particular item
    if id.startswith("tt"):
        recommendations = await recommendation_service.get_recommendations_for_item(item_id=id)
        logger.info(f"Found {len(recommendations)} recommendations for {id}")
        # response.headers["Cache-Control"] = "public, max-age=86400"
        return {"metas": recommendations}
    try:
        # Get recommendations based on library
        # Use last 10 items from library, get 5 recommendations per item
        recommendations = await recommendation_service.get_recommendations(
            content_type=type, seed_limit=10, per_seed_limit=5, max_results=50
        )
        logger.info(f"Found {len(recommendations)} recommendations for {type}")

        # Recommendations already contain full metadata in Stremio format
        # Extract meta from each recommendation
        metas = []
        for rec in recommendations:
            # rec is already the full addon meta response with 'meta' key
            if rec and rec.get("meta"):
                metas.append(rec["meta"])

        logger.info(f"Returning {len(metas)} items for {type}")
        # Cache catalog responses for 1 day (86400 seconds)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return {"metas": metas}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching catalog for {type}/{id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/")
async def update_catalogs(response: Response):
    """
    Update the catalogs for the addon.
    """
    # steps
    # 1. Log in to stremio
    # 2. Fetch addons and find this addon
    # 3. Update catalogs
    # 4. Update manifest in addons in stremio
    try:
        stremio_service = StremioService()
        auth_key = await stremio_service._get_auth_token()
        # find catalogs to update
        catalogs = []
        stremio_service.update_catalogs(catalogs, auth_key)
    except Exception as e:
        logger.error(f"Error updating catalogs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
