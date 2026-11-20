#!/usr/bin/env python
"""
Backfill Galaxy job metrics from job metrics instrumentation (__instrument_*) files,
e.g. ones copied from Pulsar's staging directory after Galaxy failed to record them.

--jobs-dir must hold one directory per Galaxy job id, with the __instrument_* files
in <job_id>/metadata/, <job_id>/working/ or <job_id>/ itself (--subdir to pick).

Run on the Galaxy host as the Galaxy user (Postgres peer auth), with Galaxy's
virtualenv python and Galaxy's own lib, so files are parsed exactly as that Galaxy
release would parse them, e.g.:

    PYTHONPATH=/srv/galaxy/server/lib python backfill_job_metrics.py \
        --db-url 'postgresql:///<galaxy_db_name>?host=/var/run/postgresql' \
        --metrics-conf /srv/galaxy/config/job_metrics_conf.yml \
        --jobs-dir ~/metadata_jobs/ \
        --dry-run --quiet

The metrics config must list the same plugins (and plugin options) that produced
the files; Galaxy's own job_metrics_conf.yml is fine when Galaxy and Pulsar use the
same plugins.

What gets written:
  * only jobs in a finished state (ok, error, failed, deleted, stopped, skipped);
    an unfinished job would get its metrics added again by Galaxy when it ends
    (--any-state overrides);
  * by default only metrics a job doesn't have yet; metrics Galaxy already
    recorded are kept, and values that differ from the files are reported.
    --force deletes a job's existing metrics and inserts the parsed ones instead;
  * numbers too large for the numeric column are dropped and long text is
    truncated, the same as Galaxy does.

The whole run is ONE database transaction:
  * every job gets a SAVEPOINT, so a job that fails is rolled back and skipped
    without aborting the rest;
  * --dry-run performs all the INSERTs (so the SQL is checked against the real
    schema) and then rolls everything back;
  * without --dry-run, a summary is printed and you are asked on the terminal to
    confirm the COMMIT (--yes skips the prompt). Anything but "yes" rolls back.

Take a database backup before the real run, e.g.
    pg_dump -Fc -t job_metric_numeric -t job_metric_text -f metrics_backup.dump <db>
"""
import argparse
import collections
import inspect
import math
import numbers
import os
import sys
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, inspect as sa_inspect, text

try:  # Galaxy >= 21.01
    from galaxy.job_metrics import JobMetrics
except ImportError:  # older Galaxy
    from galaxy.jobs.metrics import JobMetrics

# Mirrors galaxy.model.JOB_METRIC_MAX_LENGTH / JOB_METRIC_PRECISION / JOB_METRIC_SCALE.
TEXT_LIMIT = 1023
DEFAULT_PRECISION, DEFAULT_SCALE = 26, 7
CANDIDATE_SUBDIRS = ["metadata", "working", "."]
TABLES = ("job_metric_numeric", "job_metric_text")
FINISHED_STATES = {"ok", "error", "failed", "deleted", "stopped", "skipped"}


class SkipJob(Exception):
    pass


def find_metrics_dir(job_dir, subdir=None):
    candidates = [subdir] if subdir else CANDIDATE_SUBDIRS
    for sub in candidates:
        path = os.path.normpath(os.path.join(job_dir, sub))
        if os.path.isdir(path) and any(f.startswith("__instrument_") for f in os.listdir(path)):
            return path
    return None


def make_collector(job_metrics):
    """Galaxy <= 26.1 takes collect_properties(dest, job_id, dir); newer releases take a
    job object (with .id and .resubmission_count) instead of the id."""
    params = list(inspect.signature(job_metrics.collect_properties).parameters)
    wants_job = len(params) > 1 and params[1] == "job"

    def collect(destination, job_id, resubmission_count, metrics_dir):
        if wants_job:
            job = SimpleNamespace(id=job_id, resubmission_count=resubmission_count)
            return job_metrics.collect_properties(destination, job, metrics_dir)
        return job_metrics.collect_properties(destination, job_id, metrics_dir)

    return collect


def numeric_limit(conn):
    """Largest integer part job_metric_numeric.metric_value can hold (Galaxy's MAX_NUMERIC)."""
    precision, scale = DEFAULT_PRECISION, DEFAULT_SCALE
    if conn.dialect.name == "postgresql":
        row = conn.execute(
            text(
                "SELECT numeric_precision, numeric_scale FROM information_schema.columns"
                " WHERE table_name = 'job_metric_numeric' AND column_name = 'metric_value'"
            )
        ).first()
        if row and row.numeric_precision is not None:
            precision, scale = row.numeric_precision, row.numeric_scale or 0
    return 10 ** (precision - scale) - 1


def to_rows(props, max_numeric):
    """Split collected properties into {table: [(plugin, name, value)]} like Job.add_metric does."""
    rows, dropped = {t: [] for t in TABLES}, []
    for plugin, values in props.items():
        for metric, value in values.items():
            if isinstance(value, numbers.Number):
                if isinstance(value, float) and not math.isfinite(value) or int(value) > max_numeric:
                    dropped.append(f"{plugin}.{metric}={value}")
                else:
                    rows["job_metric_numeric"].append((plugin, metric, value))
            else:
                rows["job_metric_text"].append((plugin, metric, str(value)[: TEXT_LIMIT - 1]))
    return rows, dropped


def same_value(db_value, new_value):
    if isinstance(new_value, numbers.Number):
        try:
            return Decimal(str(db_value)) == Decimal(str(new_value))
        except Exception:
            return False
    return str(db_value) == str(new_value)[: TEXT_LIMIT - 1]


def job_dirs(jobs_dir, only_ids):
    for name in sorted(os.listdir(jobs_dir)):
        job_dir = os.path.join(jobs_dir, name)
        if os.path.isdir(job_dir) and (not only_ids or name in only_ids):
            yield name, job_dir


def confirm(question):
    """Ask on the terminal, so stdout can be piped or redirected."""
    if not sys.stdin.isatty():
        return False
    sys.stderr.write(question)
    sys.stderr.flush()
    return sys.stdin.readline().strip() == "yes"


def backfill_job(conn, args, collect, max_numeric, job_columns, mismatches, job_id, job_dir):
    """Insert metrics for one job; raises SkipJob to skip it. Returns number of rows inserted."""
    cols = ["destination_id", "state"] + (["resubmission_count"] if "resubmission_count" in job_columns else [])
    row = conn.execute(text(f"SELECT {', '.join(cols)} FROM job WHERE id = :id"), {"id": job_id}).mappings().first()
    if row is None:
        raise SkipJob("no such job in Galaxy")
    if row["state"] not in FINISHED_STATES and not args.any_state:
        raise SkipJob(f"job is in state '{row['state']}', not finished (use --any-state to include)")

    # (plugin, metric_name) -> value of metrics Galaxy already recorded for this job
    existing = {}
    for t in TABLES:
        for r in conn.execute(
            text(f"SELECT plugin, metric_name, metric_value FROM {t} WHERE job_id = :id"), {"id": job_id}
        ):
            existing[(r.plugin, r.metric_name)] = r.metric_value

    metrics_dir = find_metrics_dir(job_dir, args.subdir)
    if metrics_dir is None:
        raise SkipJob("no __instrument_* files found")

    # Only the default instrumenter is configured, so the destination doesn't change which plugins run.
    destination = row["destination_id"]
    try:
        props = collect(destination, job_id, row.get("resubmission_count") or 0, metrics_dir)
    except Exception as e:  # a broken file shouldn't stop the whole run
        raise SkipJob(f"parsing failed: {e!r}")

    rows, dropped = to_rows(props, max_numeric)
    if not any(rows.values()):
        raise SkipJob("no metrics parsed (do the plugins in --metrics-conf match the files?)")

    if not args.force:
        # keep what Galaxy recorded, only add what's missing; note where Galaxy and the files disagree
        for table, table_rows in rows.items():
            kept = []
            for plugin, metric, value in table_rows:
                key = (plugin, metric)
                if key not in existing:
                    kept.append((plugin, metric, value))
                elif not same_value(existing[key], value):
                    mismatches[f"{plugin}.{metric}"] += 1
                    if args.show_mismatches:
                        print(f"    mismatch {job_id} {plugin}.{metric}: galaxy={existing[key]!r} files={value!r}")
            rows[table] = kept
    n = sum(len(r) for r in rows.values())
    if not n:
        raise SkipJob(f"nothing missing ({len(existing)} metrics already recorded)")

    print(f"job {job_id} [{row['state']}, {destination}]: {n} metrics to add, {len(existing)} already recorded")
    if not args.quiet:
        for table_rows in rows.values():
            for plugin, metric, value in table_rows:
                print(f"    {plugin}.{metric} = {value!r}")
    if dropped:
        print(f"    dropped (doesn't fit the numeric column, Galaxy would drop too): {', '.join(dropped)}")

    if existing and args.force:
        for t in TABLES:
            conn.execute(text(f"DELETE FROM {t} WHERE job_id = :id"), {"id": job_id})
    for table, table_rows in rows.items():
        if table_rows:
            conn.execute(
                text(
                    f"INSERT INTO {table} (job_id, plugin, metric_name, metric_value)"
                    " VALUES (:job_id, :plugin, :name, :value)"
                ),
                [{"job_id": job_id, "plugin": p, "name": m, "value": v} for p, m, v in table_rows],
            )
    return n


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db-url", required=True, help="SQLAlchemy URL of the Galaxy database")
    p.add_argument("--metrics-conf", required=True, help="job metrics config with the plugins that produced the files")
    p.add_argument(
        "--jobs-dir", "--pulsar-staging", dest="jobs_dir", required=True, help="directory holding one subdirectory per job id"
    )
    p.add_argument("--subdir", help="subdirectory of each job dir holding the __instrument_* files (auto-detected if omitted)")
    p.add_argument("--job-id", action="append", default=[], help="only process this job id (repeatable)")
    p.add_argument(
        "--force",
        action="store_true",
        help="delete all metrics Galaxy recorded for a job and insert the parsed ones (default: only add missing metrics)",
    )
    p.add_argument("--any-state", action="store_true", help="also backfill jobs that are not finished yet")
    p.add_argument("--show-mismatches", action="store_true", help="print each existing metric that differs from the files")
    p.add_argument("--dry-run", action="store_true", help="do all inserts, then roll back")
    p.add_argument("--yes", action="store_true", help="commit without asking for confirmation")
    p.add_argument("--quiet", action="store_true", help="don't print every metric, only per-job summaries")
    args = p.parse_args()

    if not os.path.exists(args.metrics_conf):
        # JobMetrics silently falls back to core-only when the file is missing.
        p.error(f"metrics config not found: {args.metrics_conf}")
    if not os.path.isdir(args.jobs_dir):
        p.error(f"jobs dir not found: {args.jobs_dir}")

    collect = make_collector(JobMetrics(conf_file=args.metrics_conf))
    engine = create_engine(args.db_url)
    mismatches = collections.Counter()  # "plugin.metric" -> jobs where Galaxy's value differs from the files

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            job_columns = {c["name"] for c in sa_inspect(conn).get_columns("job")}
            max_numeric = numeric_limit(conn)

            done = skipped = rows_total = 0
            for name, job_dir in job_dirs(args.jobs_dir, set(args.job_id)):
                if not name.isdigit():
                    print(f"skip {name}: directory name is not a Galaxy job id")
                    skipped += 1
                    continue
                savepoint = conn.begin_nested()
                try:
                    rows_total += backfill_job(
                        conn, args, collect, max_numeric, job_columns, mismatches, int(name), job_dir
                    )
                    savepoint.commit()
                    done += 1
                except SkipJob as e:
                    savepoint.rollback()
                    print(f"skip {name}: {e}")
                    skipped += 1
                except Exception as e:  # DB error on this job: undo just this job
                    savepoint.rollback()
                    print(f"skip {name}: database error: {e!r}")
                    skipped += 1

            print(f"\n{done} jobs ({rows_total} metric rows) inserted in the open transaction, {skipped} skipped")
            if mismatches:
                print("existing Galaxy values that differ from the files (kept as recorded):")
                for key, count in mismatches.most_common():
                    print(f"    {key}: {count} jobs")
            sys.stdout.flush()

            if args.dry_run:
                trans.rollback()
                print("dry run: rolled back, nothing written")
                return 0
            if not args.yes and not confirm(
                f"COMMIT {rows_total} metric rows for {done} jobs? type 'yes' (no terminal: rolls back): "
            ):
                trans.rollback()
                print("rolled back, nothing written")
                return 1
            trans.commit()
            print("committed")
            return 0
        except BaseException:
            if trans.is_active:
                trans.rollback()
            raise


if __name__ == "__main__":
    sys.exit(main())
