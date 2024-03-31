import sys

if sys.version_info.major < 3 or sys.version_info.minor < 10:
  print("Python 3.10 or higher is required.")
  sys.exit(1)

import argparse
import json
from tokenbag import TokenBag

def main():
  parser = argparse.ArgumentParser(
      description="Tokenbag: a simple token bag for Python.")
  #parser.add_argument("-v",
  #                    "--version",
  #                    action="version",
  #                    version=f"{tokenbag.__title__} {tokenbag.__version__}")
  parser.add_argument(
      "-c",
      "--config",
      help="Path to the configuration file. [bagpool.conf]",
      default="bagpool.conf")
  parser.add_argument(
      "-D",
      "--debug",
      action="store_false",
      help="Enable debug mode.",
      default=True)
  parser.add_argument("-l", "--log", help="Path to the log file.")
  parser.add_argument(
      "-r",
      "--rank",
      help=
      "Max rank of the skill. 0 - no rank, 1 - Bronze, 2 - Silver, 3 - Gold. [0]",
      type=int,
      default=0)
  parser.add_argument(
      "-n",
      "--number-of-draws",
      help="Number of draws to make for generating statistics. [100]",
      type=int,
      default=10)
  parser.add_argument(
      "-d",
      "--draw-cap",
      help=
      "Maximum number of tokens to pull in a single draw. 0 - unlimited [3]",
      type=int,
      default=3)
  parser.add_argument(
      "-b",
      "--bag",
      help="Specify name of bag (if more than one in config)",
      type=str,
      default="Base")
  parser.add_argument(
    "-s",
    "--sums",
    action="store_true",
    help="Calculate sums instead of hits/misses. [False]",
    default=False)

  args = parser.parse_args()
  pool = TokenBag(args.debug, args.log)
  pool.read_config_file(args.config, bag_name=args.bag)
  pool.configure_pull(
    max_draws=args.draw_cap,
    sums=args.sums
  )

  print(pool.get_pool())
  print("\nRunning a pull")
  for i in range(args.number_of_draws):
    #print(json.dumps(pool.pull(), indent=2))
    #print(json.dumps(pool.pull()))
    print(json.dumps(pool.pull()).replace("}", "}\n"))


main()
