import pandas as pd
from neo4j import GraphDatabase
import time

# ---- CONFIG ----
URI = "neo4j+s://f1a3e611.databases.neo4j.io"
USER = "f1a3e611"
PASSWORD = "ILTqiU7kbxt3D8uYDNxwqaVD23dL0Gz8gfpVCYJrprM"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ---- LOAD CSV ----
players = pd.read_csv("data/players.csv")
clubs = pd.read_csv("data/clubs.csv")
transfers = pd.read_csv("data/transfers.csv")

# ---- CREATE INDEXES (important for speed) ----
def create_indexes(tx):
    tx.run("CREATE INDEX player_id IF NOT EXISTS FOR (p:Player) ON (p.id)")
    tx.run("CREATE INDEX club_id IF NOT EXISTS FOR (c:Club) ON (c.id)")
    tx.run("CREATE INDEX club_name IF NOT EXISTS FOR (c:Club) ON (c.name)")

# ---- INSERT PLAYERS ----
def batch(iterable, size=50):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]
def create_players_batch(tx, rows):
    tx.run("""
        UNWIND $rows AS row
        MERGE (p:Player {id: row.player_id})
        SET p.name = row.name,
            p.first_name = row.first_name,
            p.last_name = row.last_name,
            p.nationality = row.country_of_citizenship,
            p.dob = row.date_of_birth,
            p.position = row.position,
            p.market_value = row.market_value_in_eur,
            p.current_club_id = row.current_club_id,
            p.current_club_name = row.current_club_name
    """, rows=rows)
# ---- INSERT CLUBS ----
def create_clubs_batch(tx, rows):
    tx.run("""
        UNWIND $rows AS row
        MERGE (c:Club {id: row.club_id})
        SET c.name = row.name,
            c.league = row.domestic_competition_id,
            c.squad_size = row.squad_size
    """, rows=rows)
# ---- CREATE RELATIONSHIPS (FROM TRANSFERS) ----
def create_relationships_batch(tx, rows):
    tx.run("""
        UNWIND $rows AS row

        MATCH (p:Player {id: row.player_id})

        FOREACH (_ IN CASE WHEN row.from_club_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (c1:Club {id: row.from_club_id})
            MERGE (p)-[:PLAYED_FOR]->(c1)
        )

        FOREACH (_ IN CASE WHEN row.to_club_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (c2:Club {id: row.to_club_id})
            MERGE (p)-[:PLAYED_FOR]->(c2)
        )
    """, rows=rows)
# ---- MAIN LOAD ----
with driver.session() as session:

    print("Creating indexes...")
    session.execute_write(create_indexes)

    print("Loading players...")
    player_rows = players.to_dict("records")
    for i, chunk in enumerate(batch(player_rows, 50)):
        session.execute_write(create_players_batch, chunk)
        time.sleep(0.5)

        if i % 20 == 0:
            print(f"Players batch {i} done")

    print("Loading clubs...")
    club_rows = clubs.to_dict("records")
    for chunk in batch(club_rows, 50):
        session.execute_write(create_clubs_batch, chunk)
        time.sleep(0.5)

    print("Linking players to clubs...")
    transfer_rows = transfers.to_dict("records")
    for i, chunk in enumerate(batch(transfer_rows, 50)):
        session.execute_write(create_relationships_batch, chunk)
        time.sleep(0.5)

        if i % 20 == 0:
            print(f"Transfers batch {i} done")

print("✅ DONE!")