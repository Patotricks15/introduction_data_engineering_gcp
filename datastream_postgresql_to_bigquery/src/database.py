#!/usr/bin/env python3

import argparse
import os

import psycopg


def connect() -> psycopg.Connection:
    """Open a TLS connection to the temporary Cloud SQL instance."""
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=5432,
        dbname=os.environ["PGDATABASE"],
        user="postgres",
        password=os.environ["PGPASSWORD"],
        sslmode="require",
        connect_timeout=30,
    )


def initialize_source(connection: psycopg.Connection) -> None:
    """Create source data and PostgreSQL logical replication objects."""
    with connection.cursor() as cursor:
        cursor.execute("ALTER ROLE datastream_user WITH REPLICATION")
        cursor.execute("GRANT CONNECT ON DATABASE commerce TO datastream_user")
        cursor.execute("GRANT USAGE ON SCHEMA public TO datastream_user")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS public.orders (
                order_id BIGINT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                status TEXT NOT NULL,
                amount NUMERIC(10, 2) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO public.orders
                (order_id, customer_name, status, amount)
            VALUES
                (1001, 'Ada Lovelace', 'paid', 149.90),
                (1002, 'Grace Hopper', 'shipped', 89.50),
                (1003, 'Katherine Johnson', 'processing', 215.00)
            ON CONFLICT (order_id) DO NOTHING
            """
        )
        cursor.execute(
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO datastream_user"
        )
        cursor.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT ON TABLES TO datastream_user"
        )
        cursor.execute(
            """
            SELECT 1
            FROM pg_publication
            WHERE pubname = 'datastream_publication'
            """
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "CREATE PUBLICATION datastream_publication "
                "FOR TABLE public.orders"
            )
        cursor.execute(
            """
            SELECT 1
            FROM pg_replication_slots
            WHERE slot_name = 'datastream_slot'
            """
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "SELECT pg_create_logical_replication_slot(%s, %s)",
                ("datastream_slot", "pgoutput"),
            )
    connection.commit()


def insert_change(connection: psycopg.Connection) -> None:
    """Insert a row after Datastream starts to demonstrate CDC."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO public.orders
                (order_id, customer_name, status, amount)
            VALUES
                (1004, 'Margaret Hamilton', 'paid', 320.75)
            ON CONFLICT (order_id) DO UPDATE SET
                customer_name = EXCLUDED.customer_name,
                status = EXCLUDED.status,
                amount = EXCLUDED.amount,
                updated_at = CURRENT_TIMESTAMP
            """
        )
    connection.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the PostgreSQL CDC source.")
    parser.add_argument("action", choices=("initialize", "insert-change"))
    args = parser.parse_args()

    with connect() as connection:
        if args.action == "initialize":
            initialize_source(connection)
            print("PostgreSQL source and replication objects are ready.")
        else:
            insert_change(connection)
            print("A new order was committed to PostgreSQL.")


if __name__ == "__main__":
    main()
