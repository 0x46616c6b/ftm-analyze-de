"""
Analyze FollowTheMoney entities without OpenAleph:

    ftm-analyze-de analyze -i entities.ftm.json -o results.ftm.json
"""

import argparse
import json
import sys

from followthemoney import model


def _analyze(args: argparse.Namespace) -> None:
    # upstream logs to stdout; keep it for the entity stream
    stdout, sys.stdout = sys.stdout, sys.stderr
    from ftm_analyze_de.pipeline import analyze_entity_de

    source = open(args.input, encoding="utf-8") if args.input != "-" else sys.stdin
    target = open(args.output, "w", encoding="utf-8") if args.output != "-" else stdout
    with source, target:
        for line in source:
            if not line.strip():
                continue
            entity = model.get_proxy(json.loads(line))
            results, register = analyze_entity_de(entity, overwrite_lang=args.overwrite_lang)
            for result in [*results, *register]:
                target.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ftm-analyze-de")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="Analyze a stream of entities (JSON lines)")
    analyze.add_argument("-i", "--input", default="-", help="input file, default stdin")
    analyze.add_argument("-o", "--output", default="-", help="output file, default stdout")
    analyze.add_argument("--overwrite-lang", action="store_true", help="detect languages again")
    analyze.set_defaults(func=_analyze)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
