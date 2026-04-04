from config import driver

with driver.session() as s:
    r = s.run("MATCH (m:MatchAnalysis) DELETE m RETURN count(m) as deleted")
    print("Deleted:", r.single()["deleted"])
