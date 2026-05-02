from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from .ids import mouse_id_from_display, next_external_id, normalize_cage_id
from .utils import age_days, parse_year, today_iso


Row = sqlite3.Row


def row_dict(row: Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def require_row(conn: sqlite3.Connection, table: str, id_field: str, value: str) -> Row:
    row = conn.execute(f"SELECT * FROM {table} WHERE {id_field} = ?", (value,)).fetchone()
    if row is None:
        raise ValueError(f"{table} not found: {value}")
    return row


def create_strain(
    conn: sqlite3.Connection,
    *,
    name: str,
    background: str = "",
    source: str = "",
    status: str = "active",
    common_name: str = "",
    official_name: str = "",
    strain_type: str = "",
    owner: str = "",
) -> dict[str, Any]:
    strain_id = next_external_id(conn, "strain")
    conn.execute(
        """
        INSERT INTO strain
            (strain_id, strain_name, common_name, official_name, strain_type,
             background, source, status, owner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (strain_id, name, common_name, official_name, strain_type, background, source, status, owner),
    )
    return show_strain(conn, strain_id)


def list_strains(conn: sqlite3.Connection, query: str = "") -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if query:
        where = """
        WHERE lower(s.strain_id || ' ' || s.strain_name || ' ' || s.common_name || ' ' ||
                    s.official_name || ' ' || s.background || ' ' || s.source || ' ' || s.status)
              LIKE ?
        """
        params.append(f"%{query.lower()}%")
    rows = conn.execute(
        f"""
        SELECT s.*,
               SUM(CASE WHEN m.current_status NOT IN ('dead','sacrificed','archived','transferred') THEN 1 ELSE 0 END) AS alive_mouse_count,
               SUM(CASE WHEN m.current_use = 'breeder' OR m.current_status = 'breeder' THEN 1 ELSE 0 END) AS active_breeder_count
        FROM strain s
        LEFT JOIN mouse m ON m.strain_id = s.strain_id
        {where}
        GROUP BY s.strain_id
        ORDER BY s.status = 'active' DESC, s.strain_name COLLATE NOCASE
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def show_strain(conn: sqlite3.Connection, strain_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT s.*,
               COALESCE(SUM(CASE WHEN m.current_status NOT IN ('dead','sacrificed','archived','transferred') THEN 1 ELSE 0 END), 0) AS alive_mouse_count,
               COALESCE(SUM(CASE WHEN m.current_use = 'breeder' OR m.current_status = 'breeder' THEN 1 ELSE 0 END), 0) AS active_breeder_count
        FROM strain s
        LEFT JOIN mouse m ON m.strain_id = s.strain_id
        WHERE s.strain_id = ?
        GROUP BY s.strain_id
        """,
        (strain_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"strain not found: {strain_id}")
    return dict(row)


def archive_strain(conn: sqlite3.Connection, strain_id: str) -> dict[str, Any]:
    require_row(conn, "strain", "strain_id", strain_id)
    conn.execute(
        "UPDATE strain SET status = 'archived', date_archived = ?, updated_at = CURRENT_TIMESTAMP WHERE strain_id = ?",
        (today_iso(), strain_id),
    )
    return show_strain(conn, strain_id)


def ensure_cage(conn: sqlite3.Connection, cage_ref: str | None) -> str | None:
    if not cage_ref:
        return None
    cage_id = normalize_cage_id(cage_ref)
    row = conn.execute("SELECT cage_id FROM cage WHERE cage_id = ? OR cage_label = ?", (cage_id, cage_ref)).fetchone()
    if row is not None:
        return row["cage_id"]
    label = cage_ref.replace("-", "")
    conn.execute(
        "INSERT INTO cage (cage_id, cage_label, status) VALUES (?, ?, 'active')",
        (cage_id, label),
    )
    return cage_id


def create_cage(
    conn: sqlite3.Connection,
    *,
    label: str,
    location: str = "",
    rack: str = "",
    shelf: str = "",
    cage_type: str = "",
    status: str = "active",
    note: str = "",
) -> dict[str, Any]:
    cage_id = normalize_cage_id(label)
    cage_label = label.replace("-", "")
    existing = conn.execute("SELECT * FROM cage WHERE cage_id = ? OR cage_label = ?", (cage_id, cage_label)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE cage SET location = ?, rack = ?, shelf = ?, cage_type = ?,
                            status = ?, note = ?, updated_at = CURRENT_TIMESTAMP
            WHERE cage_id = ?
            """,
            (location, rack, shelf, cage_type, status, note, existing["cage_id"]),
        )
        return show_cage(conn, existing["cage_id"])
    conn.execute(
        """
        INSERT INTO cage (cage_id, cage_label, location, rack, shelf, cage_type, status, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cage_id, cage_label, location, rack, shelf, cage_type, status, note),
    )
    return show_cage(conn, cage_id)


def show_cage(conn: sqlite3.Connection, cage_id: str) -> dict[str, Any]:
    normalized = normalize_cage_id(cage_id)
    row = conn.execute("SELECT * FROM cage WHERE cage_id = ? OR cage_label = ?", (normalized, cage_id)).fetchone()
    if row is None:
        raise ValueError(f"cage not found: {cage_id}")
    result = dict(row)
    result["mouse_count"] = conn.execute(
        "SELECT COUNT(*) AS count FROM mouse WHERE current_cage_id = ? AND current_status NOT IN ('dead','sacrificed','archived','transferred')",
        (result["cage_id"],),
    ).fetchone()["count"]
    return result


def list_cages(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM cage ORDER BY cage_id").fetchall()
    return [show_cage(conn, row["cage_id"]) for row in rows]


def event(
    conn: sqlite3.Connection,
    *,
    mouse_id: str,
    event_type: str,
    event_date: str | None = None,
    details: str = "",
    related_entity_type: str = "",
    related_entity_id: str = "",
    previous_value: str | None = None,
    new_value: str | None = None,
) -> dict[str, Any]:
    require_row(conn, "mouse", "mouse_id", mouse_id)
    event_year = parse_year(event_date) or date.today().year
    event_id = next_external_id(conn, "event", event_year)
    conn.execute(
        """
        INSERT INTO mouse_event
            (event_id, mouse_id, event_type, event_date, related_entity_type,
             related_entity_id, details, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            mouse_id,
            event_type,
            event_date or today_iso(),
            related_entity_type,
            related_entity_id,
            details,
            previous_value,
            new_value,
        ),
    )
    return dict(require_row(conn, "mouse_event", "event_id", event_id))


def create_mouse(
    conn: sqlite3.Connection,
    *,
    display_id: str,
    strain_id: str | None = None,
    sex: str = "unknown",
    dob: str | None = None,
    cage: str | None = None,
    status: str = "alive",
    use: str = "unknown",
    father_id: str | None = None,
    mother_id: str | None = None,
    litter_id: str | None = None,
    genotype_summary: str = "",
    owner: str = "",
    note: str = "",
) -> dict[str, Any]:
    if strain_id:
        require_row(conn, "strain", "strain_id", strain_id)
    if litter_id:
        require_row(conn, "litter", "litter_id", litter_id)
    cage_id = ensure_cage(conn, cage)
    mouse_year = parse_year(dob) or date.today().year
    preferred = mouse_id_from_display(display_id, mouse_year)
    mouse_id = preferred or next_external_id(conn, "mouse", mouse_year)
    if conn.execute("SELECT 1 FROM mouse WHERE mouse_id = ?", (mouse_id,)).fetchone():
        mouse_id = next_external_id(conn, "mouse", mouse_year)
    conn.execute(
        """
        INSERT INTO mouse
            (mouse_id, display_id, strain_id, sex, date_of_birth, father_id,
             mother_id, litter_id, current_cage_id, current_status, current_use,
             current_genotype_summary, owner, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mouse_id,
            display_id,
            strain_id,
            sex,
            dob,
            father_id,
            mother_id,
            litter_id,
            cage_id,
            status,
            use,
            genotype_summary,
            owner,
            note,
        ),
    )
    event(conn, mouse_id=mouse_id, event_type="born" if dob else "note_added", event_date=dob, details=note, related_entity_type="litter" if litter_id else "", related_entity_id=litter_id or "")
    if cage_id:
        event(conn, mouse_id=mouse_id, event_type="moved", event_date=dob or today_iso(), details=f"Initial cage {cage_id}", related_entity_type="cage", related_entity_id=cage_id, new_value=cage_id)
    return show_mouse(conn, mouse_id)


def show_mouse(conn: sqlite3.Connection, mouse_id: str) -> dict[str, Any]:
    row = require_row(conn, "mouse", "mouse_id", mouse_id)
    result = dict(row)
    result["age_days"] = age_days(result.get("date_of_birth"))
    return result


def list_mice(
    conn: sqlite3.Connection,
    *,
    strain_id: str | None = None,
    sex: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if strain_id:
        clauses.append("strain_id = ?")
        params.append(strain_id)
    if sex:
        clauses.append("sex = ?")
        params.append(sex)
    if status:
        clauses.append("current_status = ?")
        params.append(status)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = conn.execute(f"SELECT * FROM mouse {where} ORDER BY mouse_id", params).fetchall()
    return [show_mouse(conn, row["mouse_id"]) for row in rows]


def update_mouse_status(conn: sqlite3.Connection, mouse_id: str, status: str | None = None, use: str | None = None) -> dict[str, Any]:
    before = show_mouse(conn, mouse_id)
    if status:
        conn.execute("UPDATE mouse SET current_status = ?, updated_at = CURRENT_TIMESTAMP WHERE mouse_id = ?", (status, mouse_id))
        event_type = {"sacrificed": "sacrificed", "dead": "dead_found", "archived": "archived"}.get(status, "note_added")
        event(conn, mouse_id=mouse_id, event_type=event_type, event_date=today_iso(), previous_value=before["current_status"], new_value=status)
    if use:
        conn.execute("UPDATE mouse SET current_use = ?, updated_at = CURRENT_TIMESTAMP WHERE mouse_id = ?", (use, mouse_id))
        event(conn, mouse_id=mouse_id, event_type="note_added", event_date=today_iso(), details="current_use updated", previous_value=before["current_use"], new_value=use)
    return show_mouse(conn, mouse_id)


def move_mouse(conn: sqlite3.Connection, mouse_id: str, to_cage: str, moved_date: str | None = None) -> dict[str, Any]:
    mouse = show_mouse(conn, mouse_id)
    cage_id = ensure_cage(conn, to_cage)
    conn.execute("UPDATE mouse SET current_cage_id = ?, updated_at = CURRENT_TIMESTAMP WHERE mouse_id = ?", (cage_id, mouse_id))
    event(
        conn,
        mouse_id=mouse_id,
        event_type="moved",
        event_date=moved_date or today_iso(),
        details=f"{mouse.get('current_cage_id') or ''} -> {cage_id}",
        related_entity_type="cage",
        related_entity_id=cage_id or "",
        previous_value=mouse.get("current_cage_id"),
        new_value=cage_id,
    )
    return show_mouse(conn, mouse_id)


def list_events(conn: sqlite3.Connection, mouse_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM mouse_event WHERE mouse_id = ? ORDER BY event_date, id",
        (mouse_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def record_genotype(
    conn: sqlite3.Connection,
    *,
    mouse_id: str,
    allele_id: str | None = None,
    result: str,
    zygosity: str = "",
    test_date: str | None = None,
    sample_id: str = "",
    method: str = "",
    note: str = "",
) -> dict[str, Any]:
    require_row(conn, "mouse", "mouse_id", mouse_id)
    if allele_id:
        require_row(conn, "allele", "allele_id", allele_id)
    gt_year = parse_year(test_date) or date.today().year
    genotype_result_id = next_external_id(conn, "genotype", gt_year)
    conn.execute(
        """
        INSERT INTO genotype_result
            (genotype_result_id, mouse_id, allele_id, sample_id, test_date,
             result, zygosity, method, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (genotype_result_id, mouse_id, allele_id, sample_id, test_date, result, zygosity, method, note),
    )
    allele_label = allele_id or "genotype"
    summary = f"{allele_label}:{result}" + (f"/{zygosity}" if zygosity else "")
    existing = show_mouse(conn, mouse_id).get("current_genotype_summary") or ""
    new_summary = ";".join([part for part in [existing, summary] if part])
    conn.execute(
        "UPDATE mouse SET current_genotype_summary = ?, updated_at = CURRENT_TIMESTAMP WHERE mouse_id = ?",
        (new_summary, mouse_id),
    )
    event(conn, mouse_id=mouse_id, event_type="genotyped", event_date=test_date or today_iso(), details=summary, related_entity_type="genotype_result", related_entity_id=genotype_result_id, previous_value=existing, new_value=new_summary)
    payload = dict(require_row(conn, "genotype_result", "genotype_result_id", genotype_result_id))
    payload["raw_result"] = payload["result"]
    payload["normalized_result"] = payload["result"]
    return payload


def list_genotypes(conn: sqlite3.Connection, mouse_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM genotype_result WHERE mouse_id = ? ORDER BY test_date, id", (mouse_id,)).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["raw_result"] = payload["result"]
        payload["normalized_result"] = payload["result"]
        result.append(payload)
    return result


def create_mating(
    conn: sqlite3.Connection,
    *,
    male: str | None,
    female: str | None,
    second_female: str | None = None,
    goal: str = "",
    expected_genotype: str = "",
    start_date: str | None = None,
    status: str = "active",
    purpose: str = "",
    note: str = "",
) -> dict[str, Any]:
    for mouse_id in [male, female, second_female]:
        if mouse_id:
            require_row(conn, "mouse", "mouse_id", mouse_id)
    mating_id = next_external_id(conn, "mating", parse_year(start_date) or date.today().year)
    conn.execute(
        """
        INSERT INTO mating
            (mating_id, mating_label, male_mouse_id, female_mouse_id,
             second_female_mouse_id, strain_goal, expected_genotype,
             start_date, status, purpose, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (mating_id, mating_id, male, female, second_female, goal, expected_genotype, start_date, status, purpose, note),
    )
    for mouse_id in [male, female, second_female]:
        if mouse_id:
            event(conn, mouse_id=mouse_id, event_type="paired", event_date=start_date or today_iso(), related_entity_type="mating", related_entity_id=mating_id, details=goal)
    return show_mating(conn, mating_id)


def show_mating(conn: sqlite3.Connection, mating_id: str) -> dict[str, Any]:
    return dict(require_row(conn, "mating", "mating_id", mating_id))


def list_matings(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM mating ORDER BY start_date DESC, mating_id").fetchall()
    return [dict(row) for row in rows]


def end_mating(conn: sqlite3.Connection, mating_id: str, end_date: str | None = None) -> dict[str, Any]:
    mating = show_mating(conn, mating_id)
    conn.execute("UPDATE mating SET status = 'ended', end_date = ?, updated_at = CURRENT_TIMESTAMP WHERE mating_id = ?", (end_date or today_iso(), mating_id))
    for mouse_id in [mating.get("male_mouse_id"), mating.get("female_mouse_id"), mating.get("second_female_mouse_id")]:
        if mouse_id:
            event(conn, mouse_id=mouse_id, event_type="separated", event_date=end_date or today_iso(), related_entity_type="mating", related_entity_id=mating_id)
    return show_mating(conn, mating_id)


def create_litter(
    conn: sqlite3.Connection,
    *,
    mating_id: str | None,
    birth_date: str | None,
    number_born: int = 0,
    note: str = "",
) -> dict[str, Any]:
    if mating_id:
        require_row(conn, "mating", "mating_id", mating_id)
    litter_id = next_external_id(conn, "litter", parse_year(birth_date) or date.today().year)
    conn.execute(
        """
        INSERT INTO litter
            (litter_id, litter_label, mating_id, birth_date, number_born,
             number_alive, status, note)
        VALUES (?, ?, ?, ?, ?, ?, 'born', ?)
        """,
        (litter_id, litter_id, mating_id, birth_date, number_born, number_born, note),
    )
    if mating_id:
        mating = show_mating(conn, mating_id)
        for mouse_id in [mating.get("male_mouse_id"), mating.get("female_mouse_id"), mating.get("second_female_mouse_id")]:
            if mouse_id:
                event(conn, mouse_id=mouse_id, event_type="litter_produced", event_date=birth_date or today_iso(), related_entity_type="litter", related_entity_id=litter_id, details=str(number_born))
    return show_litter(conn, litter_id)


def show_litter(conn: sqlite3.Connection, litter_id: str) -> dict[str, Any]:
    return dict(require_row(conn, "litter", "litter_id", litter_id))


def list_litters(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM litter ORDER BY birth_date DESC, litter_id").fetchall()
    return [dict(row) for row in rows]


def wean_litter(conn: sqlite3.Connection, litter_id: str, weaning_date: str | None = None) -> dict[str, Any]:
    require_row(conn, "litter", "litter_id", litter_id)
    conn.execute(
        "UPDATE litter SET status = 'weaned', weaning_date = ?, number_weaned = number_alive, updated_at = CURRENT_TIMESTAMP WHERE litter_id = ?",
        (weaning_date or today_iso(), litter_id),
    )
    return show_litter(conn, litter_id)


def create_litter_mice(conn: sqlite3.Connection, litter_id: str, count: int, strain_id: str, sex: str = "unknown") -> list[dict[str, Any]]:
    litter = show_litter(conn, litter_id)
    created = []
    for index in range(1, count + 1):
        display_id = f"{litter_id.split('-')[-1]}-{index:02d}"
        created.append(
            create_mouse(
                conn,
                display_id=display_id,
                strain_id=strain_id,
                sex=sex,
                dob=litter.get("birth_date"),
                litter_id=litter_id,
                status="weaning_pending",
                use="stock",
            )
        )
    return created


def colony_summary(conn: sqlite3.Connection, strain_id: str | None = None) -> dict[str, Any]:
    params = []
    strain_clause = ""
    if strain_id:
        strain_clause = " AND strain_id = ?"
        params.append(strain_id)
    total_alive = conn.execute(
        f"SELECT COUNT(*) AS count FROM mouse WHERE current_status NOT IN ('dead','sacrificed','archived','transferred') {strain_clause}",
        params,
    ).fetchone()["count"]
    active_strains = conn.execute("SELECT COUNT(*) AS count FROM strain WHERE status = 'active'").fetchone()["count"]
    active_matings = conn.execute("SELECT COUNT(*) AS count FROM mating WHERE status = 'active'").fetchone()["count"]
    weaning_due = conn.execute("SELECT COUNT(*) AS count FROM litter WHERE status IN ('pre_weaning','weaning_due','born')").fetchone()["count"]
    genotyping_pending = conn.execute("SELECT COUNT(*) AS count FROM mouse WHERE current_status = 'genotyping_pending'").fetchone()["count"]
    low_stock = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM (
          SELECT s.strain_id, COUNT(m.mouse_id) AS alive_count
          FROM strain s
          LEFT JOIN mouse m ON m.strain_id = s.strain_id
             AND m.current_status NOT IN ('dead','sacrificed','archived','transferred')
          WHERE s.status = 'active'
          GROUP BY s.strain_id
          HAVING alive_count < 5
        )
        """
    ).fetchone()["count"]
    return {
        "mouse_total": total_alive,
        "total_alive_mice": total_alive,
        "active_strains": active_strains,
        "active_matings": active_matings,
        "weaning_due_litters": weaning_due,
        "genotyping_pending_mice": genotyping_pending,
        "low_stock_strains": low_stock,
    }


def experiment_ready(
    conn: sqlite3.Connection,
    *,
    strain_id: str | None = None,
    genotype: str | None = None,
    sex: str | None = None,
    age_min_weeks: float | None = None,
    age_max_weeks: float | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    mice = list_mice(conn, strain_id=strain_id, sex=sex, status=status)
    candidates = []
    for mouse in mice:
        warnings: list[str] = []
        if genotype and genotype.lower() not in (mouse.get("current_genotype_summary") or "").lower():
            continue
        days = mouse.get("age_days")
        if age_min_weeks is not None and (days is None or days < age_min_weeks * 7):
            continue
        if age_max_weeks is not None and (days is None or days > age_max_weeks * 7):
            continue
        if not mouse.get("current_genotype_summary"):
            warnings.append("genotype_unknown")
        if mouse.get("reviewed_status") != "accepted":
            warnings.append("review_not_accepted")
        candidates.append(
            {
                "mouse_id": mouse["mouse_id"],
                "display_id": mouse["display_id"],
                "sex": mouse["sex"],
                "age_weeks": round((days or 0) / 7, 1) if days is not None else None,
                "cage": mouse.get("current_cage_id"),
                "genotype": mouse.get("current_genotype_summary"),
                "status": mouse.get("current_status"),
                "eligibility": "candidate" if not warnings else "candidate_with_warning",
                "warnings": warnings,
            }
        )
    return {
        "query": {
            "strain": strain_id,
            "genotype": genotype,
            "sex": sex,
            "age_min_weeks": age_min_weeks,
            "age_max_weeks": age_max_weeks,
            "status": status,
        },
        "count": len(candidates),
        "mice": candidates,
    }


def seed(conn: sqlite3.Connection) -> dict[str, Any]:
    if conn.execute("SELECT 1 FROM strain WHERE strain_id = 'STR-0001'").fetchone() is None:
        conn.execute(
            """
            INSERT INTO strain (strain_id, strain_name, common_name, background, source, status)
            VALUES ('STR-0001', 'PV-Cre', 'PV-Cre', 'C57BL/6J', 'JAX', 'active')
            """
        )
    if conn.execute("SELECT 1 FROM gene WHERE gene_id = 'GENE-0001'").fetchone() is None:
        conn.execute("INSERT INTO gene (gene_id, gene_symbol, full_name) VALUES ('GENE-0001', 'Pvalb', 'parvalbumin')")
    if conn.execute("SELECT 1 FROM allele WHERE allele_id = 'AL-0001'").fetchone() is None:
        conn.execute(
            """
            INSERT INTO allele (allele_id, gene_id, allele_name, allele_type, zygosity_options)
            VALUES ('AL-0001', 'GENE-0001', 'Pvalb-IRES-Cre', 'Cre', 'positive,negative,heterozygous')
            """
        )
    if conn.execute("SELECT 1 FROM strain_allele WHERE strain_allele_id = 'SA-0001'").fetchone() is None:
        conn.execute("INSERT INTO strain_allele (strain_allele_id, strain_id, allele_id, default_zygosity) VALUES ('SA-0001', 'STR-0001', 'AL-0001', 'heterozygous')")
    create_cage(conn, label="C014", location="Animal Room A", rack="R2", shelf="S3")
    return {"seeded": True, "strain_id": "STR-0001", "allele_id": "AL-0001", "cage_id": "C-014"}
