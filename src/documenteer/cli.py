"""Documenteer's command-line interface (CLI)."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from pydantic import ValidationError

from documenteer.services.technoteauthor import (
    AuthorSyncOutcome,
    SyncAction,
    TechnoteAuthorService,
)
from documenteer.services.technotecff import (
    CFF_FILENAME,
    CffStatus,
    TechnoteCffService,
)
from documenteer.services.technotemigration import TechnoteMigrationService
from documenteer.storage.authordb import (
    AuthorDb,
    AuthorDbUnreachableError,
    AuthorNotFoundError,
    InvalidOrcidError,
)
from documenteer.storage.technotetoml import TechnoteTomlFile


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(message="%(version)s")
def main() -> None:
    """Documenteer command-line tools.

    You can learn more at https://documenteer.lsst.io/
    """


# display_help is vendored from safir.click.


def display_help(
    main: click.Group,
    ctx: click.Context,
    topic: str | None = None,
    subtopic: str | None = None,
) -> None:
    """Show help for a Click command."""
    if not topic:
        if not ctx.parent:
            raise RuntimeError("help called without topic or parent")
        click.echo(ctx.parent.get_help())
        return
    if topic not in main.commands:
        raise click.UsageError(f"Unknown help topic {topic}", ctx)
    if not subtopic:
        ctx.info_name = topic
        click.echo(main.commands[topic].get_help(ctx))
        return

    # Subtopic handling. This requires some care with typing, since the
    # commands attribute (although present) is not documented, and the
    # get_command method is only available on Groups.
    group = main.commands[topic]
    if isinstance(group, click.Group):
        command = group.get_command(ctx, subtopic)
        if command:
            ctx.info_name = f"{topic} {subtopic}"
            click.echo(command.get_help(ctx))
            return

    # Fall through to the error case of no subcommand found.
    msg = f"Unknown help topic {topic} {subtopic}"
    raise click.UsageError(msg, ctx)


@main.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx: click.Context, topic: str | None) -> None:
    """Show help for any command."""
    display_help(main, ctx, topic)


@main.group()
def technote() -> None:
    """Manage Rubin technotes."""


@technote.command(name="add-author")
@click.option(
    "-a",
    "--author-id",
    "author_id",
    nargs=1,
    default=None,
    help="Author ID: a key in the authors map in authordb.yaml.",
)
@click.option(
    "--orcid",
    "orcid",
    nargs=1,
    default=None,
    help="ORCID of the author, bare or as an orcid.org URL.",
)
@click.option(
    "--toml",
    "-t",
    "technote_toml",
    type=click.Path(exists=True),
    default="technote.toml",
    help="Path to technote.toml file",
)
def technote_add_author(
    author_id: str | None, orcid: str | None, technote_toml: str
) -> None:
    """Add an author to technote.toml from the Rubin author DB.

    Identify the author either by their author ID (-a/--author-id), a key in
    the "authors" map in authordb.yaml, or by their ORCID (--orcid). With
    neither option the command prompts for an author ID. See
    https://github.com/lsst/lsst-texmf/blob/main/etc/authordb.yaml
    """
    if author_id is not None and orcid is not None:
        raise click.UsageError(
            "Use either -a/--author-id or --orcid to identify the author, "
            "not both."
        )

    toml_path = Path(technote_toml)
    toml_file = TechnoteTomlFile.open(toml_path)
    author_db = AuthorDb()

    service = TechnoteAuthorService(toml_file, author_db)
    try:
        if orcid is not None:
            identifier = f"ORCID {orcid}"
            author = service.add_author_by_orcid(orcid)
        else:
            # Prompt here rather than through the option's own `prompt=`
            # handler, which would go on demanding an author ID even when
            # --orcid already identifies the author.
            resolved_id = author_id or click.prompt("Author ID")
            identifier = f"internal_id '{resolved_id}'"
            author = service.add_author_by_id(resolved_id)
    except (
        AuthorNotFoundError,
        InvalidOrcidError,
        AuthorDbUnreachableError,
    ) as e:
        # A mistyped or unknown identifier is user error, and an author
        # database that cannot be reached is the network's doing; neither is
        # a Documenteer bug. Report them plainly and exit 1 rather than
        # dumping a traceback, as sync-authors does for the same conditions.
        raise click.ClickException(str(e)) from e
    except ValidationError as e:
        # A 200 whose body is not an author record. pydantic's own message
        # is a field-by-field dump of what failed to validate, which tells a
        # writer nothing they can act on, so report the condition itself —
        # the same one sync-authors reports as a skipped entry.
        raise click.ClickException(
            f"The Rubin author database returned a malformed record for "
            f"{identifier}."
        ) from e

    click.echo(
        f"Added author {author.given_name} {author.family_name} to {toml_path}"
    )
    service.write_toml(toml_path)


@technote.command(name="sync-authors")
@click.option(
    "--toml",
    "-t",
    "technote_toml",
    type=click.Path(exists=True),
    default="technote.toml",
    help="Path to technote.toml file",
)
def technote_sync_authors(technote_toml: str) -> None:
    """Sync author info from authordb.yaml to technote.toml.

    An author whose internal_id is wrong or missing is repaired from the
    ORCID the entry declares. An author who cannot be resolved at all is
    reported as a warning and left as declared; the rest are still
    synchronized and written, and the command exits non-zero.
    """
    toml_path = Path(technote_toml)
    toml_file = TechnoteTomlFile.open(toml_path)
    author_db = AuthorDb()

    service = TechnoteAuthorService(toml_file, author_db)
    outcomes = service.sync_authors()
    service.write_toml(toml_path)

    reports = [
        line
        for line in (_describe_sync_outcome(o) for o in outcomes)
        if line is not None
    ]
    skipped_reasons = [
        o.reason for o in outcomes if o.action is SyncAction.skipped
    ]

    if reports:
        click.echo(f"Synchronized authors to {toml_path}:")
        for line in reports:
            click.echo(f"- {line}")
    elif not skipped_reasons:
        click.echo("No authors to update")

    for reason in skipped_reasons:
        click.echo(f"Warning: {reason}", err=True)
    if skipped_reasons:
        sys.exit(1)


def _describe_sync_outcome(outcome: AuthorSyncOutcome) -> str | None:
    """Phrase one synchronized author for the sync-authors report.

    An outcome that wrote nothing yields `None`: it has nothing to report
    under "Synchronized authors", and is warned about separately.

    A repaired or filled-in ``internal_id`` is called out along with the
    basis for it. That is a change to the technote's own metadata, which the
    writer should see and verify, rather than a routine refresh.
    """
    author = outcome.author
    if author is None:
        return None
    name = f"{author.given_name or ''} {author.family_name}"
    if outcome.action is SyncAction.repaired:
        return (
            f"{name} ({outcome.previous_internal_id} → "
            f"{author.internal_id}, matched by ORCID)"
        )
    if outcome.action is SyncAction.filled:
        return f"{name} ({author.internal_id}, matched by ORCID)"
    return f"{name} ({author.internal_id})"


@technote.command(name="migrate")
@click.option(
    "--author-id",
    "-a",
    "author_ids",
    multiple=True,
    required=True,
    help="Author IDs to add to technote.toml",
)
@click.option(
    "--dir",
    "-d",
    "root_dir",
    type=click.Path(exists=True),
    required=True,
    default=".",
    help="Path to technote directory",
)
@click.option(
    "--auto-delete",
    "-D",
    "auto_delete",
    is_flag=True,
    default=False,
    help="Delete deprecated files without prompting",
)
def technote_migrate(
    author_ids: list[str], root_dir: str, *, auto_delete: bool
) -> None:
    """Migrate a technote from a metadata.yaml file.

    This command migrates an old-style Rubin technote (that uses a
    metadata.yaml file) into the modern format.

    This command creates a technote.toml file, upgrades the index.rst file,
    and adds/updates other supporting files. Check the git diff after running
    this command to see what changed.

    authors to the technote.toml file from the Rubin author DB.
    The `-a/--author-id` options are author IDs in the Rubin author database.
    See https://github.com/lsst/lsst-texmf/blob/main/etc/authordb.yaml
    """
    author_db = AuthorDb()
    migration_service = TechnoteMigrationService(Path(root_dir), author_db)
    migration_service.migrate(author_ids=author_ids)

    if auto_delete or click.confirm("Delete deprecated files?"):
        migration_service.delete_deprecated_files()


@technote.command(name="lint")
@click.option(
    "--dir",
    "-d",
    "root_dir",
    type=click.Path(exists=True),
    default=".",
    help="Path to technote directory",
)
@click.option(
    "--strict",
    "-s",
    "strict",
    is_flag=True,
    default=False,
    help="Promote warnings to errors",
)
def technote_lint(root_dir: str, *, strict: bool) -> None:
    """Lint a technote's metadata and structure.

    This runs three groups of checks and reports each finding with a stable
    rule code (for example ``[TN101]``). Structural checks (``TN0xx``)
    confirm that technote.toml exists, is valid TOML, and conforms to the
    technote schema, and that requirements.txt declares documenteer[technote]
    without pinning Sphinx separately. Metadata checks (``TN1xx``) confirm that
    every author declares an internal_id that resolves in the Rubin author
    database. Content checks (``TN2xx``) confirm that the content declares a
    non-empty abstract using the abstract directive rather than an ordinary
    section heading.

    A directory with no content file and no conf.py is a technote that Sphinx
    does not build, so only the technote.toml checks (structural and metadata)
    apply to it.

    Each rule has a documentation page explaining the finding and its fix at
    https://documenteer.lsst.io/technotes/lint/, and the report links to the
    page for every rule it fires.

    The command exits non-zero when any error remains. Use ``--strict`` to
    promote warnings to errors.
    """
    # Imported here, rather than at module scope, because the lint service is
    # the only part of the CLI that needs the `technote` package (a
    # documenteer[technote] extra). Keeping it lazy means the rest of the
    # CLI — `sync-cff` in particular, which runs as a pre-commit hook from a
    # plain documenteer install — works without the extra.
    from documenteer.services.technotelint import (  # noqa: PLC0415
        LintContext,
        LintFinding,
        Severity,
        TechnoteLintService,
        rule_url,
    )

    author_db = AuthorDb()
    context = LintContext.from_dir(Path(root_dir), author_db)
    service = TechnoteLintService(context)
    findings = service.lint()

    # Split into errors and warnings; --strict promotes warnings to errors.
    errors: list[LintFinding] = []
    warnings: list[LintFinding] = []
    for finding in findings:
        if strict or finding.severity is Severity.error:
            errors.append(finding)
        else:
            warnings.append(finding)

    # Report errors first, then warnings; each prefixed with its code.
    for finding in (*errors, *warnings):
        click.echo(f"[{finding.code}] {finding.message}")

    if not errors and not warnings:
        click.echo("✅ Technote lint passed with no issues.")
        return

    click.echo(f"Found {len(errors)} error(s) and {len(warnings)} warning(s).")

    # Point at the landing page for each distinct rule that fired.
    click.echo("Learn more:")
    for code in sorted({f.code for f in (*errors, *warnings)}):
        click.echo(f"  {code}: {rule_url(code)}")

    if errors:
        raise SystemExit(1)


@technote.command(name="sync-cff")
@click.option(
    "--dir",
    "-d",
    "root_dir",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Path to technote directory",
)
@click.option(
    "--check",
    "check",
    is_flag=True,
    default=False,
    help=(
        "Report whether CITATION.cff is up to date instead of writing it. "
        "Exits non-zero only when the file exists and is stale."
    ),
)
def technote_sync_cff(root_dir: str, *, check: bool) -> None:
    """Generate CITATION.cff from technote.toml.

    This writes a Citation File Format 1.2.0 file at the technote's
    repository root, so that GitHub's "Cite this repository" button offers a
    proper technote citation. CFF's top-level ``type`` may only be
    ``software`` or ``dataset``, so the technote itself is the file's
    ``preferred-citation`` — a ``report`` reference carrying the DOI, the
    authors with their ORCIDs and affiliations, the publishing institution,
    the technote's handle as ``number``, the release date, and the canonical
    URL.

    :file:`technote.toml` is the canonical source: the file is regenerated
    from scratch on every run, so edit technote.toml rather than
    CITATION.cff. Generation is deterministic, which makes ``--check`` a
    content comparison suitable for CI and pre-commit. ``--check`` exits
    non-zero only when CITATION.cff exists and is stale; a repository with
    no CITATION.cff has simply not opted in, and passes.
    """
    root = Path(root_dir)
    toml_path = root / "technote.toml"
    if not toml_path.is_file():
        raise click.ClickException(f"No technote.toml found in {root}.")

    try:
        service = TechnoteCffService.from_technote_toml(toml_path)
    except ValueError as e:
        # Malformed TOML, a DOI that is not a DOI, or metadata too sparse to
        # cite: all of them are something to fix in technote.toml, not a
        # Documenteer bug, so report the condition rather than a traceback.
        raise click.ClickException(str(e)) from e

    for warning in service.warnings:
        click.echo(f"Warning: {warning}", err=True)

    cff_path = root / CFF_FILENAME
    if check:
        status = service.status(cff_path)
        if status is CffStatus.stale:
            click.echo(
                f"{cff_path} is out of date with {toml_path}. Run "
                f"'documenteer technote sync-cff' to regenerate it.",
                err=True,
            )
            raise SystemExit(1)
        if status is CffStatus.absent:
            click.echo(f"{cff_path} does not exist; nothing to check.")
        else:
            click.echo(f"{cff_path} is up to date.")
        return

    if service.sync(cff_path) is CffStatus.current:
        click.echo(f"{cff_path} is already up to date.")
    else:
        click.echo(f"Wrote {cff_path}")
