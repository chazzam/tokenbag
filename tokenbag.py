#__title__ = "TokenBag"
#__version__ = '0.1.0'
import copy
import json
#import os
import logging
import random

class TokenBag:
  def __init__(self, config_filename: str, bag_name:str, debug: bool, log:str, pulls:int) -> None:
    self.config_filename = config_filename
    self.config = {}
    self.bag_name = bag_name
    self.pool = {"bags": [], "tokens": {}}
    self.debug = False
    self.logfile = log
    self.max_pulls = pulls

    if debug:
      logging.basicConfig(
        format='%(levelname)s: %(message)s',
        filename=log,
        filemode='w',
        level=logging.ERROR)
    else:
      logging.basicConfig(
        format='%(funcName)s@%(levelname)s #%(lineno)d: %(message)s',
        filename=log,
        filemode='w',
        level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    with open(config_filename) as f:
      self.config = json.load(f)

    if "Bag Pool" not in self.config or "Token Pool" not in self.config:
      logger.error("No `Bag Pool` (or no `Token Pool`) specified in %s", self.config_filename)
      return
    if self.bag_name not in self.config["Bag Pool"]:
      logger.error("Requested bag `%s` not found in Bag Pool", self.bag_name)
      return

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
        "Flipped": {
          "Can Flip": False
        }
    }
    # Update the default if it is specified
    if "Blank" in self.config["Token Pool"]:
      blank_token.update(self.config["Token Pool"]["Blank"])
    self.pool["tokens"]["Blank"] = blank_token
    logger.debug("Generated Default Blank Token:")
    logger.debug(blank_token)

    for bag_def in self.config["Bag Pool"][self.bag_name]:
      # This should yield an array of bags
      bag_number= len(self.pool["bags"]) + 1
      logger.debug(
        "Found %d unique tokens in `%s` bag pool - bag %d",
        len(bag_def),
        self.bag_name,
        bag_number)
      sub_bag = []
      for token_def in bag_def:
        if token_def not in self.config["Token Pool"]:
          logger.debug(
            "Couldn't find `%s` token definition in Token Pool, skipping",
            len(token_def),
            token_def)
          continue
        logger.debug("Adding %d `%s` tokens", bag_def[token_def], token_def)
        # Add the correct number of this token to the bag
        tokens = [token_def for x in range(bag_def[token_def])]
        sub_bag.extend(tokens)

        # Add the token definition to the Token Pool
        token = json.loads(json.dumps(blank_token))
        token.update(self.config["Token Pool"][token_def])
        if token["Can Flip"]:
          # Add in the fully specified Flipped state, defaulted to the initial token state
          fToken = json.loads(json.dumps(token))
          fToken.update(token["Flipped"])
          # These options are not supported after flipping
          fToken["Can Flip"] = False
          fToken["Can Steal"] = False
          fToken["Can Be Stolen"] = False
          del fToken["Flipped"]
          token["Flipped"].update(fToken)

        if token_def not in self.pool["tokens"]:
          self.pool["tokens"][token_def] = {}
        self.pool["tokens"][token_def].update(token)
        logger.debug("Writing token `%s`", token_def)
        logger.debug(token)
      self.pool["bags"].append(sub_bag)

  def get_pool(self) -> dict:
    """Read the input config and generate the token bags for this run"""
    return self.pool

  def _getHitMissSum(self, rank, minRank, inHit, inSum):
    """Handle navigating the hit/miss/sum values"""
    vHit = 0
    vMiss = 0
    vSum = 0

    if not isinstance(inHit, list):
      if inHit > 0:
        vHit += inHit
      else:
        vMiss += inHit
    else:
      # Handle looking up Min Rank to see where to start the value
      i = rank - minRank
      vHitMiss = 0
      if len(inHit) <= i:
        # Can just take the last element
        vHitMiss = inHit[-1]
      else:
        # Use i as the value index
        vHitMiss = inHit[i]
      if vHitMiss > 0:
        vHit += vHitMiss
      else:
        vMiss += vHitMiss

    # Handle Sums
    if not isinstance(inSum, list):
      vSum += inSum
    else:
      # Handle looking up Min Rank to see where to start the value
      i = rank - minRank
      if len(inSum) <= i:
        # Can just take the last element
        vSum += inSum[-1]
      else:
        # Use i as the value index
        vSum += inSum[i]

    return (vHit, abs(vMiss), vSum)

  def pull(self, rank:int, iBag:int) -> dict:
    """Evaluate a pull by bag indices"""
    # Build initial pulls list by randomly shuffling the bag
    bag = self.pool["bags"][iBag]
    bag_size = len(bag)
    pulls = list(range(bag_size))
    random.shuffle(pulls)
    canBeStolen = []

    rs = {
      "rank": rank,
      "pulls": 0,
      "hits": 0,
      "misses": 0,
      "sum": 0,
      "fortune-hits": 0,
      "fortune-misses": 0,
      "fortune-sum": 0,
      "actual-pulls": []
    }

    bHit = 0
    bMiss = 0
    bSum = 0
    fHit = 0
    fMiss = 0
    fSum = 0

    pull_again = True
    latched = False
    while pull_again:
      # Get the token definition
      p = pulls.pop(0)
      token = self.pool["tokens"][bag[p]]
      rs["pulls"] += 1
      rs["actual-pulls"].append(bag[p])

      # Check rank compliance
      minRank = token["Min Rank"]

      if minRank > rank:
        continue

      bHit = 0
      bMiss = 0
      bSum = 0
      fHit = 0
      fMiss = 0
      fSum = 0

      # Handle Hits/Misses
      (bHit, bMiss, bSum) = self._getHitMissSum(
        rank,
        minRank,
        token["Hit Value"],
        token["Sum Value"])
      rs["hits"] += bHit
      rs["misses"] += bMiss
      rs["sum"] += bSum

      # Handle Flipped Hits/Misses/Sums
      if token["Can Flip"] and rank <= token["Flipped"]["Min Rank"]:
        (fHit, fMiss, fSum) = self._getHitMissSum(
          rank,
          token["Flipped"]["Min Rank"],
          token["Flipped"]["Hit Value"],
          token["Flipped"]["Sum Value"])
        rs["fortune-hits"] += fHit
        rs["fortune-misses"] += fMiss
        rs["fortune-sum"] += fSum
      else:
        rs["fortune-hits"] += bHit
        rs["fortune-misses"] += bMiss
        rs["fortune-sum"] += bSum

      # Handle Stealing
      if token["Can Steal"]:
        # Loop over all the prior pulls and see if they can be stolen
        rStolen = copy.deepcopy(canBeStolen)
        rStolen.reverse()
        handledBaseSteal = False
        baseToken = 0

        for r in rStolen:
          rToken = self.pool["tokens"][bag[r]]

          if rToken["Can Be Stolen"] and not handledBaseSteal:
            if rToken["Can Latch"] and latched:
              latched = False
            (bHit, bMiss, bSum) = self._getHitMissSum(
              rank,
              rToken["Min Rank"],
              rToken["Hit Value"],
              rToken["Sum Value"])
            rs["hits"] -= bHit
            rs["misses"] -= bMiss
            rs["sum"] -= bSum
            handledBaseSteal = True
            baseToken = r
            if not rToken["Can Flip"] or rToken["Flipped"]["Can Be Stolen"]:
              rs["fortune-hits"] -= bHit
              rs["fortune-misses"] -= bMiss
              rs["fortune-sum"] -= bSum
            break

        if handledBaseSteal:
            canBeStolen.remove(baseToken)

      # Log that we pulled this one, now that we've processed the steals
      if token["Can Be Stolen"] or (token["Can Flip"] and token["Flipped"]["Can Be Stolen"]):
        canBeStolen.append(p)

      if latched:
        # TODO: Figure out a DSL for latching and check it here
        # Probably need to make sure we check for a previous latch here above
        # setting the latch
        latched = False

      # Handle returns
      if token["Return to Bag"]:
        # Add this back to the bag and re-shuffle
        pulls.append(p)
        random.shuffle(pulls)

      # Placeholder for Latching
      if token["Can Latch"]:
        latched = True

      # Check if token ends pulls
      if token["Ends Pulls"]:
        break

      # Check if we hit the max token pull
      if rs["pulls"] >= self.max_pulls:
        break
    return rs
