# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from typing import List

import rich.table
import typer
from rich import box
from rich.console import Console

import kr8s
from kr8s.asyncio.objects import Table

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

console = Console()


async def get(
    resources: List[str] = typer.Argument(..., help="TYPE[.VERSION][.GROUP]"),
    all_namespaces: bool = typer.Option(
        False,
        "-A",
        "--all-namespaces",
        help="If present, list the requested object(s) across all namespaces. "
        "Namespace in current context is ignored even if specified with --namespace.",
    ),
    namespace: str = typer.Option(
        None,
        "-n",
        "--namespace",
    ),
    label_selector: str = typer.Option(
        "",
        "-l",
        "--selector",
        help="Selector (label query) to filter on, supports '=', '==', and '!='. "
        "(e.g. -l key1=value1,key2=value2). "
        "Matching objects must satisfy all of the specified label constraints.",
    ),
    field_selector: str = typer.Option(
        "",
        "--field-selector",
        help="Selector (field query) to filter on, supports '=', '==', and '!='. "
        "(e.g. --field-selector key1=value1,key2=value2). "
        "The server only supports a limited number of field queries per type. ",
    ),
    show_kind: bool = typer.Option(
        False,
        "--show-kind",
        help="If present, list the resource type for the requested object(s).",
    ),
    show_labels: bool = typer.Option(
        False,
        "--show-labels",
        help="When printing, show all labels as the last column "
        "(default hide labels column).",
    ),
    label_columns: List[str] = typer.Option(
        [],
        "-L",
        "--label-columns",
        help="Accepts a comma separated list of labels that are going to be presented as columns. "
        "Names are case-sensitive. "
        "You can also use multiple flag options like -L label1 -L label2...",
    ),
):
    """Display one or many resources.

    Prints a table of the most important information about the specified resources. You can filter the list using a
    label selector and the --selector flag. If the desired resource type is namespaced you will only see results
    in your current namespace unless you pass --all-namespaces.

    By specifying the output as 'template' and providing a Jinja2 template as the value of the --template flag, you
    can filter the attributes of the fetched resources.

    Use "kubectl-ng api-resources" for a complete list of supported resources.
    """
    resource_names = []
    # Support kubectl-ng get pod,svc
    if len(resources) == 1:
        resources = resources[0].split(",")
    # Support kubectl-ng get pod [name]
    elif len(resources) == 2:
        resources, resource_names = [[r] for r in resources]
    else:
        raise typer.BadParameter(
            f"Format '{' '.join(resources)}' not currently supported."
        )
    kubernetes = await kr8s.asyncio.api()
    if namespace:
        kubernetes.namespace = namespace
    if all_namespaces:
        kubernetes.namespace = kr8s.ALL
    for kind in resources:
        response = await kubernetes.get(
            kind,
            label_selector=label_selector,
            field_selector=field_selector,
            as_object=Table,
        )

        table = rich.table.Table(box=box.SIMPLE)
        table.add_column("Namespace", style="magenta", no_wrap=True)

        for column in response.column_definitions:
            if column["priority"] == 0:
                kwargs = {}
                if column["name"] == "Name":
                    kwargs = {"style": "cyan", "no_wrap": True}
                table.add_column(column["name"], **kwargs)

        for row in response.rows:
            if (
                not resource_names
                or row["object"]["metadata"]["name"] == resource_names[0]
            ):
                r = [
                    str(row)
                    for row, column in zip(row["cells"], response.column_definitions)
                    if column["priority"] == 0
                ]
                table.add_row(row["object"]["metadata"]["namespace"], *r)

        if not table.rows:
            if resource_names:
                console.print(f"No resources found with name {resource_names[0]}.")
            else:
                console.print(
                    f"No {kind} resources found in {kubernetes.namespace} namespace."
                )
            return

        console.print(table)
