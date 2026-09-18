import { intLabel, varLabel } from "./labels.js";

/**
 * Turns a finished assessment into a short spoken summary.
 *
 * Reads only from the assessment, exactly like the on-screen summary: no new facts, no numbers
 * that are not already computed. Identifiers like `moisture_percent` become "Soil moisture" so the
 * voice does not read underscores aloud.
 */
export function spokenSummary(result) {
  const a = result.assessment;
  if (a.status === "insufficient_data") {
    const missing = a.missing_variables.map(varLabel).join(", ");
    return `I cannot recommend anything responsibly yet. ${a.missing_variables.length} essential details are missing: ${missing}. `
      + (result.questions?.length ? `To continue, ${result.questions[0]}` : "");
  }

  const parts = [];
  parts.push(`The main constraint on this land is ${varLabel(a.limiting_factor).toLowerCase()}.`);

  const top = a.drivers_ranked?.[0];
  if (top && top.variable !== a.limiting_factor) {
    parts.push(`The strongest explanation for your concern is ${varLabel(top.variable).toLowerCase()}.`);
  }
  if (a.hypothesis_note) parts.push(a.hypothesis_note);

  const steps = (a.sequence_detail || []).slice(0, 3);
  if (steps.length) {
    parts.push("Here is what to do, in order.");
    steps.forEach((s, i) => {
      const deferred = s.stage.startsWith("defer") ? ", which is deliberately held back until water is secured" : "";
      parts.push(`${i + 1}. ${intLabel(s.intervention)}${deferred}, over the ${s.time_horizon} term.`);
    });
    const deferredStep = (a.sequence_detail || []).find((s) => s.stage.startsWith("defer"));
    if (deferredStep && !steps.includes(deferredStep)) {
      parts.push(`${intLabel(deferredStep.intervention)} is worth doing later, but not yet, because it competes for scarce soil water.`);
    }
  }

  parts.push(`Confidence in this assessment is ${a.confidence.level}, based on ${a.confidence.n_supporting_claims} supporting studies.`);
  if (a.transfer_warnings?.length) {
    parts.push("One caution: some of the numbers come from studies in different conditions, so treat their size with care.");
  }
  return parts.join(" ");
}
