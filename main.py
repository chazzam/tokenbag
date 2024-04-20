import sys

if sys.version_info.major < 3 or sys.version_info.minor < 10:
    print("Python 3.10 or higher is required.")
    sys.exit(1)

import argparse
import copy
import json
import logging

from tokenbag import TokenBag


def main():
    parser = argparse.ArgumentParser(
        description="Tokenbag: a simple token bag for Python."
    )
    # parser.add_argument("-v",
    #                    "--version",
    #                    action="version",
    #                    version=f"{tokenbag.__title__} {tokenbag.__version__}")
    parser.add_argument(
        "-c",
        "--config",
        help="Path to the configuration file. [bagpool.conf]",
        default="bagpool.conf",
    )
    parser.add_argument(
        "-D", "--debug", action="store_true", help="Enable debug mode.", default=False
    )
    parser.add_argument("-l", "--log", help="Path to the log file.")
    parser.add_argument(
        "-r",
        "--rank",
        help=(
            "Max rank of the skill. 0 - no rank, "
            "1 - Bronze, 2 - Silver, 3 - Gold. "
            "'-1' for all. [-1]"
        ),
        type=int,
        default=-1,
    )
    parser.add_argument(
        "-n",
        "--number-of-draws",
        help="Number of draws to make for generating statistics. [10]",
        type=int,
        default=10,
    )
    parser.add_argument(
        "-d",
        "--draw-cap",
        help="Maximum number of tokens to pull in a single draw. 0 - unlimited [3]",
        type=int,
        default=3,
    )
    parser.add_argument(
        "-b",
        "--bag",
        help="Specify name of bag (if more than one in config)",
        type=str,
        default="Base",
    )
    parser.add_argument(
        "-s",
        "--sums",
        action="store_true",
        help="Calculate sums instead of hits/misses. [False]",
        default=False,
    )
    parser.add_argument(
        "-P",
        "--print-rank-numbers",
        action="store_true",
        help="Print Rank Numbers in some outputs [False]",
        default=False,
    )

    parser.add_argument(
        "-V",
        "--skip-verify-tests",
        action="store_true",
        help="Skip running verification tests on bag before running pulls [False]",
        default=False,
    )

    parser.add_argument(
        "-R",
        "--resistance",
        action="store_true",
        help="Run a Resistance Pull set rather than a standard draw [False]",
        default=False,
    )

    args = parser.parse_args()

    if not args.debug:
        logging.basicConfig(
            format="%(levelname)s: %(message)s",
            filename=args.log,
            filemode="w",
            level=logging.ERROR,
        )
    else:
        logging.basicConfig(
            format="%(funcName)s@%(levelname)s #%(lineno)d: %(message)s",
            filename=args.log,
            filemode="w",
            level=logging.DEBUG,
        )
    logger = logging.getLogger(__name__)

    pool = TokenBag(args.debug, args.log)
    pool.read_config_file(
        args.config, bag_name=args.bag, tests=bool(not args.skip_verify_tests)
    )
    pool.configure_pull(max_draws=args.draw_cap, sums=args.sums)

    # print(pool.get_pool())
    run_pulls = True
    if not args.skip_verify_tests:
        print("\nVerifying Tests")
        (run_pulls, results) = pool.verify_tests()
        print("\nTest Results:")
        print(json.dumps(results).replace("}", "}\n"))

    if not run_pulls:
        print("\n\nERROR: Test Verifications failed. Aborting pulls")
        return

    if not args.resistance:
        print("\nRunning a pull")
        rank_stats = {}
        total_stats = {}
        for _ in range(args.number_of_draws):
            for pull in pool.pull()[-1]["ranks"]:
                logger.debug(json.dumps(pull).replace("}", "}\n"))
                if pull["rank"] != args.rank and args.rank >= 0:
                    continue
                if pull["rank"] not in rank_stats:
                    rank_stats[pull["rank"]] = {
                        "rank": pull["rank"],
                        "crits": 0,
                        "fulls": 0,
                        "partials": 0,
                        "failures": 0,
                        "fortune-crits": 0,
                        "fortune-fulls": 0,
                        "fortune-partials": 0,
                        "fortune-failures": 0,
                    }
                if len(total_stats) == 0:
                    total_stats = copy.deepcopy(rank_stats[pull["rank"]])
                stats = rank_stats[pull["rank"]]
                crit = "^" if pull["can-crit"] == "Y" else " "

                name = pull["rank"]
                if not args.print_rank_numbers:
                    name = pool.get_rank_name(pull["rank"])

                base = ""
                if pull["failure"]:
                    base = " "
                    stats["failures"] += 1
                    total_stats["failures"] += 1
                elif pull["crit"]:
                    base = "^"
                    stats["crits"] += 1
                    total_stats["crits"] += 1
                elif pull["full"]:
                    base = "+"
                    stats["fulls"] += 1
                    total_stats["fulls"] += 1
                else:
                    base = "-"
                    stats["partials"] += 1
                    total_stats["partials"] += 1

                fortune = ""
                if pull["fortune-failure"]:
                    fortune = " "
                    stats["fortune-failures"] += 1
                    total_stats["fortune-failures"] += 1
                elif pull["fortune-crit"]:
                    fortune = "^"
                    stats["fortune-crits"] += 1
                    total_stats["fortune-crits"] += 1
                elif pull["fortune-partial"]:
                    fortune = "-"
                    stats["fortune-partials"] += 1
                    total_stats["fortune-partials"] += 1
                else:
                    fortune = "+"
                    stats["fortune-fulls"] += 1
                    total_stats["fortune-fulls"] += 1

                if args.sums:
                    print(
                        f"{crit}{pull['rank']}:"
                        f" {pull['sum']:+}b{base}"
                        f" {pull['fortune-sum']:+}f{fortune}"
                        f" pull: {', '.join(pull['fortune-pull-order'])}"
                    )
                else:
                    print(
                        f"{name:>10}:{crit}"
                        f" {pull['hits']}/{pull['misses']}b{base}"
                        f" {pull['fortune-hits']}/{pull['fortune-misses']}f{fortune}"
                        f" pull: {', '.join(pull['fortune-pull-order'])}"
                    )

        print(f"\nSummary Counts: (from {args.number_of_draws} pulls)")
        for rank in sorted(rank_stats.keys()):
            stats = rank_stats[rank]
            name = rank
            if not args.print_rank_numbers:
                name = pool.get_rank_name(rank)
            print(
                f"{name:>14}: "
                f".{stats['failures']}f{stats['fortune-failures']} "
                f"-{stats['partials']}f{stats['fortune-partials']} "
                f"+{stats['fulls']}f{stats['fortune-fulls']} "
                f"^{stats['crits']}f{stats['fortune-crits']} "
            )
        name = "Totals"
        print(
            f"\n{name:>14}: "
            f".{total_stats['failures']}f{total_stats['fortune-failures']} "
            f"-{total_stats['partials']}f{total_stats['fortune-partials']} "
            f"+{total_stats['fulls']}f{total_stats['fortune-fulls']} "
            f"^{total_stats['crits']}f{total_stats['fortune-crits']} "
        )
    else:
        print("\nRunning a Resistance pull")
        rank_stats = {}
        total_stats = {}
        for _ in range(args.number_of_draws):
            record = ""
            for pull in pool.resistance_pull()[-1]["ranks"]:
                logger.debug(json.dumps(pull).replace("}", "}\n"))
                if pull["rank"] != args.rank and args.rank >= 0:
                    continue
                if pull["rank"] not in rank_stats:
                    rank_stats[pull["rank"]] = {
                        "rank": pull["rank"],
                        "costs": {
                            "lost": 0,
                            "taken": 0,
                            "mitigated": 0,
                        },
                    }
                if len(total_stats) == 0:
                    total_stats = copy.deepcopy(rank_stats[pull["rank"]])
                stats = rank_stats[pull["rank"]]

                name = pull["rank"]
                if not args.print_rank_numbers:
                    name = pool.get_rank_name(pull["rank"])

                total_stats["costs"]["mitigated"] += pull["costs"]["mitigated"]
                total_stats["costs"]["taken"] += pull["costs"]["taken"]
                total_stats["costs"]["lost"] += pull["costs"]["lost"]
                stats["costs"]["mitigated"] += pull["costs"]["mitigated"]
                stats["costs"]["taken"] += pull["costs"]["taken"]
                stats["costs"]["lost"] += pull["costs"]["lost"]

                if not record:
                    record = f"{''.ljust(12)}{', '.join(pull['pull-order'])}\n"
                record += (
                    f"{name:>10}:"
                    f" {pull['costs']['mitigated']:>3}+"
                    f" {pull['costs']['taken']:>3}~"
                    f" {pull['costs']['lost']:>3}$\n"
                )
            print(record)

        print(f"\nSummary Counts: (from {args.number_of_draws} pulls)")
        for rank in sorted(rank_stats.keys()):
            stats = rank_stats[rank]
            name = rank
            if not args.print_rank_numbers:
                name = pool.get_rank_name(rank)
            print(
                f"{name:>10}:"
                f" {stats['costs']['mitigated']:>3}+"
                f" {stats['costs']['taken']:>3}~"
                f" {stats['costs']['lost']:>3}$"
            )
        name = "Totals"
        print(
            f"\n{name:>10}:"
            f" {total_stats['costs']['mitigated']:>3}+"
            f" {total_stats['costs']['taken']:>3}~"
            f" {total_stats['costs']['lost']:>3}$"
        )


main()
