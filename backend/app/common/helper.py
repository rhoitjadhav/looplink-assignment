from sqlalchemy import inspect


def to_dict(model):
    return {
        c.key: getattr(model, c.key)
        for c in inspect(model).mapper.column_attrs
    }
