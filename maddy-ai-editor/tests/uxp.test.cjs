const test = require('node:test');
const assert = require('node:assert/strict');
const { inspectPremiere } = require('../integrations/premiere_uxp/adobe-adapter.js');

test('adapter inspects project and sequence through documented methods', async () => {
  const calls = [];
  const ppro = { Project: { async getActiveProject() {
    calls.push('project');
    return { name: 'Disposable project', async getActiveSequence() {
      calls.push('sequence'); return { name: 'Review copy' };
    }};
  }}};
  const result = await inspectPremiere(ppro);
  assert.deepEqual(calls, ['project', 'sequence']);
  assert.equal(result.project_name, 'Disposable project');
  assert.equal(result.sequence_name, 'Review copy');
  assert.equal(result.plugin_version, '0.1.0');
});

test('adapter reports missing project and missing active sequence', async () => {
  const missing = await inspectPremiere({ Project: { getActiveProject: async () => null }});
  assert.equal(missing.project_name, null);
  assert.equal(missing.sequence_name, null);
  const noSequence = await inspectPremiere({ Project: { getActiveProject: async () => ({
    name: 'Project', getActiveSequence: async () => null
  }) }});
  assert.equal(noSequence.sequence_name, null);
});

test('manifest restricts host and network permissions', () => {
  const manifest = require('../integrations/premiere_uxp/manifest.json');
  assert.equal(manifest.host.app, 'premierepro');
  assert.equal(manifest.host.minVersion, '25.6.0');
  assert.deepEqual(manifest.requiredPermissions, { network: { domains: ['http://127.0.0.1:8765'] }});
});
