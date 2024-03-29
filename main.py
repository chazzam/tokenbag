import sys

if sys.version_info.major < 3 or sys.version_info.minor < 10:
  print("Python 3.10 or higher is required.")
  sys.exit(1)

import argparse
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
      "-d",
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
      default=100)
  parser.add_argument(
      "-p",
      "--pull-cap",
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

  args = parser.parse_args()
  pool = TokenBag(args.config, args.bag, args.debug, args.log, args.pull_cap)
  #print(pool.get_pool())
  print("\nRunning a pull")
  for i in range(args.number_of_draws):
    print(pool.pull(args.rank, 0))


main()
