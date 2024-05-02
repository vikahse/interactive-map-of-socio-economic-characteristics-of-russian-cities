from common.sqlalchemy_data_type import sqlalchemy_type
from tables.data import DataDao
from utils.column import get_columns
from sqlalchemy import Column, types
from sqlalchemy.ext.asyncio import AsyncSession


async def check_columns(session: AsyncSession):
    real_columns = await get_columns(DataDao.__tablename__, session)
    declarative_names = set(DataDao.__table__.columns.keys())
    real_names = set(real_columns.keys())

    if real_names.difference(declarative_names):
        column_type = {}
        for el in real_columns.cursor.description:
            column_type[el[0]] = sqlalchemy_type[el[1]]

        for column in real_names.difference(declarative_names):
            setattr(DataDao, column,
                    Column(column, getattr(types, column_type[column])))