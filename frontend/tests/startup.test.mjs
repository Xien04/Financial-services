import assert from "node:assert/strict";
import test from "node:test";

const origin = process.env.SMOKE_TEST_URL;
assert.ok(origin, "Set SMOKE_TEST_URL to a running frontend before running test:smoke.");

test("the running application serves the starter page semantics", async () => {
  const response = await fetch(origin);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<html[^>]*lang="en"/);
  assert.match(html, /href="#main"/);
  assert.match(html, /<main id="main"/);
  assert.match(html, /<h1[^>]*>A clearer view of your money\./);
  assert.doesNotMatch(html, /₱0\.00/);
});

test("same-origin API requests reach Django", {
  skip: process.env.SMOKE_TEST_API !== "1",
}, async () => {
  const response = await fetch(new URL("/api/v1/health/live", origin));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: "ok" });
});
