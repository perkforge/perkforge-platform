// Tests only: use the same library version bundled by the pinned action; no API calls.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const load = createRequire(process.argv[2]);
load('release-please');
const { Simple } = load('release-please/build/src/strategies/simple');
const { DefaultVersioningStrategy } = load('release-please/build/src/versioning-strategies/default');
const { parseConventionalCommits } = load('release-please/build/src/commit');
const { Version } = load('release-please/build/src/version');
const { TagName } = load('release-please/build/src/util/tag-name');
const config = JSON.parse(readFileSync('release-please-config.json')).packages['.'];
const strategy = new Simple({
  github: { repository: { owner: 'fixture', repo: 'configuration' } },
  targetBranch: 'main', includeComponentInTag: config['include-component-in-tag'],
  includeVInTag: config['include-v-in-tag'], versionFile: config['version-file'],
  initialVersion: config['initial-version'],
  versioningStrategy: new DefaultVersioningStrategy({
    bumpMinorPreMajor: config['bump-minor-pre-major'],
    bumpPatchForMinorPreMajor: config['bump-patch-for-minor-pre-major'],
  }),
});
for (const [message, expected] of [
  ['fix: config', '0.1.1'], ['feat: tenant input', '0.2.0'],
  ['feat!: incompatible input', '1.0.0'],
  ['fix: input\n\nBREAKING CHANGE: incompatible config', '1.0.0'],
  ['feat: input (#12)', '0.2.0'], ['perf: reconcile', '0.1.1'],
  ['docs: guide', null], ['chore: tooling', null], ['test: fixture', null],
]) {
  const pr = await strategy.buildReleasePullRequest(
    parseConventionalCommits([{ sha: 'a'.repeat(40), message }]),
    { tag: new TagName(Version.parse('0.1.0')), sha: 'b'.repeat(40) },
  );
  assert.equal(pr?.version.toString() ?? null, expected, message);
  if (pr) {
    assert(pr.updates.some(update => update.path === 'VERSION'));
    assert(pr.updates.some(update => update.path === 'CHANGELOG.md'));
  }
}
const first = await strategy.buildReleasePullRequest(
  parseConventionalCommits([{ sha: 'a'.repeat(40), message: 'feat(release): version configuration' }]),
);
assert.equal(first.version.toString(), '0.1.0');
assert.equal(new TagName(first.version, undefined, undefined, true).toString(), 'v0.1.0');
const quiet = await strategy.buildReleasePullRequest(
  parseConventionalCommits([{ sha: 'a'.repeat(40), message: 'docs: initial guide' }]),
);
assert.equal(quiet, undefined);
console.log('Eleven actual release eligibility/version cases passed; no GitHub requests.');
