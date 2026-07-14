from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    r1 = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'utilisateurs' ORDER BY ordinal_position"))
    print('COLONNES utilisateurs:')
    for row in r1:
        print(' ', row[0], '-', row[1])
    r2 = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'documents' ORDER BY ordinal_position"))
    print('COLONNES documents:')
    for row in r2:
        print(' ', row[0], '-', row[1])
