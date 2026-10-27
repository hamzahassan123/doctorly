from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Python classes ko Database Tables k sath map(link) karti hai
# Metadata:aik object hai.  record i.e. metadata(schemas, tables, constraints{rules} ) apny pass rakhta hai 
# naming_convention: contrains(rules) ka naming format
class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )

# ix: index > ix_column_name
# fk: foreign key  > fk_table_name_column_name_referred_table_name
# primery key > pk_table_name

