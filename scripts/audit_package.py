"""Sprawdź czytelność ZIP i wymagane pliki, bez rozpakowywania."""
import argparse
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def inspect_archive(path, required=()):
    report = {"archive": str(path), "status": "failed", "required": list(required)}
    try:
        with ZipFile(path) as package:
            damaged = package.testzip()
            names = set(package.namelist())
            roots = {""} | {name.split("/", 1)[0] + "/" for name in names if "/" in name}
            matching = [root for root in sorted(roots)
                        if all(root + item in names for item in required)]
            report.update(member_count=len(names), damaged_member=damaged,
                          matching_roots=matching)
            if damaged is not None:
                report["reason"] = "Niezgodna suma CRC lub długość wpisu."
            elif not matching:
                report["reason"] = "Brak wspólnego katalogu z wymaganymi plikami."
            else:
                report["status"] = "passed"
    except (BadZipFile, OSError, EOFError, RuntimeError) as error:
        report["reason"] = f"{type(error).__name__}: {error}"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--require", action="append", default=[])
    args = parser.parse_args()
    result = inspect_archive(args.archive, args.require)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
