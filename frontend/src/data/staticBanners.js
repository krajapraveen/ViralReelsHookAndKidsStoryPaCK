/**
 * WEBPACK-BUNDLED Homepage Banner Assets
 * Images are imported directly — webpack hashes and bundles them into the build.
 * ZERO network dependency. ZERO CDN. ZERO proxy. ZERO CORS.
 * These are part of the JS bundle itself.
 */

// ── Hero images (800px wide, ~30KB each) ────────────────────────────
import painterHero from '../assets/homepage/the-painter-of-stars-hero.jpg';
import crystalHero from '../assets/homepage/the-crystal-cave-hero.jpg';
import catHero from '../assets/homepage/a-cats-big-city-adventure-hero.jpg';
import cloverHero from '../assets/homepage/clover-and-the-golden-key-hero.jpg';
import discoveryHero from '../assets/homepage/the-discovery-hero.jpg';
import concCHero from '../assets/homepage/conc-test-c-hero.jpg';
import concBHero from '../assets/homepage/conc-test-b-hero.jpg';
import concAHero from '../assets/homepage/conc-test-a-hero.jpg';
import currCHero from '../assets/homepage/concurrent-c-hero.jpg';
import currBHero from '../assets/homepage/concurrent-b-hero.jpg';
import currAHero from '../assets/homepage/concurrent-a-hero.jpg';
import bench2Hero from '../assets/homepage/clean-benchmark-2-hero.jpg';
import bench1Hero from '../assets/homepage/clean-benchmark-1-hero.jpg';
import forestHero from '../assets/homepage/speed-test---forest-friends-hero.jpg';

// ── Card images (400px wide, ~15KB each) ────────────────────────────
import painterCard from '../assets/homepage/the-painter-of-stars-card.jpg';
import crystalCard from '../assets/homepage/the-crystal-cave-card.jpg';
import catCard from '../assets/homepage/a-cats-big-city-adventure-card.jpg';
import cloverCard from '../assets/homepage/clover-and-the-golden-key-card.jpg';
import discoveryCard from '../assets/homepage/the-discovery-card.jpg';
import concCCard from '../assets/homepage/conc-test-c-card.jpg';
import concBCard from '../assets/homepage/conc-test-b-card.jpg';
import concACard from '../assets/homepage/conc-test-a-card.jpg';
import currCCard from '../assets/homepage/concurrent-c-card.jpg';
import currBCard from '../assets/homepage/concurrent-b-card.jpg';
import currACard from '../assets/homepage/concurrent-a-card.jpg';
import bench2Card from '../assets/homepage/clean-benchmark-2-card.jpg';
import bench1Card from '../assets/homepage/clean-benchmark-1-card.jpg';
import forestCard from '../assets/homepage/speed-test---forest-friends-card.jpg';

const STATIC_BANNERS_LIST = [
  {
    title: "The Painter of Stars",
    hook_text: "Every night, an old woman climbed the tallest hill with a bucket of stardust...",
    animation_style: "watercolor",
    story_prompt: "Every night, an old woman climbed the tallest hill with a bucket of stardust. She dipped her brush in the glowing dust and painted new stars across the sky. One evening a child followed her and asked why. She smiled and said: because the sky forgets its own beauty, someone must remind it.",
    job_id: "261430a2-28f5-4c40-bac2-35f8d275fae7",
    hero_img: painterHero,
    card_img: painterCard,
  },
  {
    title: "The Crystal Cave",
    hook_text: "Deep beneath the mountains, a young fox named Sage discovers a hidden cave filled with glowing crystals...",
    animation_style: "cartoon_2d",
    story_prompt: "Deep beneath the mountains, a young fox named Sage discovers a hidden cave filled with glowing crystals. Each crystal holds a memory from a different time. When Sage touches one, she is transported to a magical forest where trees whisper secrets.",
    job_id: "b95498d4-2e2a-4472-8dac-f8a253d07dfd",
    hero_img: crystalHero,
    card_img: crystalCard,
  },
  {
    title: "A Cat's Big City Adventure",
    hook_text: "A short test story about a cat who goes on an adventure in the city and meets new friends along the way...",
    animation_style: "watercolor",
    story_prompt: "A short test story about a cat who goes on an adventure in the city and meets new friends along the way.",
    job_id: "da85bb12-785b-4906-8fba-48de780f4a2e",
    hero_img: catHero,
    card_img: catCard,
  },
  {
    title: "Clover and the Golden Key",
    hook_text: "A brave little rabbit named Clover explored the enchanted meadow...",
    animation_style: "watercolor",
    story_prompt: "A brave little rabbit named Clover explored the enchanted meadow. She discovered a golden key under an old oak tree. The key opened a secret door to a world of talking flowers and singing birds.",
    job_id: "13ddd5d5-307c-4c45-8ac6-e349344d8abf",
    hero_img: cloverHero,
    card_img: cloverCard,
  },
  {
    title: "The Discovery",
    hook_text: "On a bright sunny morning, Jasper the young fox stumbles upon the entrance to the Magic Fox Forest...",
    animation_style: "cartoon_2d",
    story_prompt: "On a bright sunny morning, Jasper the young fox stumbles upon the entrance to the Magic Fox Forest. With the help of Luna and Roo, he begins to explore the magical wonders hidden within the forest.",
    job_id: "0eefaead-21c0-487f-8fed-5f3326357950",
    hero_img: discoveryHero,
    card_img: discoveryCard,
  },
  {
    title: "Maya's Living Paintings",
    hook_text: "A young painter named Maya discovered her paintings came alive at night...",
    animation_style: "cartoon_2d",
    story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color. There she met friendly creatures made entirely of paint and watercolor.",
    job_id: "b70a9af2-4f43-4ed3-a251-594fecddda2d",
    hero_img: concCHero,
    card_img: concCCard,
  },
  {
    title: "Puff the Traveling Cloud",
    hook_text: "A talking cloud named Puff traveled the world raining on gardens that needed water...",
    animation_style: "cartoon_2d",
    story_prompt: "A talking cloud named Puff traveled the world raining on gardens that needed water. One day she found a desert with no plants at all. She cried so many raindrops that flowers began to bloom everywhere.",
    job_id: "7dc2bce1-20da-42d3-88a1-3e5589ab0b9e",
    hero_img: concBHero,
    card_img: concBCard,
  },
  {
    title: "The Knight and the Dragon",
    hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...",
    animation_style: "cartoon_2d",
    story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket. Ash offered a lantern and they became friends.",
    job_id: "484c5179-bf3c-4a00-895e-7d30fb63d5bb",
    hero_img: concAHero,
    card_img: concACard,
  },
  {
    title: "The Rainbow Bridge",
    hook_text: "A young painter named Maya discovered her paintings came alive at night...",
    animation_style: "cartoon_2d",
    story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color.",
    job_id: "05521f33-91fd-404f-a7cd-d0683aeef597",
    hero_img: currCHero,
    card_img: currCCard,
  },
  {
    title: "The Desert Oasis",
    hook_text: "A talking cloud named Puff traveled the world, raining on gardens that needed water...",
    animation_style: "cartoon_2d",
    story_prompt: "A talking cloud named Puff traveled the world, raining on gardens that needed water. One day she found a desert with no plants at all. She cried so many raindrops that flowers began to bloom.",
    job_id: "4f8f9b7b-7e53-4780-8d11-e94b1b97845c",
    hero_img: currBHero,
    card_img: currBCard,
  },
  {
    title: "The Lantern Knight",
    hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...",
    animation_style: "cartoon_2d",
    story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket.",
    job_id: "5e071235-b445-454e-8410-56009d31b93f",
    hero_img: currAHero,
    card_img: currACard,
  },
  {
    title: "Colors That Dance",
    hook_text: "A young painter named Maya discovered her paintings came alive at night...",
    animation_style: "cartoon_2d",
    story_prompt: "A young painter named Maya discovered her paintings came alive at night. She painted a rainbow bridge and walked across it to a land of color. There she met friendly creatures made of paint.",
    job_id: "5a0af22b-30ac-4035-ae6e-3bc8732a553c",
    hero_img: currCHero,
    card_img: currCCard,
  },
  {
    title: "Rain for the Garden",
    hook_text: "A talking cloud named Puff traveled the world, raining on gardens that needed water...",
    animation_style: "cartoon_2d",
    story_prompt: "A talking cloud named Puff traveled the world, raining on gardens that needed water. One day she found a desert with no plants at all.",
    job_id: "1b586dbf-cf77-473f-b821-6842dd72082e",
    hero_img: currBHero,
    card_img: currBCard,
  },
  {
    title: "Ash and the Shadow",
    hook_text: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark...",
    animation_style: "cartoon_2d",
    story_prompt: "A brave knight named Ash set out to find a dragon who was secretly afraid of the dark. When Ash arrived at the cave, the dragon was hiding under a blanket. Ash offered a lantern and they became friends.",
    job_id: "fb3e388e-ccd4-4235-964c-68b997c4cd3c",
    hero_img: currAHero,
    card_img: currACard,
  },
  {
    title: "Flicker the Firefly",
    hook_text: "A small firefly named Flicker could not glow as brightly as his friends...",
    animation_style: "cartoon_2d",
    story_prompt: "A small firefly named Flicker could not glow as brightly as his friends. He practiced every night, trying harder and harder. One evening, a lost baby owl needed help finding her way home.",
    job_id: "995f835d-f623-43ae-94be-62e529f9f397",
    hero_img: bench2Hero,
    card_img: bench2Card,
  },
  {
    title: "Theodore the Wise Tortoise",
    hook_text: "A wise old tortoise named Theodore taught the forest animals about patience...",
    animation_style: "cartoon_2d",
    story_prompt: "A wise old tortoise named Theodore taught the forest animals about patience. He showed the rabbit how to slow down and enjoy the flowers.",
    job_id: "cc1f19b4-0c00-4541-a819-bcb36942e938",
    hero_img: bench1Hero,
    card_img: bench1Card,
  },
  {
    title: "Maple's Forest Friends",
    hook_text: "A baby bear named Maple got lost during her first autumn walk...",
    animation_style: "cartoon_2d",
    story_prompt: "A baby bear named Maple got lost during her first autumn walk. She met a squirrel gathering nuts, a deer drinking from a stream, and a family of rabbits building a new home.",
    job_id: "e69f852d-dd7e-4cc2-860b-3816dcf6e823",
    hero_img: forestHero,
    card_img: forestCard,
  },
];

// Fast lookup by job_id
const BANNER_MAP = {};
STATIC_BANNERS_LIST.forEach(b => { BANNER_MAP[b.job_id] = b; });

/**
 * Get bundled hero image for a story.
 * Returns webpack-hashed URL (e.g., /static/media/the-painter-of-stars-hero.abc123.jpg)
 */
export function getStaticHeroImg(jobId) {
  return BANNER_MAP[jobId]?.hero_img || null;
}

/**
 * Get bundled card image for a story.
 * Returns webpack-hashed URL (e.g., /static/media/the-painter-of-stars-card.def456.jpg)
 */
export function getStaticCardImg(jobId) {
  return BANNER_MAP[jobId]?.card_img || null;
}

/** Get all static banners */
export function getAllStaticBanners() {
  return STATIC_BANNERS_LIST;
}

/** Check if a story has a bundled banner */
export function hasStaticBanner(jobId) {
  return !!BANNER_MAP[jobId];
}

export default STATIC_BANNERS_LIST;
