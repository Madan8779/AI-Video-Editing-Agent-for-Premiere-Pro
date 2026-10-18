/* Adobe calls stay isolated here. Supported documentation since Premiere 25.6.
 * https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/project/
 * Must still be validated in the installed host before claiming integration. */
async function inspectPremiere(ppro) {
  const project = await ppro.Project.getActiveProject();
  const sequence = project ? await project.getActiveSequence() : null;
  return {
    plugin_version: "0.1.0",
    project_name: project ? project.name : null,
    sequence_name: sequence ? sequence.name : null,
    host_version: "unreported"
  };
}
module.exports = { inspectPremiere };
