/**
 * Static Homepage Banner Data — same-origin, no CDN/proxy dependency.
 * All images served from /public/homepage-banners/ (compressed JPEG, 8-75KB).
 * Cross-browser safe: desktop Chrome, Safari, mobile Chrome, mobile Safari.
 */

const STATIC_BANNERS_LIST = [
  { slug: "the-painter-of-stars", title: "The Painter of Stars", hook_text: "Every night, an old woman climbed the tallest hill with a bucket of stardust...", animation_style: "watercolor", story_prompt: "Every night, an old woman climbed the tallest hill with a bucket of stardust. She dipped her brush in the glowing dust and painted new stars across the sky. One evening a child followed her and asked why. She smiled and said: because the sky forgets its own beauty, someone must remind it.", job_id: "261430a2-28f5-4c40-bac2-35f8d275fae7", hero_img: "/homepage-banners/the-painter-of-stars-hero.jpg", card_img: "/homepage-banners/the-painter-of-stars-card.jpg" },
  { slug: "the-crystal-cave", title: "The Crystal Cave", hook_text: "Deep beneath the mountains, a young fox named Sage discovers a hidden cave filled with glowing crystals...", animation_style: "cartoon_2d", story_prompt: "Deep beneath the mountains, a young fox named Sage discovers a hidden cave filled with glowing crystals. Each crystal holds a memory from a different time. When Sage touches one, she is transported to a magical forest where trees whisper secrets.", job_id: "b95498d4-2e2a-4472-8dac-f8a253d07dfd", hero_img: "/homepage-banners/the-crystal-cave-hero.jpg", card_img: "/homepage-banners/the-crystal-cave-card.jpg" },
  { slug: "a-cats-big-city-adventure", title: "A Cat's Big City Adventure", hook_text: "A short test story about a cat who goes on an adventure in the city and meets new friends along the way...", animation_style: "watercolor", story_prompt: "A short test story about a cat who goes on an adventure in the city and meets new friends along the way.", job_id: "da85bb12-785b-4906-8fba-48de780f4a2e", hero_img: "/homepage-banners/a-cats-big-city-adventure-hero.jpg", card_img: "/homepage-banners/a-cats-big-city-adventure-card.jpg" },
  { slug: "clover-and-the-golden-key", title: "Clover and the Golden Key", hook_text: "A brave little rabbit named Clover explored the enchanted meadow...", animation_style: "watercolor", story_prompt: "A brave little rabbit named Clover explored the enchanted meadow. She discovered a golden key under an old oak tree. The key opened a secret door to a world of talking flowers and singing birds.", job_id: "13ddd5d5-307c-4c45-8ac6-e349344d8abf", hero_img: "/homepage-banners/clover-and-the-golden-key-hero.jpg", card_img: "/homepage-banners/clover-and-the-golden-key-card.jpg" },
  { slug: "the-discovery", title: "The Discovery", hook_text: "On a bright sunny morning, Jasper the young fox stumbles upon the entrance to the Magic Fox Forest...", animation_style: "cartoon_2d", story_prompt: "On a bright sunny morning, Jasper the young fox stumbles upon the entrance to the Magic Fox Forest. With the help of Luna and Roo, he begins to explore the magical wonders hidden within the forest.", job_id: "0eefaead-21c0-487f-8fed-5f3326357950", hero_img: "/homepage-banners/the-discovery-hero.jpg", card_img: "/homepage-banners/the-discovery-card.jpg" },
  { slug: "conc-test-c", title: "Maya's Living Paintings", hook_text: "A young painter named Maya discovered her paintings came alive at night...", animation_style: "cartoon_2d", story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color. There she met friendly creatures made entirely of paint and watercolor.", job_id: "b70a9af2-4f43-4ed3-a251-594fecddda2d", hero_img: "/homepage-banners/conc-test-c-hero.jpg", card_img: "/homepage-banners/conc-test-c-card.jpg" },
  { slug: "conc-test-b", title: "Puff the Traveling Cloud", hook_text: "A talking cloud named Puff traveled the world raining on gardens that needed water...", animation_style: "cartoon_2d", story_prompt: "A talking cloud named Puff traveled the world raining on gardens that needed water. One day she found a desert with no plants at all. She cried so many raindrops that flowers began to bloom everywhere.", job_id: "7dc2bce1-20da-42d3-88a1-3e5589ab0b9e", hero_img: "/homepage-banners/conc-test-b-hero.jpg", card_img: "/homepage-banners/conc-test-b-card.jpg" },
  { slug: "conc-test-a", title: "The Knight and the Dragon", hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...", animation_style: "cartoon_2d", story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket. Ash offered a lantern and they became friends.", job_id: "484c5179-bf3c-4a00-895e-7d30fb63d5bb", hero_img: "/homepage-banners/conc-test-a-hero.jpg", card_img: "/homepage-banners/conc-test-a-card.jpg" },
  { slug: "concurrent-c", title: "The Rainbow Bridge", hook_text: "A young painter named Maya discovered her paintings came alive at night...", animation_style: "cartoon_2d", story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color.", job_id: "05521f33-91fd-404f-a7cd-d0683aeef597", hero_img: "/homepage-banners/concurrent-c-hero.jpg", card_img: "/homepage-banners/concurrent-c-card.jpg" },
  { slug: "concurrent-b", title: "The Desert Oasis", hook_text: "A talking cloud named Puff traveled the world, raining on gardens that needed water...", animation_style: "cartoon_2d", story_prompt: "A talking cloud named Puff traveled the world, raining on gardens that needed water. One day she found a desert with no plants at all. She cried so many raindrops that flowers began to bloom.", job_id: "4f8f9b7b-7e53-4780-8d11-e94b1b97845c", hero_img: "/homepage-banners/concurrent-b-hero.jpg", card_img: "/homepage-banners/concurrent-b-card.jpg" },
  { slug: "concurrent-a", title: "The Lantern Knight", hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...", animation_style: "cartoon_2d", story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket.", job_id: "5e071235-b445-454e-8410-56009d31b93f", hero_img: "/homepage-banners/concurrent-a-hero.jpg", card_img: "/homepage-banners/concurrent-a-card.jpg" },
  { slug: "concurrent-c-2", title: "Colors That Dance", hook_text: "A young painter named Maya discovered her paintings came alive at night...", animation_style: "cartoon_2d", story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color. There she met friendly creatures made of paint.", job_id: "5a0af22b-30ac-4035-ae6e-3bc8732a553c", hero_img: "/homepage-banners/concurrent-c-hero.jpg", card_img: "/homepage-banners/concurrent-c-card.jpg" },
  { slug: "concurrent-b-2", title: "Rain for the Garden", hook_text: "A talking cloud named Puff traveled the world, raining on gardens that needed water...", animation_style: "cartoon_2d", story_prompt: "A talking cloud named Puff traveled the world, raining on gardens that needed water. One day she found a desert with no plants at all.", job_id: "1b586dbf-cf77-473f-b821-6842dd72082e", hero_img: "/homepage-banners/concurrent-b-hero.jpg", card_img: "/homepage-banners/concurrent-b-card.jpg" },
  { slug: "concurrent-a-2", title: "Ash and the Shadow", hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...", animation_style: "cartoon_2d", story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket. Ash offered a lantern and they became friends.", job_id: "fb3e388e-ccd4-4235-964c-68b997c4cd3c", hero_img: "/homepage-banners/concurrent-a-hero.jpg", card_img: "/homepage-banners/concurrent-a-card.jpg" },
  { slug: "clean-benchmark-2", title: "Flicker the Firefly", hook_text: "A small firefly named Flicker could not glow as brightly as his friends...", animation_style: "cartoon_2d", story_prompt: "A small firefly named Flicker could not glow as brightly as his friends. He practiced every night, trying harder and harder. One evening, a lost baby owl needed help finding her way home.", job_id: "995f835d-f623-43ae-94be-62e529f9f397", hero_img: "/homepage-banners/clean-benchmark-2-hero.jpg", card_img: "/homepage-banners/clean-benchmark-2-card.jpg" },
  { slug: "clean-benchmark-1", title: "Theodore the Wise Tortoise", hook_text: "A wise old tortoise named Theodore taught the forest animals about patience...", animation_style: "cartoon_2d", story_prompt: "A wise old tortoise named Theodore taught the forest animals about patience. He showed the rabbit how to slow down and enjoy the flowers.", job_id: "cc1f19b4-0c00-4541-a819-bcb36942e938", hero_img: "/homepage-banners/clean-benchmark-1-hero.jpg", card_img: "/homepage-banners/clean-benchmark-1-card.jpg" },
  { slug: "speed-test---forest-friends", title: "Maple's Forest Friends", hook_text: "A baby bear named Maple got lost during her first autumn walk...", animation_style: "cartoon_2d", story_prompt: "A baby bear named Maple got lost during her first autumn walk. She met a squirrel gathering nuts, a deer drinking from a stream, and a family of rabbits building a new home.", job_id: "e69f852d-dd7e-4cc2-860b-3816dcf6e823", hero_img: "/homepage-banners/speed-test---forest-friends-hero.jpg", card_img: "/homepage-banners/speed-test---forest-friends-card.jpg" },
];

// Fast lookup by job_id
const BANNER_MAP = {};
STATIC_BANNERS_LIST.forEach(b => { BANNER_MAP[b.job_id] = b; });

/**
 * Get static hero image for a story (same-origin, no CDN).
 * Returns null if no static banner exists.
 */
export function getStaticHeroImg(jobId) {
  return BANNER_MAP[jobId]?.hero_img || null;
}

/**
 * Get static card image for a story (same-origin, no CDN).
 * Returns null if no static banner exists.
 */
export function getStaticCardImg(jobId) {
  return BANNER_MAP[jobId]?.card_img || null;
}

/** Get all static banners as array */
export function getAllStaticBanners() {
  return STATIC_BANNERS_LIST;
}

/** Check if a story has a static banner */
export function hasStaticBanner(jobId) {
  return !!BANNER_MAP[jobId];
}

export default STATIC_BANNERS_LIST;
