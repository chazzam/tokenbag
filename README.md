# tokenbag

pull tokens from a blind bag

## Tests

The basic format of a test definition is `<rank> <sum test> <hit/miss test>`. Spaces inside a test definition should be ignored.

The rank is a numerical rank specification, expected to be from 0 to 3, but will only be tested up to the calculated Max Rank of the bag.

The '$' (dollar sign) is used to separate the basic result from the fortune / flipped result.

Only one of the sum or hit/miss tests must be specified, but either may be specified in any order.

### Result specification

The test result is specified by a single character:

- '.' (period) = The pull ends in a Failure
- '-' (hyphen) = The pull ends in a Partial Success, or success with complications
- '+' (plus sign) = The pull ends in a Full Success
- '^' (carat) = The pull ends in a Critical Success

 For any given sub test string, the Result will be the final character in the sub test.

### Sum Test Specification

A Sum test definition begins with '=' (equal sign) and could look like this: `=-2. $-2.`. This says the basic sum would be '-2' and result in a failure. The fortune sum would also be '-2' and also result in a failure.

### Hit/Miss Test Specification

A Hit/Miss test definition begins with '&' (ampersand), specifies the Hits / Misses Result, and could look like this: `& 3/1+ $ 4/0^`. This specifies that the basic result would have three hits and one miss, resulting in a Full Success. The fortune result would have four hits and no misses, resulting in a Critical Success.
