"""Check collector table access without printing credentials or requiring an SDK."""

from supabase_ingest import SupabaseError, SupabaseIngestor, load_local_env


def main() -> int:
    try:
        load_local_env()
        ingestor = SupabaseIngestor.from_environment()
        if ingestor is None:
            print("Set SUPABASE_URL and SUPABASE_SECRET_KEY in the local .env")
            return 1
        for table in ("data_sources", "fetch_runs", "observations"):
            ingestor.client.request(table, query={"select": "id", "limit": 0})
            print(f"Supabase {table}: OK")
    except (SupabaseError, OSError, ValueError) as exc:
        print(f"Connection check: FAILED — {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
