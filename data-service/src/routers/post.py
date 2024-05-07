import pandas as pd
from fastapi import APIRouter, File, UploadFile, Request, status, Depends, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.data import create_column, update_data
from sqlalchemy.ext.asyncio import AsyncSession
from utils.session import get_session
from io import BytesIO
from models.data_models import CreateColumn, UpdateData
from fastapi import HTTPException
from cache.cache_maps import cache_map
from cache.cache_graphs import update_all_settlements
from common.sqlalchemy_data_type import matching_columns
from sqlalchemy.exc import InvalidRequestError
from tables.data import DataDao
from typing import Optional
import os

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/post")


@router.post("/column")
async def post_file(request: Request, file: UploadFile = File(...), column_type: str = Form(...),
                    session: AsyncSession = Depends(get_session), access_token_cookie: Optional[str] = Cookie(default=None)):
    if access_token_cookie == None:
        url = f'http://{os.getenv("INTERNAL_ADDRESS")}:{os.getenv("USER_SERVICE_PORT")}/login/'
        return RedirectResponse(url=url)
    if not file:
        redirect_url = request.url_for('get_upload_form').include_query_params(message="Необходимо загрузить файл",
                                                                               color="red")
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    if file.content_type != "text/csv":
        redirect_url = request.url_for('get_upload_form').include_query_params(message="Формаn файла должен быть csv",
                                                                               color="red")
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    new_data = pd.read_csv(BytesIO(file.file.read()))
    if len(new_data.columns.values.tolist()) != 2:
        error_message = "В файле должно быть 2 колонки - с сопоставляющей конокой и новыми данными"
        redirect_url = request.url_for('get_upload_form').include_query_params(message=error_message,
                                                                               color="red")
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    error_message = None
    matching_column = new_data.columns.values.tolist()[0]
    if matching_column not in matching_columns:
        error_message = f"""Сопостовляющая колонка должна быть одна из 
         {matching_columns}, а введена {matching_column}"""

    if column_type not in ['Float', 'Integer']:
        error_message = f"Тип новых данных должен быть Float или Integer, получен {column_type}"

    new_column_name = new_data.columns.values.tolist()[1]
    if new_column_name.find('_') != -1:
        year = new_column_name.split('_')[1]
        if not year or not year.isdigit():
            error_message = f"Если в индикаторе используется '_', то это должен быть год из чисел"
    if new_column_name != new_column_name.strip():
        error_message = f"В названии столбца присутствуют пробелы"

    if error_message:
        redirect_url = request.url_for('get_upload_form').include_query_params(message=error_message,
                                                                               color="red")
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    try:
        await create_column(CreateColumn(column_name=new_column_name, column_type=column_type),
                            session)
        for index, row in new_data.iterrows():
            response = await update_data(
                UpdateData(matching_column_value=row[matching_column],
                           matching_column_name=matching_column,
                           column=new_column_name,
                           new_value=row[new_column_name]),
                session)
    except HTTPException as e:
        await session.rollback()
        try:
            del DataDao.__mapper__._props[new_column_name]
        except InvalidRequestError:
            ...

        redirect_url = request.url_for('get_upload_form').include_query_params(message=e.detail,
                                                                               color="red")
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    await session.commit()

    await cache_map(new_column_name, session)

    await update_all_settlements()

    redirect_url = request.url_for('get_upload_form').include_query_params(
        message=f"Данные для конки {new_column_name} успешно загружены",
        color="green")
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/column")
async def get_upload_form(request: Request, message: str = "", color: str = None, access_token_cookie: Optional[str] = Cookie(default=None)):
    if access_token_cookie == None:
        url = f'http://{os.getenv("INTERNAL_ADDRESS")}:{os.getenv("USER_SERVICE_PORT")}/login/'
        return RedirectResponse(url=url)
    return templates.TemplateResponse(name="post_column.html",
                                      context={"request": request,
                                               "types": ['Float', 'Integer'],
                                               "message": message,
                                               "color": color
                                               })