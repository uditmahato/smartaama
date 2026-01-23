#!/usr/bin/env python
from app.db.session import engine
import sqlalchemy as sa

# Check table structure
with engine.connect() as conn:
    result = conn.execute(sa.text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'patients' ORDER BY ordinal_position"))
    print('Patient table columns:')
    for row in result:
        print(f'  {row[0]}: {row[1]}')
