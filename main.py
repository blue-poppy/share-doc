from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from polars_readstat.polars_readstat_bindings import (  # ty: ignore
    readstat_metadata_json_rs,
)

SHARE_FILE_RE = re.compile(
    r"^sharew(?P<wave>\d+)_rel(?P<release>[^_]+)_(?P<module>.+)\.dta$"
)

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT.parent / "data-share"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "guides"

CATEGORY_TITLES = {
    "core": "Core Interview Modules",
    "special": "Special Modules",
    "sharelife": "SHARELIFE Modules",
    "generated": "Generated Modules",
    "auxiliary": "Auxiliary Datasets",
    "other": "Other Datasets",
}

CATEGORY_ORDER = {
    "core": 0,
    "special": 1,
    "sharelife": 2,
    "generated": 3,
    "auxiliary": 4,
    "other": 5,
}

MODULE_INFO = {
    "ac": ("Activities", "core"),
    "as": ("Assets", "core"),
    "ax": ("Accelerometry", "special"),
    "br": ("Behavioural Risks", "core"),
    "bs": ("Blood Sample", "core"),
    "cc": ("Childhood Circumstances", "sharelife"),
    "cf": ("Cognitive Function", "core"),
    "ch": ("Children", "core"),
    "co": ("Consumption", "core"),
    "cs": ("Chair Stand", "core"),
    "cv_r": ("Coverscreen on individual level", "core"),
    "dn": ("Demographics", "core"),
    "dq": ("Disability", "sharelife"),
    "dropoff": ("Paper-and-pencil drop-off", "special"),
    "ep": ("Employment and Pensions", "core"),
    "ep_ilextra": ("Israel EP add-on", "auxiliary"),
    "ex": ("Expectations", "core"),
    "fs": ("Financial Section", "sharelife"),
    "ft": ("Financial Transfers", "core"),
    "gl": ("General Life and Persecution", "sharelife"),
    "gs": ("Grip Strength", "core"),
    "gv_accelerometer_day": ("Accelerometer day-level dataset", "generated"),
    "gv_accelerometer_hour": ("Accelerometer hour-level dataset", "generated"),
    "gv_accelerometer_sleep": ("Accelerometer sleep dataset", "generated"),
    "gv_accelerometer_total": ("Accelerometer summary dataset", "generated"),
    "gv_big5": ("Big Five traits", "generated"),
    "gv_children": ("Generated child-level summaries", "generated"),
    "gv_dbs": ("Dried blood spot generated variables", "generated"),
    "gv_deprivation": ("Material and social deprivation", "generated"),
    "gv_exrates": ("Exchange rates and PPP variables", "generated"),
    "gv_grossnet": ("Net income derived from gross income", "generated"),
    "gv_health": ("Generated health indicators", "generated"),
    "gv_housing": ("Housing generated variables", "generated"),
    "gv_imputations": ("Multiple imputations", "generated"),
    "gv_isced": ("ISCED education recodes", "generated"),
    "gv_isco": ("Occupation and industry coding", "generated"),
    "gv_networks": ("Generated social network variables", "generated"),
    "gv_ssw": ("Social security wealth", "generated"),
    "gv_weights": ("Cross-sectional weights", "generated"),
    "hc": ("Health Care", "core"),
    "hh": ("Household Income", "core"),
    "ho": ("Housing", "core"),
    "hs": ("Health History / Health Section", "sharelife"),
    "interviewer_survey": ("Interviewer Survey", "auxiliary"),
    "it": ("Computer Use", "core"),
    "iv": ("Interviewer Observations", "core"),
    "mc": ("Mini Childhood", "core"),
    "mh": ("Mental Health", "core"),
    "pf": ("Peak Flow", "core"),
    "ph": ("Physical Health", "core"),
    "ra": ("Retrospective Accommodation", "sharelife"),
    "rc": ("Retrospective Children History", "sharelife"),
    "re": ("Retrospective Employment", "sharelife"),
    "rh": ("Retrospective Health Care", "sharelife"),
    "rp": ("Retrospective Partner History", "sharelife"),
    "sn": ("Social Networks", "core"),
    "sp": ("Social Support", "core"),
    "sr": ("Saving Regrets", "core"),
    "st": ("SHARELIFE demographics", "sharelife"),
    "te": ("Time Expenditure", "core"),
    "technical_variables": ("Technical variables", "special"),
    "vignettes": ("Vignettes", "special"),
    "wq": ("Work Quality", "sharelife"),
    "ws": ("Walking Speed", "core"),
    "xt": ("End-of-Life Interview", "core"),
}

WAVE3_OVERRIDES = {
    "ac": ("Retrospective Accommodation", "sharelife"),
    "cs": ("Childhood Section", "sharelife"),
    "hc": ("Retrospective Health Care", "sharelife"),
}


@dataclass(frozen=True)
class VariableMeta:
    name: str
    label: str
    dtype: str
    fmt: str


@dataclass(frozen=True)
class DatasetMeta:
    wave: int
    release: str
    module: str
    label: str
    category: str
    file_name: str
    row_count: int
    variables: tuple[VariableMeta, ...]

    @property
    def variable_count(self) -> int:
        return len(self.variables)

    @property
    def primary_key_hint(self) -> str:
        names = {variable.name for variable in self.variables}

        if self.module == "interviewer_survey":
            return "`intid`"
        if self.module == "gv_exrates":
            return "`country`"
        if self.module == "gv_accelerometer_day":
            return "`mergeid` + `measurementday`"
        if self.module == "gv_accelerometer_hour":
            return "`mergeid` + hour-level repeated rows"
        if self.module == "gv_accelerometer_sleep":
            return "`mergeid` + sleep-interval repeated rows"
        if "mergeid" in names:
            return "`mergeid`"
        if "intid" in names:
            return "`intid`"
        if "country" in names:
            return "`country`"
        if self.variables:
            return f"`{self.variables[0].name}`"
        return "See dataset"

    @property
    def read_example(self) -> str:
        return f'`ps.read_share_module("{self.module}", wave={self.wave})`'


def escape_cell(text: str | None) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def module_info(module: str, wave: int) -> tuple[str, str]:
    if wave == 3 and module in WAVE3_OVERRIDES:
        return WAVE3_OVERRIDES[module]

    if module in MODULE_INFO:
        return MODULE_INFO[module]

    if module.startswith("gv_"):
        return (module.replace("gv_", "").replace("_", " ").title(), "generated")

    return (module.replace("_", " ").title(), "other")


def parse_dataset(path: Path) -> DatasetMeta | None:
    match = SHARE_FILE_RE.match(path.name)
    if match is None:
        return None

    metadata = json.loads(readstat_metadata_json_rs(str(path)))
    wave = int(match["wave"])
    module = match["module"]
    label, category = module_info(module, wave)

    variables = tuple(
        VariableMeta(
            name=variable["name"],
            label=variable.get("label") or "",
            dtype=variable.get("type") or "",
            fmt=variable.get("format") or "",
        )
        for variable in metadata["variables"]
    )

    return DatasetMeta(
        wave=wave,
        release=match["release"],
        module=module,
        label=label,
        category=category,
        file_name=path.name,
        row_count=metadata["row_count"],
        variables=variables,
    )


def dataset_sort_key(dataset: DatasetMeta) -> tuple[int, str]:
    return (CATEGORY_ORDER.get(dataset.category, 99), dataset.module)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def ensure_output_dir(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f"Output path exists but is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def find_data_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Data path exists but is not a directory: {data_dir}")

    data_files = sorted(data_dir.glob("sharew*_rel*.dta"))
    if not data_files:
        raise FileNotFoundError(
            f"No SHARE Stata files found in {data_dir} matching sharew*_rel*.dta"
        )

    return data_files


def collect_datasets(data_files: list[Path]) -> dict[int, list[DatasetMeta]]:
    datasets_by_wave: dict[int, list[DatasetMeta]] = defaultdict(list)
    skipped_files = 0

    for path in data_files:
        try:
            dataset = parse_dataset(path)
        except Exception:
            LOGGER.exception("Failed to read metadata from %s", path)
            raise

        if dataset is None:
            skipped_files += 1
            LOGGER.warning("Skipping file with unexpected name: %s", path.name)
            continue

        datasets_by_wave[dataset.wave].append(dataset)

    if skipped_files:
        LOGGER.warning("Skipped %d file(s) with unexpected names", skipped_files)

    if not datasets_by_wave:
        raise RuntimeError("No valid SHARE datasets were parsed from the input files")

    return datasets_by_wave


def verify_written_files(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.exists()]
    empty = [path for path in paths if path.exists() and path.stat().st_size == 0]

    if missing or empty:
        details = []
        if missing:
            details.append("missing: " + ", ".join(str(path) for path in missing))
        if empty:
            details.append("empty: " + ", ".join(str(path) for path in empty))
        raise RuntimeError("Output verification failed; " + "; ".join(details))


def render_index(datasets_by_wave: dict[int, list[DatasetMeta]]) -> str:
    lines = [
        "---",
        "icon: lucide/book-marked",
        "---",
        "",
        "# SHARE Variable Dictionary",
        "",
        "This section is generated from the Stata metadata embedded in the local SHARE release files stored in `data/`.",
        "",
        "It is a file-level dictionary: for each wave and dataset, it lists every variable name together with the variable label, storage type, and Stata format.",
        "",
        "Use this dictionary when you already know the wave and need to answer questions like:",
        "",
        "- What does `ph006d10` mean in wave 9?",
        "- Which variables are inside `technical_variables`?",
        "- Does `gv_exrates` use `mergeid` or `country`?",
        "",
        "Use the official SHARE sources below for complementary tasks:",
        "",
        "- SHARE Data Documentation: <https://share-eric.eu/data/data-documentation>",
        "- SHARE Data & Documentation Tool: <https://www.share-datadocutool.org/>",
        "- SHARE Cross-Wave Comparison: <https://www.share-eric.eu/data/data-documentation/questionnaires/cross-wave-comparison>",
        "",
        "For module selection and naming conventions, see the [module guide](../modules.md).",
        "",
        "## Waves",
        "",
        "| Wave | Release | Datasets | Variable entries | Page |",
        "| --- | --- | --- | --- | --- |",
    ]

    for wave in sorted(datasets_by_wave):
        datasets = datasets_by_wave[wave]
        release = datasets[0].release if datasets else "-"
        variable_entries = sum(dataset.variable_count for dataset in datasets)
        lines.append(
            f"| Wave {wave} | `{release}` | {len(datasets)} | {variable_entries:,} | [Wave {wave}](wave-{wave}.md) |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The pages in this section reflect the files currently available in the local `data/` directory.",
            "- Regenerate this section with `uv run python scripts/generate_variable_dictionary.py`.",
            "- Variable names can change meaning across waves for SHARELIFE datasets, especially in wave 3. Check the wave-specific page before comparing short module codes like `ac`, `cs`, or `hc`.",
            "- This dictionary is not a cross-wave harmonisation table. For cross-wave item correspondences, use the official SHARE Cross-Wave Comparison.",
        ]
    )

    return "\n".join(lines) + "\n"


def render_wave_page(wave: int, datasets: list[DatasetMeta]) -> str:
    release = datasets[0].release if datasets else "-"
    total_variables = sum(dataset.variable_count for dataset in datasets)

    lines = [
        "---",
        "icon: lucide/list-tree",
        "---",
        "",
        f"# Wave {wave} Variable Dictionary",
        "",
        f"This page is generated from the local SHARE wave {wave} release `{release}` Stata files.",
        "",
        f"It covers {len(datasets)} datasets and {total_variables:,} variable entries for the files currently available in `data/`.",
        "",
        "[Back to variable dictionary](./index.md)",
        "",
        "## Overview",
        "",
        "| Module | Category | Meaning | Key | Variables | Rows | File |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for dataset in datasets:
        lines.append(
            "| "
            f"`{dataset.module}` | {dataset.category} | {escape_cell(dataset.label)} | {dataset.primary_key_hint} | "
            f"{dataset.variable_count:,} | {dataset.row_count:,} | `{dataset.file_name}` |"
        )

    grouped: dict[str, list[DatasetMeta]] = defaultdict(list)
    for dataset in datasets:
        grouped[dataset.category].append(dataset)

    for category in sorted(grouped, key=lambda item: CATEGORY_ORDER.get(item, 99)):
        lines.extend(["", f"## {CATEGORY_TITLES[category]}", ""])

        for dataset in grouped[category]:
            lines.extend(
                [
                    f"### `{dataset.module}` - {dataset.label}",
                    "",
                    f"- Dataset: `{dataset.file_name}`",
                    f"- Read with: {dataset.read_example}",
                    f"- Rows: {dataset.row_count:,}",
                    f"- Variables: {dataset.variable_count:,}",
                    f"- Key hint: {dataset.primary_key_hint}",
                    "",
                    "| Variable | Label | Type | Format |",
                    "| --- | --- | --- | --- |",
                ]
            )

            for variable in dataset.variables:
                lines.append(
                    "| "
                    f"`{escape_cell(variable.name)}` | {escape_cell(variable.label)} | "
                    f"`{escape_cell(variable.dtype)}` | `{escape_cell(variable.fmt)}` |"
                )

            lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    configure_logging()

    LOGGER.info("Project root: %s", PROJECT_ROOT)
    LOGGER.info("Data directory: %s", DATA_DIR)
    LOGGER.info("Output directory: %s", OUTPUT_DIR)

    ensure_output_dir(OUTPUT_DIR)
    data_files = find_data_files(DATA_DIR)
    LOGGER.info("Found %d input file(s)", len(data_files))

    datasets_by_wave = collect_datasets(data_files)
    total_datasets = sum(len(datasets) for datasets in datasets_by_wave.values())
    total_variables = sum(
        dataset.variable_count
        for datasets in datasets_by_wave.values()
        for dataset in datasets
    )
    LOGGER.info(
        "Parsed %d dataset(s) across %d wave(s), with %d variable entries",
        total_datasets,
        len(datasets_by_wave),
        total_variables,
    )

    written_paths: list[Path] = []

    for wave in sorted(datasets_by_wave):
        datasets = datasets_by_wave[wave]
        datasets.sort(key=dataset_sort_key)
        output_path = OUTPUT_DIR / f"wave-{wave}.md"
        write_file(output_path, render_wave_page(wave, datasets))
        written_paths.append(output_path)
        LOGGER.info(
            "Wrote wave %d page: %d dataset(s), %d variable entries -> %s",
            wave,
            len(datasets),
            sum(dataset.variable_count for dataset in datasets),
            output_path,
        )

    index_path = OUTPUT_DIR / "index.md"
    write_file(index_path, render_index(datasets_by_wave))
    written_paths.append(index_path)

    verify_written_files(written_paths)

    LOGGER.info("Wrote index page -> %s", index_path)
    LOGGER.info("Done: wrote %d markdown file(s)", len(written_paths))


if __name__ == "__main__":
    main()
