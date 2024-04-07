# __title__ = "TokenBag"
# __version__ = '0.1.0'
import copy
import json

# import os
import logging
import random


class TokenBag:
    def __init__(self, debug: bool, log: str) -> None:
        self.config_filename = ""
        self.pool = {"bags": [], "tokens": {}}
        self.debug = debug
        self.logfile = log

        # Configuration updated in configure_pool
        # name of bag set to use
        self.bag_name = "Base"
        self.ranks = ["Unranked", "Bronze", "Silver", "Gold"]
        # Max tokens to draw in a pull
        self.max_draws = 10
        # Configure #tokens to draw from each bag in sequence up
        # to max_draws total tokens
        self.bag_draws = [(0, 1)]
        # use sums(True) or hit/miss(False)
        self.sums = False
        # hit/miss parameters
        self.hit_ceil_only_on_crit = True
        self.hit_ceil = 3
        self.hit_full = 2
        self.hit_partial = 1
        self.miss_ceil = 2
        # sum parameters
        self.sum_ceil = 4
        self.sum_full = 2
        self.sum_partial = 0
        self.sum_floor = -2

        # auto calculated or overridden by configure_pool
        self.max_rank = 3

        if debug:
            logging.basicConfig(
                format="%(levelname)s: %(message)s",
                filename=log,
                filemode="w",
                level=logging.ERROR,
            )
        else:
            logging.basicConfig(
                format="%(funcName)s@%(levelname)s #%(lineno)d: %(message)s",
                filename=log,
                filemode="w",
                level=logging.DEBUG,
            )

    def read_config_file(self, config_filename: str, bag_name: str = "") -> None:
        """Read configuration from a json text file"""
        self.config_filename = config_filename
        with open(config_filename) as f:
            config = json.load(f)
            self._initialize_pool(config, bag_name)

    def import_config_json(self, config_json: dict, bag_name: str = "") -> None:
        """Load configuration from a json dict"""
        self._initialize_pool(config_json, bag_name)

    def configure_pull(self, **kwargs) -> None:
        """Update configuration parameters for pulling from the bag(s)"""
        logger = logging.getLogger(__name__)

        # Respecify defaults to ensure they exist
        parameters = {
            "bag_name": self.bag_name,
            "ranks": self.ranks,
            "max_draws": self.max_draws,
            "sums": self.sums,
            "hit_ceil_only_on_crit": self.hit_ceil_only_on_crit,
            "hit_ceil": self.hit_ceil,
            "hit_full": self.hit_full,
            "hit_partial": self.hit_partial,
            "miss_ceil": self.miss_ceil,
            "sum_ceil": self.sum_ceil,
            "sum_full": self.sum_full,
            "sum_partial": self.sum_partial,
            "sum_floor": self.sum_floor,
            "bag_draws": self.bag_draws,
        }
        # Then update them from the passed in kwargs
        parameters.update(kwargs)

        self.bag_name = parameters["bag_name"]
        self.ranks = parameters["ranks"]
        self.max_draws = parameters["max_draws"]
        self.sums = parameters["sums"]

        self.hit_ceil_only_on_crit = parameters["hit_ceil_only_on_crit"]
        self.hit_ceil = parameters["hit_ceil"]
        self.miss_ceil = parameters["miss_ceil"]
        self.sum_ceil = parameters["sum_ceil"]
        self.sum_floor = parameters["sum_floor"]

        self.hit_full = parameters["hit_full"]
        self.hit_partial = parameters["hit_partial"]
        self.sum_full = parameters["sum_full"]
        self.sum_partial = parameters["sum_partial"]

        # [(bag, draws from bag before moving on), ...]
        # It will loop over the list to build the pull,
        # so to draw once from each bag in turn do [(0,1), (1,1)] for two bags
        self.bag_draws = parameters["bag_draws"]

        # This is auto calculated when initializing the pool, but allow overriding it
        if "max_rank" in parameters:
            self.max_rank = parameters["max_rank"]

        logger.debug("Updated configuration:")
        logger.debug(vars(self))

    def _initialize_pool(self, config: dict, bag_name: str = "") -> None:
        """Parse the stored config and generate the bag and token pools"""
        logger = logging.getLogger(__name__)
        if "Bag Pool" not in config or "Token Pool" not in config:
            logger.error("No `Bag Pool` (or no `Token Pool`) specified in config")
            return

        # Update configuration if given
        if "Config" in config:
            self.configure_pull(**(config["Config"]))
        if bag_name:
            # we want a command line arg to over-ride the config file,
            # so set this now if needed
            logger.debug(
                "Command-line overriding the bag_name from `%s` to `%s`",
                self.bag_name,
                bag_name,
            )
            self.bag_name = bag_name
        if self.bag_name not in config["Bag Pool"]:
            logger.error("Requested bag `%s` not found in Bag Pool", self.bag_name)
            return

        self.pool["bags"].clear()
        self.pool["tokens"].clear()
        max_rank = 0

        # Make the default token entry
        blank_token = {
            "Sum Value": 0,
            "Hit Value": 0,
            "Can Be Stolen": False,
            "Can Steal": False,
            "Can Latch": False,
            "Return to Bag": False,
            "Min Rank": 0,
            "Ends Draws": False,
            "Can Flip": False,
            "Enable Crit": -1,
            "Flipped": {"Can Flip": False},
        }
        # Update the default if it is specified
        if "Blank" in config["Token Pool"]:
            blank_token.update(config["Token Pool"]["Blank"])
        self.pool["tokens"]["Blank"] = blank_token
        logger.debug("Generated Default Blank Token:")
        logger.debug(blank_token)

        bag_spec = []
        bag_top = config["Bag Pool"][self.bag_name]
        if isinstance(bag_top, list):
            bag_spec = bag_top
        else:
            if "Config" in bag_top:
                self.configure_pull(**(bag_top["Config"]))
            if "Specification" in bag_top:
                bag_spec = bag_top["Specification"]

        for bag_def in bag_spec:
            bag_number = len(self.pool["bags"]) + 1
            logger.debug(
                "Found %d unique tokens in `%s` bag pool - bag %d",
                len(bag_def),
                self.bag_name,
                bag_number,
            )
            sub_bag = []
            for token_def in bag_def:
                if token_def not in config["Token Pool"]:
                    logger.debug(
                        "Couldn't find `%s` token definition in Token Pool, skipping",
                        len(token_def),
                        token_def,
                    )
                    continue
                logger.debug("Adding %d `%s` tokens", bag_def[token_def], token_def)
                # Add the correct number of this token to the bag
                tokens = [token_def for x in range(bag_def[token_def])]
                sub_bag.extend(tokens)

                # Add the token definition to the Token Pool
                token = json.loads(json.dumps(blank_token))
                token.update(config["Token Pool"][token_def])
                max_rank = max(max_rank, token["Min Rank"])
                if token["Can Flip"]:
                    # Add in the fully specified Flipped state,
                    # defaulted to the initial token state
                    fToken = json.loads(json.dumps(token))
                    fToken.update(token["Flipped"])
                    # These options are not supported after flipping
                    fToken["Can Flip"] = False
                    fToken["Can Steal"] = False
                    # fToken["Can Be Stolen"] = False
                    del fToken["Flipped"]
                    token["Flipped"].update(fToken)
                    max_rank = max(max_rank, token["Flipped"]["Min Rank"])

                if token_def not in self.pool["tokens"]:
                    self.pool["tokens"][token_def] = {}
                self.pool["tokens"][token_def].update(token)
                logger.debug("Writing token `%s`", token_def)
                logger.debug(token)
            self.pool["bags"].append(sub_bag)
            # Update the bag with the max rank found on a token
            self.max_rank = max_rank

    def get_pool(self) -> dict:
        """Return the stored bag and token pools"""
        return self.pool

    def get_rank_name(self, rank: int) -> str:
        """Convert an integer rank into its string rank name"""
        if rank >= len(self.ranks) or rank < 0:
            return ""
        return self.ranks[rank]

    def _replayable_pull(self) -> list:
        """Return a list of token names as the pull from the bag(s)"""
        the_pull = []
        logger = logging.getLogger(__name__)

        # Setup the original shuffled bags
        the_bags = {}
        bag_pulls = []
        draw_again = True
        draw_count = 0
        while draw_again:
            for bag, draws in self.bag_draws:
                if bag >= len(self.pool["bags"]):
                    logger.error("Requested bag index `%d` not found in Bag Pool", bag)
                    return the_pull

                # Add a shuffled bag to draw from
                if bag not in the_bags:
                    the_bags[bag] = list(range(len(self.pool["bags"][bag])))
                    random.shuffle(the_bags[bag])

                # Configure the draw(s) from the bag(s)
                for _ in range(0, draws):
                    if draw_count >= self.max_draws:
                        draw_again = False
                        break
                    bag_pulls.append(bag)
                    draw_count += 1

        # Now get the token associated for each draw from the corresponding bag
        for bag in bag_pulls:
            # Get the token name & definition
            p = the_bags[bag].pop(0)
            token_name = self.pool["bags"][bag][p]

            if token_name not in self.pool["tokens"]:
                logger.error("Requested token `%s` not found in Token Pool", token_name)
                return the_pull

            # We're returning the list of token names, so save it
            the_pull.append(token_name)

            # Check for abilities that alter the bag and shuffle order
            token = self.pool["tokens"][token_name]

            if token["Return to Bag"]:
                # Add this back to the bag and re-shuffle
                the_bags[bag].append(p)
                random.shuffle(the_bags[bag])

            # Check if token ends draws
            flippedEnd = (token["Can Flip"] and token["Flipped"]["Ends Draws"]) or (
                not token["Can Flip"] and token["Ends Draws"]
            )
            if flippedEnd:
                break

        return the_pull

    def _getHitMissSum(self, rank, minRank, inHit, inSum):
        """Handle navigating the hit/miss/sum values"""
        vHit = 0
        vMiss = 0
        vSum = 0

        if not self.sums:
            vHitMiss = 0
            if not isinstance(inHit, list):
                vHitMiss = inHit
            else:
                # Possible i values: 0, 1, 2 with four ranks 0-3
                # 0 = 1 - 1;
                # 1 = 2 - 1; 0 = 2 - 2;
                # 2 = 3 - 1; 1 = 3 - 2; 0 = 3 - 3
                i = rank - minRank
                vHitMiss = inHit[-1] if i >= len(inHit) else inHit[i]
            if vHitMiss > 0:
                vHit += vHitMiss
            else:
                vMiss += vHitMiss
        else:
            # Handle Sums
            if not isinstance(inSum, list):
                vSum += inSum
            else:
                # Handle looking up Min Rank to see where to start the value
                i = rank - minRank
                # If we want a position not in the list, take the last
                # Otherwise take the requested position
                vSum += inSum[-1] if i >= len(inSum) else inSum[i]

        return (vHit, abs(vMiss), vSum)

    def _pull(self, rank: int, the_pull: list) -> dict:
        """Evaluate a replayable pull via token names for a given rank"""
        draw_again = True
        rank_draw = 0
        rs = {
            "rank": rank,
            "can-crit": "-",
            "hits": 0,
            "misses": 0,
            "sum": 0,
            "fortune-hits": 0,
            "fortune-misses": 0,
            "fortune-sum": 0,
            "crit": False,
            "full": False,
            "partial": False,
            "failure": False,
            "fortune-crit": False,
            "fortune-full": False,
            "fortune-partial": False,
            "fortune-failure": False,
            "pull-order": [],
        }
        canBeStolen = []
        canBeStolenFlipped = []
        baseDrawEnded = False
        latchedFlipped = False
        latched = False
        finalHitMiss = self.sums
        finalFlippedHitMiss = self.sums
        finalSum = not self.sums
        finalFlippedSum = not self.sums
        canCrit = False

        bHit = 0
        bMiss = 0
        bSum = 0
        fHit = 0
        fMiss = 0
        fSum = 0

        while draw_again:
            if len(the_pull) == 0:
                break
            # Get the token definition
            p = the_pull.pop(0)
            token = self.pool["tokens"][p]
            rs["pull-order"].append(p)
            rank_draw += 1

            # Check rank compliance
            minRank = token["Min Rank"]
            hasRank = minRank <= rank
            # Default the flipped rank to an impossible rank
            minFlippedRank = self.max_rank + 1
            if token["Can Flip"]:
                # But make the min flipped rank valid if it can flip
                minFlippedRank = token["Flipped"]["Min Rank"]
            hasFlippedRank = minFlippedRank <= rank

            if not hasRank and not hasFlippedRank:
                continue

            if token["Enable Crit"] >= 0 and rank >= token["Enable Crit"]:
                rs["can-crit"] = "Y"
                canCrit = True

            bHit = 0
            bMiss = 0
            bSum = 0
            fHit = 0
            fMiss = 0
            fSum = 0

            # Handle Hits/Misses
            if hasRank:
                (bHit, bMiss, bSum) = self._getHitMissSum(
                    rank, minRank, token["Hit Value"], token["Sum Value"]
                )
                if not baseDrawEnded and not finalHitMiss:
                    rs["hits"] += bHit
                    rs["misses"] += bMiss
                if not baseDrawEnded and not finalSum:
                    rs["sum"] += bSum

            # Handle Flipped Hits/Misses/Sums
            if token["Can Flip"] and hasFlippedRank:
                (fHit, fMiss, fSum) = self._getHitMissSum(
                    rank,
                    token["Flipped"]["Min Rank"],
                    token["Flipped"]["Hit Value"],
                    token["Flipped"]["Sum Value"],
                )
                if not finalFlippedHitMiss:
                    rs["fortune-hits"] += fHit
                    rs["fortune-misses"] += fMiss
                if not finalFlippedSum:
                    rs["fortune-sum"] += fSum
            else:
                if not finalFlippedHitMiss:
                    rs["fortune-hits"] += bHit
                    rs["fortune-misses"] += bMiss
                if not finalFlippedSum:
                    rs["fortune-sum"] += bSum

            # Handle Stealing
            if token["Can Steal"] and hasRank:
                # Loop over all the prior pulls and see if they can be stolen

                for r in canBeStolen:
                    rToken = self.pool["tokens"][r]
                    rHasFlippedRank = bool(
                        rToken["Can Flip"]
                        and rToken["Flipped"]["Min Rank"] <= rank
                    )

                    if rToken["Can Be Stolen"] and not baseDrawEnded:
                        (bHit, bMiss, bSum) = self._getHitMissSum(
                            rank,
                            rToken["Min Rank"],
                            rToken["Hit Value"],
                            rToken["Sum Value"],
                        )
                        if rToken["Can Latch"] and latched:
                            latched = False
                        if not finalHitMiss:
                            rs["hits"] -= bHit
                            rs["misses"] -= bMiss
                        if not finalSum:
                            rs["sum"] -= bSum
                        canBeStolen.remove(r)
                        break

                for r in canBeStolenFlipped:
                    rToken = self.pool["tokens"][r]
                    rHasFlippedRank = (
                        False
                        if not rToken["Can Flip"]
                        else (rToken["Flipped"]["Min Rank"] <= rank)
                    )
                    if (rHasFlippedRank and rToken["Flipped"]["Can Latch"]) or (
                        rToken["Can Latch"] and not rHasFlippedRank
                    ):
                        latchedFlipped = False

                    if rHasFlippedRank:
                        (fHit, fMiss, fSum) = self._getHitMissSum(
                            rank,
                            rToken["Flipped"]["Min Rank"],
                            rToken["Flipped"]["Hit Value"],
                            rToken["Flipped"]["Sum Value"],
                        )
                    else:
                        (fHit, fMiss, fSum) = self._getHitMissSum(
                            rank,
                            rToken["Min Rank"],
                            rToken["Hit Value"],
                            rToken["Sum Value"],
                        )
                    if not finalFlippedHitMiss:
                        rs["fortune-hits"] -= fHit
                        rs["fortune-misses"] -= fMiss
                    if not finalFlippedSum:
                        rs["fortune-sum"] -= fSum
                    canBeStolenFlipped.remove(r)
                    break

            # Log that we pulled this one, now that we've processed the steals
            # Process base steals and flipped steals separately
            if token["Can Be Stolen"]:
                canBeStolen.insert(0, p)

            if (token["Can Be Stolen"] and not hasFlippedRank) or (
                hasFlippedRank and token["Flipped"]["Can Be Stolen"]
            ):
                canBeStolenFlipped.insert(0, p)

            if latchedFlipped:
                # TODO: Figure out a DSL for latching and check it here
                # Probably need to make sure we check for a previous latch here above
                # setting the latch
                latchedFlipped = False

            # Placeholder for Latching
            if (
                hasFlippedRank
                and token["Flipped"]["Can Latch"]
                or (token["Can Latch"] and not hasFlippedRank)
            ):
                latchedFlipped = True

            if latched and not baseDrawEnded:
                # TODO: Figure out a DSL for latching and check it here
                # Probably need to make sure we check for a previous latch here above
                # setting the latch
                latched = False

            # Placeholder for Latching
            if token["Can Latch"] and not baseDrawEnded:
                latched = True

            # Check if token ends draws
            if token["Ends Draws"]:
                # The replayable pull ends when no more tokens can be drawn for
                # fortune pulls. If only the base pull is ending here, we still
                # need to process the fortune pull
                baseDrawEnded = True

            if (
                rs["misses"] >= self.miss_ceil
                or rs["hits"] >= self.hit_ceil
            ) and (
                (self.hit_ceil_only_on_crit and canCrit
                ) or not self.hit_ceil_only_on_crit
            ):
                finalHitMiss = True
            if rs["sum"] >= self.sum_ceil or rs["sum"] <= self.sum_floor:
                finalSum = True
            if finalSum and finalHitMiss:
                baseDrawEnded = True

            if (
                rs["fortune-misses"] >= self.miss_ceil
                or rs["fortune-hits"] >= self.hit_ceil
            ) and (
                (self.hit_ceil_only_on_crit
                    and canCrit)
                or not self.hit_ceil_only_on_crit
            ):
                finalFlippedHitMiss = True
            if (
                rs["fortune-sum"] >= self.sum_ceil
                or rs["fortune-sum"] <= self.sum_floor
            ):
                finalFlippedSum = True
            if finalFlippedSum and finalFlippedHitMiss:
                draw_again = False

        if self.sums:
            # Base
            if canCrit and rs["sum"] >= self.sum_ceil:
                rs["crit"] = True
            elif rs["sum"] >= self.sum_full:
                rs["full"] = True
            elif rs["sum"] >= self.sum_partial:
                rs["partial"] = True
            else:
                rs["failure"] = True

            # Fortune
            if canCrit and rs["fortune-sum"] >= self.sum_ceil:
                rs["fortune-crit"] = True
            elif rs["fortune-sum"] >= self.sum_full:
                rs["fortune-full"] = True
            elif rs["fortune-sum"] >= self.sum_partial:
                rs["fortune-partial"] = True
            else:
                rs["fortune-failure"] = True
        else:
            # Base
            if canCrit and rs["hits"] >= self.hit_ceil:
                rs["crit"] = True
            elif rs["hits"] >= self.hit_full:
                rs["full"] = True
            elif rs["hits"] >= self.hit_partial:
                rs["partial"] = True
            else:
                rs["failure"] = True

            # Fortune
            if canCrit and rs["fortune-hits"] >= self.hit_ceil:
                rs["fortune-crit"] = True
            elif rs["fortune-hits"] >= self.hit_full:
                rs["fortune-full"] = True
            elif rs["fortune-hits"] >= self.hit_partial:
                rs["fortune-partial"] = True
            else:
                rs["fortune-failure"] = True
        return rs

    def pull(self) -> list:
        """Evaluate a pull from the bag(s)"""
        # Get the replayable pull list.
        # This handles "Return to Bag" abilities
        the_pull = self._replayable_pull()

        pulls = []
        for draw_halt in range(1, self.max_draws + 1):
            ranks = {"draws": draw_halt, "ranks": []}

            for rank in range(self.max_rank + 1):
                rs = self._pull(rank, copy.deepcopy(the_pull)[0:draw_halt])

                if self.sums:
                    del rs["hits"]
                    del rs["misses"]
                    del rs["fortune-hits"]
                    del rs["fortune-misses"]
                else:
                    del rs["sum"]
                    del rs["fortune-sum"]
                ranks["ranks"].append(copy.deepcopy(rs))
            pulls.append(copy.deepcopy(ranks))

        return pulls
