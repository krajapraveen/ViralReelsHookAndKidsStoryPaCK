/**
 * Feature Flags — Controlled rollout for studio creation engine features.
 * Only draftPersistenceV2 is ON by default. Others require explicit activation.
 */
const FEATURES = {
  draftPersistenceV2: true,    // P0: State-based draft lifecycle (draft → processing → completed)
  postGenerationLoop: true,    // P1: Rewrite/Change style/Enter battle CTAs after video result
  recentDraftsPanel: true,     // P1: Collapsed recent drafts panel in studio
  guidedStartV2: true,         // P1: Category-based idea generation with vibe picker
};

export default FEATURES;
