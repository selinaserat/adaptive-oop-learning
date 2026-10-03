"""Integration seam for the SQL teammate; not a working persistence adapter.

Implement Repository in base.py using the agreed schema. Pass the resulting
instance to create_app(repository=...) without changing routes or services.
See docs/DATABASE.md for transaction and schema requirements.
"""
class SQLRepository:
    persistent = True

    def __init__(self, *args, **kwargs):
        raise NotImplementedError('SQL schema/adapter has not been supplied. See docs/DATABASE.md.')
