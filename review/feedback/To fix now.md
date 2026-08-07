

# Fix as proposed:
01-prefetch-unfiltered
02-article-delete-orphans-s3
03-publish-fanout-async
08 & 09
10-use-article-draft-refactor - but note that this needs to happen without any changes based on 04 as that's being deferred
11-repo-images & 21-guard-test-projectimage
12-derive-summary-single-home
14-sanitizer-classname-blast-radius
15-author-facing-error-messages
16-article-serialisation-prefetch
17-untrack-vitest
18-remove-front-end-review
19-claude-md-stale-docs
20-mdxeditor-dependency-weight -> i like it, add the budget check


# Changes to fixes
07-empty-follow-rule - let's just allow this state. It happens sometimes. Change docs where we've stated it can't happen.


# Move to follow ups
04 and 05. These feel related and we'll do them in a follow up.
06 - the proper fix. put it in follow ups. Don't do anything on this right now.
13-prism bundle size
