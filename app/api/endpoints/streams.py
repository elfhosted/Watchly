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
    # ignore both type and id
    # and call update catalogs api
    # find catalogs to update
    stremio_service = StremioService()
    library_items = await stremio_service.get_library_items()
    seen_items = set()
    catalogs = []
    seed = {
        "watched": {
            "movie": False,
            "series": False,
        },
        "loved": {
            "movie": False,
            "series": False,
        },
    }
    # checked loved items
    loved_items = library_items.get("loved", [])
    watched_items = library_items.get("watched", [])
    # now find first few items
    for l_item in loved_items:
        print(l_item)
        type_ = l_item.get("type")
        if type_ in ["tv"]:
            type_ = "series"
        if l_item.get("_id") in seen_items or seed["loved"][type_]:
            continue
        seen_items.add(l_item.get("_id"))
        seed["loved"][type_] = True
        catalogs.append(
            {
                "type": type_,
                "id": l_item.get("_id"),
                "name": f"Because you Loved {l_item.get('name')}",
                "extra": [],
            }
        )
    for w_item in watched_items:
        type_ = l_item.get("type")
        if type_ in ["tv"]:
            type_ = "series"

        if w_item.get("_id") in seen_items or seed["watched"][type_]:
            continue
        seen_items.add(w_item.get("_id"))
        seed["watched"][type_] = True
        catalogs.append(
            {
                "type": type_,
                "id": w_item.get("_id"),
                "name": f"Because you Watched {w_item.get('name')}",
                "extra": [],
            }
        )
    # update catalogs
    auth_key = await stremio_service._get_auth_token()
    updated = await stremio_service.update_catalogs(catalogs, auth_key)
    logger.info(f"Updated catalogs: {updated}")
    if updated:
        return {"streams": []}
    else:
        return {
            "streams": [
                {
                    "name": "ERROR",
                    "description": "Error while updating catalogs. Please try again.",
                }
            ]
        }
