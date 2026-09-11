"""Documenteer's command-line interface (CLI)."""

from __future__ import annotations

import sys
from collections.abc import Callable
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
from documenteer.services.technoteread import TechnoteReadError, read_technote
from documenteer.services.technoteupdate import (
    FileOutcome,
    TechnoteUpdateService,
    UpdateStatus,
)
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


def _update_options(command: Callable[..., None]) -> Callable[..., None]:
    """Apply the options `technote update` and its deprecated alias share.

    ``migrate`` delegates to ``update`` with the same arguments, so the two
    commands have to accept the same ones. Declaring them once keeps the
    alias from drifting away from the command it forwards to.
    """
    options = [
        click.option(
            "--dir",
            "-d",
            "root_dir",
            type=click.Path(exists=True, file_okay=False),
            default=".",
            help="Path to technote directory.",
        ),
        click.option(
            "--check",
            "check",
            is_flag=True,
            default=False,
            help=(
                "Report what would change without writing anything. Exits "
                "non-zero if the technote is out of date."
            ),
        ),
        click.option(
            "--ignore-file",
            "ignore_files",
            metavar="NAME",
            multiple=True,
            help=(
                "A file to leave alone, named by its path from the technote "
                "root (such as tox.ini). Repeatable."
            ),
        ),
        click.option(
            "--author-id",
            "-a",
            "author_ids",
            multiple=True,
            help=(
                "Author ID to add to technote.toml, for a legacy technote "
                "being converted. Repeatable."
            ),
        ),
        click.option(
            "--auto-delete",
            "-D",
            "auto_delete",
            is_flag=True,
            default=False,
            help=(
                "Delete a converted technote's deprecated files without "
                "prompting."
            ),
        ),
    ]
    for option in reversed(options):
        command = option(command)
    return command


@technote.command(name="update")
@_update_options
def technote_update(
    root_dir: str,
    ignore_files: tuple[str, ...],
    author_ids: tuple[str, ...],
    *,
    check: bool,
    auto_delete: bool,
) -> None:
    """Bring a technote repository up to the current standard.

    This command takes a technote repository from whatever state it is in to
    the current one, and running it again changes nothing. What it does
    depends on what it finds.

    A technote that still has a metadata.yaml file is a legacy technote, and
    is converted: technote.toml is written from the old metadata, index.rst
    is upgraded, README.rst and the supporting files are replaced, and the
    deprecated files are offered for deletion. Name the technote's authors
    with the `-a/--author-id` option — IDs in the Rubin author database, at
    https://github.com/lsst/lsst-texmf/blob/main/etc/authordb.yaml — or add
    them afterwards with 'documenteer technote add-author'.

    A technote that already has a technote.toml is refreshed instead: the
    standard tooling files (the CI workflow, Dependabot configuration,
    pre-commit configuration, .gitignore, Makefile, requirements.txt, and
    tox.ini) are rewritten from Documenteer's current templates, built from
    the metadata technote.toml declares. The technote's own writing is never
    touched, and neither is a conf.py that carries Sphinx configuration of
    its own; a conf.py holding nothing but what Documenteer generated is
    brought up to date.

    Each file is reported as updated, unchanged, or skipped. A file the
    technote has customized on purpose can be held back with
    ``--ignore-file``, which takes the path as reported (``--ignore-file
    tox.ini``) and may be repeated.

    Use ``--check`` to find out whether a technote is up to date without
    writing anything: it exits non-zero when a file would change, so a fleet
    campaign can detect drift and CI can enforce it.

    Review what changed with 'git diff' before committing.
    """
    _update_technote(
        root_dir,
        ignore_files=ignore_files,
        author_ids=author_ids,
        check=check,
        auto_delete=auto_delete,
    )


@technote.command(name="migrate")
@_update_options
def technote_migrate(
    root_dir: str,
    ignore_files: tuple[str, ...],
    author_ids: tuple[str, ...],
    *,
    check: bool,
    auto_delete: bool,
) -> None:
    """Convert a legacy technote (deprecated: use 'update').

    This is a deprecated alias for 'documenteer technote update', which
    converts a legacy metadata.yaml technote exactly as this command did and
    additionally refreshes a technote that has already been converted. It
    takes the same options and behaves identically.
    """
    click.echo(
        "'documenteer technote migrate' is deprecated; use "
        "'documenteer technote update' instead.",
        err=True,
    )
    _update_technote(
        root_dir,
        ignore_files=ignore_files,
        author_ids=author_ids,
        check=check,
        auto_delete=auto_delete,
    )


def _update_technote(
    root_dir: str,
    *,
    ignore_files: tuple[str, ...],
    author_ids: tuple[str, ...],
    check: bool,
    auto_delete: bool,
) -> None:
    """Run `technote update` against one directory.

    Shared by ``update`` and its deprecated ``migrate`` alias, so that the
    alias is the same command under an older name rather than a second
    implementation of it.
    """
    root = Path(root_dir)
    service = TechnoteUpdateService(root, AuthorDb())

    if service.is_legacy:
        _convert_legacy_technote(
            service,
            root,
            author_ids=author_ids,
            check=check,
            auto_delete=auto_delete,
        )
        return

    if not (root / "technote.toml").is_file():
        raise click.ClickException(
            f"{root} is not a technote: it has neither a technote.toml nor a "
            f"metadata.yaml."
        )

    if author_ids:
        click.echo(
            "Warning: --author-id applies only to a legacy technote being "
            "converted. Add an author to this technote with 'documenteer "
            "technote add-author'.",
            err=True,
        )

    try:
        outcomes = service.refresh_tooling(
            ignore_files=ignore_files, dry_run=check
        )
    except ValueError as e:
        # Metadata this technote.toml does not declare: something to fix in
        # the file, not a Documenteer bug, so report it rather than dumping
        # a traceback.
        raise click.ClickException(str(e)) from e

    for outcome in outcomes:
        click.echo(f"{outcome.path}: {_describe_update(outcome, check=check)}")

    changed = [outcome for outcome in outcomes if outcome.changed]
    if not changed:
        click.echo("The technote's tooling is up to date.")
        return

    noun = "file" if len(changed) == 1 else "files"
    if check:
        click.echo(
            f"{len(changed)} {noun} out of date. Run 'documenteer technote "
            f"update' to bring the technote up to date.",
            err=True,
        )
        raise SystemExit(1)
    click.echo(
        f"Updated {len(changed)} {noun}. Review the changes with 'git diff'."
    )


def _convert_legacy_technote(
    service: TechnoteUpdateService,
    root: Path,
    *,
    author_ids: tuple[str, ...],
    check: bool,
    auto_delete: bool,
) -> None:
    """Convert a technote that still uses metadata.yaml."""
    if check:
        # Every file the conversion writes would change, so there is nothing
        # to enumerate: what the technote needs is the conversion itself.
        click.echo(
            f"{root} is a legacy technote that has not been converted. Run "
            f"'documenteer technote update' to convert it.",
            err=True,
        )
        raise SystemExit(1)

    service.convert_legacy(author_ids=list(author_ids))

    if auto_delete or click.confirm("Delete deprecated files?"):
        service.delete_deprecated_files()


def _describe_update(outcome: FileOutcome, *, check: bool) -> str:
    """Phrase one file's outcome for the update report."""
    if outcome.status is UpdateStatus.updated:
        return "would update" if check else "updated"
    if outcome.status is UpdateStatus.skipped:
        return "skipped (--ignore-file)"
    if outcome.status is UpdateStatus.differs:
        return "differs from every Documenteer template; left unchanged"
    return "unchanged"


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
@click.option(
    "--ignore",
    "ignore_codes",
    metavar="CODE",
    multiple=True,
    help=(
        "Rule code to skip, such as TN105. Repeatable, and additive with "
        "the [technote.lint] ignore list in technote.toml."
    ),
)
def technote_lint(
    root_dir: str, ignore_codes: tuple[str, ...], *, strict: bool
) -> None:
    """Lint a technote's metadata and structure.

    This runs three groups of checks and reports each finding with a stable
    rule code (for example ``[R101]``). A code's prefix names the rule set it
    belongs to: ``TN`` rules check what any technote needs, and ``R`` rules
    check Rubin's conventions and services. Structural checks (``TN0xx`` and
    ``R0xx``) confirm that technote.toml exists, is valid TOML, and conforms
    to the technote schema, and that requirements.txt declares
    documenteer[technote] without pinning Sphinx separately. Metadata checks
    (``TN1xx`` and ``R1xx``) confirm that every author declares an internal_id
    that resolves in the Rubin author database, that a declared DOI is a DOI
    whose registered DataCite metadata still matches technote.toml, and that a
    CITATION.cff, where the repository has one, still matches it too. Content
    checks (``TN2xx``) confirm that the content declares a non-empty abstract
    using the abstract directive rather than an ordinary section heading.

    Only the author checks and the DataCite cross-check use the network, and
    they degrade differently: an unreachable author database is reported
    (R103), because an unresolved internal_id blocks a DOI from being minted,
    while an unreachable DataCite is silent.

    The rules about what a technote *publishes* — its abstract, and the title
    the DataCite and CITATION.cff comparisons use — read the document by
    building the technote with Sphinx, so this command needs the ``technote``
    extra (``pip install documenteer[technote]``). The build is quiet, writes
    nothing, and happens once per run.

    A directory with no content file and no conf.py is a technote that Sphinx
    does not build, so only the technote.toml checks (structural and metadata)
    apply to it.

    Each rule has a documentation page explaining the finding and its fix at
    https://documenteer.lsst.io/technotes/lint/, and the report links to the
    page for every rule it fires.

    The command exits non-zero when any error remains. Use ``--strict`` to
    promote warnings to errors.

    A rule that cannot be satisfied for a particular technote can be switched
    off, either in that technote's ``[technote.lint] ignore`` list or with
    ``--ignore CODE`` here. An ignored rule does not run at all — TN105 makes
    no DataCite request when it is ignored — and the summary names it, so CI
    output shows the rule is off rather than passing.
    """
    # Imported here, rather than at module scope, because the lint service
    # imports the `technote` package (a documenteer[technote] extra) at
    # module scope. Keeping it lazy means the rest of the CLI still loads
    # from a plain documenteer install, and a missing extra is an ImportError
    # from this one command rather than from `documenteer --help`.
    from documenteer.services.technotelint import (  # noqa: PLC0415
        LintContext,
        LintFinding,
        Severity,
        TechnoteLintService,
        rule_url,
    )

    author_db = AuthorDb()
    context = LintContext.from_dir(Path(root_dir), author_db)
    service = TechnoteLintService(context, ignore=ignore_codes)
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

    # Ignored rules are counted apart from errors and warnings: they did not
    # pass, they did not run, and a reader of CI output has to be able to see
    # the difference. Exit codes are unaffected by them.
    ignored = service.ignored_rules
    if ignored:
        listing = ", ".join(f"{rule.code} ({rule.source})" for rule in ignored)
        noun = "rule" if len(ignored) == 1 else "rules"
        ignored_summary = f"Ignored {len(ignored)} {noun}: {listing}."
    else:
        ignored_summary = None

    if not errors and not warnings:
        click.echo("✅ Technote lint passed with no issues.")
        if ignored_summary is not None:
            click.echo(ignored_summary)
        return

    click.echo(f"Found {len(errors)} error(s) and {len(warnings)} warning(s).")
    if ignored_summary is not None:
        click.echo(ignored_summary)

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
    content comparison suitable for CI. ``--check`` exits non-zero only when
    CITATION.cff exists and is stale; a repository with no CITATION.cff has
    simply not opted in, and passes.

    The technote's title is the one exception to technote.toml being
    canonical, because it is the one field a technote normally leaves to its
    document: the citation is titled by the document's top-level heading
    unless technote.toml declares a ``title``. The title is read by building
    the technote with Sphinx, so this command needs the ``technote`` extra
    (``pip install documenteer[technote]``) and reports a document Sphinx
    cannot read rather than citing the technote by its handle. A
    technote-series repository with no :file:`conf.py` is not built by
    Sphinx, and is generated from technote.toml alone.

    Nothing is read for a ``--check`` that has already been answered: an
    absent CITATION.cff passes before the technote is built at all, so a
    repository that never opted in is not failed by a document Sphinx cannot
    read.
    """
    root = Path(root_dir)
    toml_path = root / "technote.toml"
    if not toml_path.is_file():
        raise click.ClickException(f"No technote.toml found in {root}.")

    cff_path = root / CFF_FILENAME
    if check and not cff_path.is_file():
        # Answered before anything is read, the way the linter's TN106
        # early-returns on the same condition. A repository that never
        # adopted CITATION.cff has nothing whose staleness a title could
        # decide, and Rubin's shared workflow runs this check on every
        # technote — so failing one here on a document Sphinx cannot read
        # would fail repositories this check has no opinion about.
        click.echo(f"{cff_path} does not exist; nothing to check.")
        return

    document_title: str | None = None
    if (root / "conf.py").is_file():
        try:
            document_title = read_technote(root).title
        except TechnoteReadError as e:
            raise click.ClickException(
                f"Could not read the technote in {root}: {e}"
            ) from e

    try:
        service = TechnoteCffService.from_technote_toml(
            toml_path, document_title=document_title
        )
    except ValueError as e:
        # Malformed TOML, a DOI that is not a DOI, or metadata too sparse to
        # cite: all of them are something to fix in technote.toml, not a
        # Documenteer bug, so report the condition rather than a traceback.
        raise click.ClickException(str(e)) from e

    for warning in service.warnings:
        click.echo(f"Warning: {warning}", err=True)

    if check:
        # The absent case returned above, so the file is here to compare.
        if service.status(cff_path) is CffStatus.stale:
            click.echo(
                f"{cff_path} is out of date with {toml_path}. Run "
                f"'documenteer technote sync-cff' to regenerate it.",
                err=True,
            )
            raise SystemExit(1)
        click.echo(f"{cff_path} is up to date.")
        return

    if service.sync(cff_path) is CffStatus.current:
        click.echo(f"{cff_path} is already up to date.")
    else:
        click.echo(f"Wrote {cff_path}")
