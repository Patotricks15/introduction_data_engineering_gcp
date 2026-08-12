import argparse

from src.events import PLAYERS


def profile_cells(profile: dict[str, str]) -> dict[bytes, bytes]:
    return {
        b"profile:display_name": profile["display_name"].encode("utf-8"),
        b"profile:team": profile["team"].encode("utf-8"),
        b"profile:region": profile["region"].encode("utf-8"),
        b"profile:rank": profile["rank"].encode("utf-8"),
    }


def seed_profiles(project_id: str, instance_id: str, table_id: str) -> int:
    from google.cloud import bigtable

    table = bigtable.Client(project=project_id, admin=True).instance(instance_id).table(table_id)
    rows = []
    for profile in PLAYERS:
        row = table.direct_row(profile["player_id"].encode("utf-8"))
        for column, value in profile_cells(profile).items():
            family, qualifier = column.split(b":", 1)
            row.set_cell(family.decode("utf-8"), qualifier, value)
        rows.append(row)
    statuses = table.mutate_rows(rows)
    failures = [status for status in statuses if status.code != 0]
    if failures:
        raise RuntimeError(f"Failed to seed {len(failures)} Bigtable rows.")
    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed e-sports player profiles in Bigtable.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--table-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = seed_profiles(args.project_id, args.instance_id, args.table_id)
    print(f"Seeded {count} player profiles in Bigtable.")


if __name__ == "__main__":
    main()