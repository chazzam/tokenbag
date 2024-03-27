#__title__ = "tokenbag"
#__version__ = '0.1.0'
import json
import os


def build_pool(config_filename, bag_name):
  """Read the input config and generate the token bags for this run"""
  pool = {"bags": [], "tokens": {}}
  config = {}
  with open(config_filename) as f:
    config = json.load(f)

  if "Bag Pool" not in config or "Token Pool" not in config:
    return pool
  if bag_name not in config["Bag Pool"]:
    return pool

  # Make the default token entry
  blank_token = {
      "Sum Value": 0,
      "Hit Value": 0,
      "Can Be Stolen": False,
      "Can Steal": False,
      "Can Latch": False,
      "Return to Bag": False,
      "Min Rank": 0,
      "Ends Pulls": False,
      "Can Flip": False,
      "Flipped": {}
  }
  # Update the default if it is specified
  if "Blank" in config["Token Pool"]:
    blank_token.update(config["Token Pool"]["Blank"])

  for bags_def in config["Bag Pool"][bag_name]:
    for bag_def in bags_def:
      sub_bag = []
      for token_def in bag_def:
        if token_def not in config["Token Pool"]:
          continue
        # Add the correct number of this token to the bag
        sub_bag.extend([token_def for x in range(bag_def[token_def])])

        # Add the token definition to the Token Pool
        token = json.loads(json.dumps(blank_token))
        token.update(config["Token Pool"][token_def])
        pool["tokens"].append(token)
      pool["bags"].append(sub_bag)

  return pool
