from config import driver
with driver.session() as s:
    r = s.run("MATCH (m:MatchAnalysis {espn_id: $id}) DELETE m RETURN count(m) as deleted", {"id": "746648"})
    print("Deleted:", r.single()["deleted"])
