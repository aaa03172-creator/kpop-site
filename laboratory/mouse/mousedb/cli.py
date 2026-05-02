from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from . import db
from .services import (
    archive_strain,
    colony_summary,
    create_cage,
    create_litter,
    create_litter_mice,
    create_mating,
    create_mouse,
    create_strain,
    end_mating,
    event,
    experiment_ready,
    list_cages,
    list_events,
    list_genotypes,
    list_litters,
    list_matings,
    list_mice,
    list_strains,
    move_mouse,
    record_genotype,
    seed as seed_data,
    show_cage,
    show_litter,
    show_mating,
    show_mouse,
    show_strain,
    update_mouse_status,
    wean_litter,
)
from .utils import print_result


app = typer.Typer(help="CLI-first MouseDB.")
strain_app = typer.Typer(help="Manage strains.")
mouse_app = typer.Typer(help="Manage mice.")
cage_app = typer.Typer(help="Manage cages.")
event_app = typer.Typer(help="Manage mouse events.")
genotype_app = typer.Typer(help="Manage genotype results.")
mating_app = typer.Typer(help="Manage matings.")
litter_app = typer.Typer(help="Manage litters.")
colony_app = typer.Typer(help="Colony summaries.")

app.add_typer(strain_app, name="strain")
app.add_typer(mouse_app, name="mouse")
app.add_typer(cage_app, name="cage")
app.add_typer(event_app, name="event")
app.add_typer(genotype_app, name="genotype")
app.add_typer(mating_app, name="mating")
app.add_typer(litter_app, name="litter")
app.add_typer(colony_app, name="colony")


def fail(exc: Exception) -> None:
    raise typer.BadParameter(str(exc))


@app.callback()
def main(
    db_path: Optional[Path] = typer.Option(
        None,
        "--db",
        help="SQLite database path. Defaults to MOUSEDB_PATH or data/mousedb.sqlite.",
    )
) -> None:
    if db_path is not None:
        os.environ["MOUSEDB_PATH"] = str(db_path)


@app.command()
def init(json_output: bool = typer.Option(False, "--json", help="Print JSON output.")) -> None:
    db.init_db()
    print_result({"database": str(db.db_path()), "initialized": True}, json_output)


@app.command()
def seed(json_output: bool = typer.Option(False, "--json", help="Print JSON output.")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = seed_data(conn)
    print_result(payload, json_output)


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", help="Confirm destructive reset."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON output."),
) -> None:
    if not yes:
        raise typer.BadParameter("reset requires --yes")
    path = db.db_path()
    if path.exists():
        path.unlink()
    db.init_db()
    print_result({"database": str(path), "reset": True}, json_output)


@strain_app.command("add")
def strain_add(
    name: str = typer.Option(..., "--name"),
    background: str = "",
    source: str = "",
    status: str = "active",
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = create_strain(conn, name=name, background=background, source=source, status=status)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@strain_app.command("list")
def strain_list(json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_strains(conn)
    print_result(payload, json_output)


@strain_app.command("search")
def strain_search(query: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_strains(conn, query=query)
    print_result(payload, json_output)


@strain_app.command("show")
def strain_show(strain_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = show_strain(conn, strain_id)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@strain_app.command("archive")
def strain_archive(strain_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = archive_strain(conn, strain_id)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@strain_app.command("update")
def strain_update(strain_id: str, status: str = typer.Option(..., "--status"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        conn.execute("UPDATE strain SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE strain_id = ?", (status, strain_id))
        payload = show_strain(conn, strain_id)
    print_result(payload, json_output)


@mouse_app.command("add")
def mouse_add(
    display_id: str = typer.Option(..., "--display-id"),
    strain: str = typer.Option(..., "--strain"),
    sex: str = typer.Option("unknown", "--sex"),
    dob: str = typer.Option(None, "--dob"),
    cage: str = typer.Option(None, "--cage"),
    status: str = typer.Option("alive", "--status"),
    use: str = typer.Option("unknown", "--use"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = create_mouse(conn, display_id=display_id, strain_id=strain, sex=sex, dob=dob, cage=cage, status=status, use=use)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@mouse_app.command("list")
def mouse_list(
    strain: str = typer.Option(None, "--strain"),
    sex: str = typer.Option(None, "--sex"),
    status: str = typer.Option(None, "--status"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_mice(conn, strain_id=strain, sex=sex, status=status)
    print_result(payload, json_output)


@mouse_app.command("show")
def mouse_show(mouse_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = show_mouse(conn, mouse_id)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@mouse_app.command("update")
def mouse_update(
    mouse_id: str,
    status: str = typer.Option(None, "--status"),
    use: str = typer.Option(None, "--use"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    try:
        with db.connection() as conn:
            payload = update_mouse_status(conn, mouse_id, status=status, use=use)
    except Exception as exc:
        fail(exc)
    print_result(payload, json_output)


@mouse_app.command("timeline")
def mouse_timeline(mouse_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_events(conn, mouse_id)
    print_result(payload, json_output)


@cage_app.command("add")
def cage_add(
    label: str = typer.Option(..., "--label"),
    location: str = "",
    rack: str = "",
    shelf: str = "",
    cage_type: str = typer.Option("", "--type"),
    status: str = "active",
    note: str = "",
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = create_cage(conn, label=label, location=location, rack=rack, shelf=shelf, cage_type=cage_type, status=status, note=note)
    print_result(payload, json_output)


@cage_app.command("list")
def cage_list(json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_cages(conn)
    print_result(payload, json_output)


@cage_app.command("show")
def cage_show(cage_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = show_cage(conn, cage_id)
    print_result(payload, json_output)


@cage_app.command("move-mouse")
def cage_move_mouse(
    mouse: str = typer.Option(..., "--mouse"),
    to: str = typer.Option(..., "--to"),
    date: str = typer.Option(None, "--date"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = move_mouse(conn, mouse, to, date)
    print_result(payload, json_output)


@event_app.command("add")
def event_add(
    mouse: str = typer.Option(..., "--mouse"),
    type: str = typer.Option(..., "--type"),
    date: str = typer.Option(None, "--date"),
    details: str = typer.Option("", "--details"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = event(conn, mouse_id=mouse, event_type=type, event_date=date, details=details)
    print_result(payload, json_output)


@event_app.command("list")
def event_list(mouse: str = typer.Option(..., "--mouse"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_events(conn, mouse)
    print_result(payload, json_output)


@genotype_app.command("record")
def genotype_record(
    mouse: str = typer.Option(..., "--mouse"),
    allele: str = typer.Option(None, "--allele"),
    result: str = typer.Option(..., "--result"),
    zygosity: str = typer.Option("", "--zygosity"),
    date: str = typer.Option(None, "--date"),
    sample_id: str = typer.Option("", "--sample-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = record_genotype(conn, mouse_id=mouse, allele_id=allele, result=result, zygosity=zygosity, test_date=date, sample_id=sample_id)
    print_result(payload, json_output)


@genotype_app.command("list")
def genotype_list(mouse: str = typer.Option(..., "--mouse"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_genotypes(conn, mouse)
    print_result(payload, json_output)


@mating_app.command("create")
def mating_create(
    male: str = typer.Option(None, "--male"),
    female: str = typer.Option(None, "--female"),
    second_female: str = typer.Option(None, "--second-female"),
    goal: str = typer.Option("", "--goal"),
    expected_genotype: str = typer.Option("", "--expected-genotype"),
    start_date: str = typer.Option(None, "--start-date"),
    status: str = "active",
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = create_mating(conn, male=male, female=female, second_female=second_female, goal=goal, expected_genotype=expected_genotype, start_date=start_date, status=status)
    print_result(payload, json_output)


@mating_app.command("list")
def mating_list(json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_matings(conn)
    print_result(payload, json_output)


@mating_app.command("show")
def mating_show(mating_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = show_mating(conn, mating_id)
    print_result(payload, json_output)


@mating_app.command("end")
def mating_end(mating_id: str, date: str = typer.Option(None, "--date"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = end_mating(conn, mating_id, date)
    print_result(payload, json_output)


@litter_app.command("create")
def litter_create(
    mating: str = typer.Option(None, "--mating"),
    birth_date: str = typer.Option(None, "--birth-date"),
    number_born: int = typer.Option(0, "--number-born"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = create_litter(conn, mating_id=mating, birth_date=birth_date, number_born=number_born)
    print_result(payload, json_output)


@litter_app.command("list")
def litter_list(json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = list_litters(conn)
    print_result(payload, json_output)


@litter_app.command("show")
def litter_show(litter_id: str, json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = show_litter(conn, litter_id)
    print_result(payload, json_output)


@litter_app.command("wean")
def litter_wean(litter_id: str, date: str = typer.Option(None, "--date"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = wean_litter(conn, litter_id, date)
    print_result(payload, json_output)


@litter_app.command("create-mice")
def litter_create_mice(
    litter_id: str,
    count: int = typer.Option(..., "--count"),
    strain: str = typer.Option(..., "--strain"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = create_litter_mice(conn, litter_id, count, strain)
    print_result(payload, json_output)


@colony_app.command("summary")
def colony_summary_cmd(strain: str = typer.Option(None, "--strain"), json_output: bool = typer.Option(False, "--json")) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = colony_summary(conn, strain_id=strain)
    print_result(payload, json_output)


@app.command("experiment-ready")
def experiment_ready_cmd(
    strain: str = typer.Option(None, "--strain"),
    genotype: str = typer.Option(None, "--genotype"),
    sex: str = typer.Option(None, "--sex"),
    age_min_weeks: float = typer.Option(None, "--age-min-weeks"),
    age_max_weeks: float = typer.Option(None, "--age-max-weeks"),
    status: str = typer.Option(None, "--status"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    db.init_db()
    with db.connection() as conn:
        payload = experiment_ready(
            conn,
            strain_id=strain,
            genotype=genotype,
            sex=sex,
            age_min_weeks=age_min_weeks,
            age_max_weeks=age_max_weeks,
            status=status,
        )
    print_result(payload, json_output)


if __name__ == "__main__":
    app()
