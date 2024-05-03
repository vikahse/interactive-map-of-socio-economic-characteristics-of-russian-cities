from fastapi import APIRouter, Request, Depends, Query, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from routers.data import get_column_names, get_indicator
from utils.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from cache.maps import get_map
import time

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix='/map')


@router.get("/")
async def render_map(request: Request, session: AsyncSession = Depends(get_session)):
    start = time.time()
    columns = await get_column_names(session)

    resp = templates.TemplateResponse(name="index.html",
                                      context={"request": request, "columns": columns['column_names'],
                                               "groups": columns['column_types'],
                                               "template_name": get_map("Empty_Map"), "selected": "Empty Map"})
    print(time.time() - start)

    return resp


@router.get('/indicator')
async def chosen_indicator(request: Request, indicator: str = Query(...), time_before: int = Query(...),
                           time_after: int = Query(...), session: AsyncSession = Depends(get_session)):
    input_indicator = indicator
    if indicator in ['Population', 'Children']:
        indicator = indicator.lower()
    elif indicator == 'Empty Map':
        indicator = 'Empty_Map'

    columns = await get_column_names(session)

    if indicator not in ['population', 'children', 'Empty_Map'] + columns['column_names']:
        return RedirectResponse(url="/map", status_code=status.HTTP_404_NOT_FOUND)

    return templates.TemplateResponse(name="index.html",
                                      context={"request": request, "columns": columns['column_names'],
                                               "groups": columns['column_types'], "selected": input_indicator,
                                               "template_name": get_map(indicator)})
