import sqlite3

con = sqlite3.connect("voters.db")
cur = con.cursor()


async def find_all_iraq(first_name: str, middle_name: str, last_name: str):
    cur.execute(
        f"SELECT GOV_MOT_ID, COUNT(*) AS NameCount FROM person WHERE PER_FIRST = '{first_name}' AND PER_FATHER = '{middle_name}' AND PER_GRAND = '{last_name}' GROUP BY GOV_MOT_ID"
    )
    return cur.fetchall()


async def find_in_city(
    first_name: str, middle_name: str, last_name: str, city: list[int]
) -> list[any]:
    query = "SELECT full_name, PER_DOB2, PER_FAMNO, GOV_MOT_ID FROM Person WHERE PER_FIRST = ? AND PER_FATHER = ? AND PER_GRAND = ? AND GOV_MOT_ID IN ({})".format(
        ",".join("?" * len(city))
    )
    params = (first_name, middle_name, last_name) + tuple(city)
    cur.execute(query, params)
    return cur.fetchall()


async def find_family_members(family_number: int, gov_mot_id: int) -> list[any]:
    cur.execute(
        f"SELECT PER_ID, PER_FAMNO, PER_DOB, PER_VRTYPE_2013, PCNO, VRC_ID, GOV_NAME_AR, PC_NAME, PC_ADDRESS, VRC_NAME_AR, VRC_ADDRESS, PSNO, VoterSEQ, VoterCard_Status, Rigestered_Case, new_card_status, full_name FROM Person WHERE PER_FAMNO = {family_number} AND GOV_MOT_ID = {gov_mot_id}"
    )
    return cur.fetchall()
