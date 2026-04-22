from __future__ import annotations


def render_migration(
    *,
    previous_migration: str,
    added: dict[str, tuple[str, str]],
    retranslated: dict[str, tuple[str, str]],
    source_hash_bumped: dict[str, str],
    retired: list[str],
) -> str:
    """Return the source text of a Django data-migration file.

    - `added`: key -> (text, hash) — brand-new keys, MT'd.
    - `retranslated`: key -> (text, hash) — source changed, IS was still MT.
    - `source_hash_bumped`: key -> new_hash — source changed, IS was human-edited.
    - `retired`: keys whose English source disappeared.
    """
    return (
        "from django.db import migrations\n"
        "\n"
        "\n"
        f"NEW_IS: dict[str, tuple[str, str]] = {_fmt_tuple_dict(added)}\n"
        "\n"
        f"RETRANSLATED: dict[str, tuple[str, str]] = {_fmt_tuple_dict(retranslated)}\n"
        "\n"
        f"SOURCE_HASH_BUMPED: dict[str, str] = {_fmt_str_dict(source_hash_bumped)}\n"
        "\n"
        f"RETIRED: list[str] = {_fmt_list(retired)}\n"
        "\n"
        "\n"
        "def forward(apps, schema_editor):\n"
        '    Translation = apps.get_model("translations", "Translation")\n'
        "    for key, (text, src_hash) in NEW_IS.items():\n"
        "        Translation.objects.update_or_create(\n"
        '            locale="is", key=key,\n'
        "            defaults={\n"
        '                "text": text,\n'
        '                "source_hash": src_hash,\n'
        '                "is_machine_translated": True,\n'
        '                "retired": False,\n'
        "            },\n"
        "        )\n"
        "    for key, (text, src_hash) in RETRANSLATED.items():\n"
        "        Translation.objects.update_or_create(\n"
        '            locale="is", key=key,\n'
        "            defaults={\n"
        '                "text": text,\n'
        '                "source_hash": src_hash,\n'
        '                "is_machine_translated": True,\n'
        '                "retired": False,\n'
        "            },\n"
        "        )\n"
        "    for key, src_hash in SOURCE_HASH_BUMPED.items():\n"
        '        Translation.objects.filter(locale="is", key=key).update(source_hash=src_hash)\n'  # noqa: E501
        "    for key in RETIRED:\n"
        '        Translation.objects.filter(locale="is", key=key).update(retired=True)\n'  # noqa: E501
        "\n"
        "\n"
        "def backward(apps, schema_editor):\n"
        '    Translation = apps.get_model("translations", "Translation")\n'
        "    for key in RETIRED:\n"
        '        Translation.objects.filter(locale="is", key=key).update(retired=False)\n'  # noqa: E501
        "    for key in NEW_IS:\n"
        '        Translation.objects.filter(locale="is", key=key).delete()\n'
        "\n"
        "\n"
        "class Migration(migrations.Migration):\n"
        f'    dependencies = [("translations", "{previous_migration}")]\n'
        "    operations = [migrations.RunPython(forward, backward)]\n"
    )


def _fmt_tuple_dict(d: dict[str, tuple[str, str]]) -> str:
    if not d:
        return "{}"
    lines = [
        f"    {_repr(k)}: ({_repr(a)}, {_repr(b)})," for k, (a, b) in sorted(d.items())
    ]
    return "{\n" + "\n".join(lines) + "\n}"


def _fmt_str_dict(d: dict[str, str]) -> str:
    if not d:
        return "{}"
    lines = [f"    {_repr(k)}: {_repr(v)}," for k, v in sorted(d.items())]
    return "{\n" + "\n".join(lines) + "\n}"


def _fmt_list(items: list[str]) -> str:
    if not items:
        return "[]"
    lines = [f"    {_repr(k)}," for k in sorted(items)]
    return "[\n" + "\n".join(lines) + "\n]"


def _repr(s: str) -> str:
    return repr(s)
