# Acceptance Criteria Patterns

The x-opening-issue skill reads this file before it writes acceptance criteria, so that each new criterion is phrased in a shape a grader can actually run and grade.

- Trigger: a criterion asking for the whole test suite to finish green -> Rule: scope it to the same test selection continuous integration actually runs, naming the known-failing tests this repository already excludes, so a pre-existing unrelated failure cannot mark an in-scope change unmet.
- Trigger: a criterion whose check is an inline script that reaches an external service -> Rule: express the check as a repository test, or as an inspection of files already in the tree, and move any live external probe into the manual post-merge gate, because a grader refuses commands outside its read-only vocabulary and grades such a criterion unmet without running it.
