#!/usr/bin/env python3
"""
Migrar dados de SQLite para PostgreSQL
"""
import sqlite3
from sqlalchemy import create_engine, MetaData, Table, select, insert, text
from sqlalchemy.pool import NullPool

# Conexões
sqlite_db = "sqlite:///instance/macalendar.db"
postgres_db = "postgresql+psycopg://mcalendar_app:Carv%232310%4076.@localhost:5432/mcalendar"

# Conectar ao SQLite
sqlite_engine = create_engine(sqlite_db, poolclass=NullPool)
sqlite_meta = MetaData()
sqlite_meta.reflect(bind=sqlite_engine)

# Conectar ao PostgreSQL
postgres_engine = create_engine(postgres_db, poolclass=NullPool)
postgres_meta = MetaData()
postgres_meta.reflect(bind=postgres_engine)

print("Iniciando migração...")

# Migrar dados de cada tabela
with sqlite_engine.connect() as sqlite_conn:
    with postgres_engine.connect() as postgres_conn:
        # Desabilitar constraints de chave estrangeira no PostgreSQL
        postgres_conn.execute(text("SET session_replication_role = replica"))
        postgres_conn.commit()
        
        for table_name in sqlite_meta.tables:
            print(f"Migrando tabela: {table_name}")
            
            # Table objects
            sqlite_table = Table(table_name, sqlite_meta, autoload_with=sqlite_engine)
            postgres_table = Table(table_name, postgres_meta, autoload_with=postgres_engine)
            
            # Select all rows from SQLite
            rows = sqlite_conn.execute(select(sqlite_table)).fetchall()
            
            if rows:
                # Insert into PostgreSQL
                for row in rows:
                    stmt = insert(postgres_table).values(**dict(row._mapping))
                    postgres_conn.execute(stmt)
                
                postgres_conn.commit()
                print(f"  ✓ {len(rows)} registros migrados")
            else:
                print(f"  - Nenhum registro para migrar")
        
        # Reabilitar constraints
        postgres_conn.execute(text("SET session_replication_role = default"))
        postgres_conn.commit()

print("\n✅ Migração concluída com sucesso!")
