"""Documenteer's command-line interface (CLI)."""

from __future__ import annotations

from pathlib import Path

import click

from documenteer.services.technoteauthor import TechnoteAuthorService
from documenteer.services.technotemigration import TechnoteMigrationService
from documenteer.storage.authordb import AuthorDb
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
    required=True,
    prompt="Author ID",
)
@click.option(
    "--toml",
    "-t",
    "technote_toml",
    type=click.Path(exists=True),
    default="technote.toml",
    help="Path to technote.toml file",
)
def technote_add_author(author_id: str, technote_toml: str) -> None:
    """Add an author to technote.toml from the Rubin author DB.

    Author IDs are the keys in the "authors" map in authordb.yaml. See
    https://github.com/lsst/lsst-texmf/blob/main/etc/authordb.yaml
    """
    toml_path = Path(technote_toml)
    toml_file = TechnoteTomlFile.open(toml_path)
    author_db = AuthorDb()

    service = TechnoteAuthorService(toml_file, author_db)
    author = service.add_author_by_id(author_id)
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
    """Sync author info from authordb.yaml to technote.toml."""
    toml_path = Path(technote_toml)
    toml_file = TechnoteTomlFile.open(toml_path)
    author_db = AuthorDb()

    service = TechnoteAuthorService(toml_file, author_db)
    updated_authors = service.sync_authors()
    service.write_toml(toml_path)

    if len(updated_authors) == 0:
        click.echo("No authors to update")
        return
    else:
        click.echo(f"Synchronized authors to {toml_path}:")
        for a in updated_authors:
            click.echo(
                f"- {a.given_name if a.given_name else ''} {a.family_name} "
                f"({a.internal_id})"
            )


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
