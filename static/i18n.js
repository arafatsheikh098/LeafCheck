// EN/Bangla string table for the LeafCheck frontend.
// Translation key → { en, bn }.
// All visible UI strings live here so the toggle is a single string lookup.

export const I18N = {
  title: {
    en: "LeafCheck",
    bn: "লিফচেক",
  },
  tagline: {
    en: "Identify 9 plant species from a single leaf photo.",
    bn: "একটি পাতার ছবি থেকে ৯টি উদ্ভিদ প্রজাতি শনাক্ত করুন।",
  },
  pickOrDrop: {
    en: "Pick a photo or drop one here",
    bn: "একটি ছবি বেছে নিন বা এখানে ফেলুন",
  },
  pickButton: {
    en: "Choose photo",
    bn: "ছবি বাছুন",
  },
  useCamera: {
    en: "Use camera",
    bn: "ক্যামেরা ব্যবহার",
  },
  predict: {
    en: "Identify",
    bn: "শনাক্ত করুন",
  },
  predicting: {
    en: "Looking at the leaf…",
    bn: "পাতাটি দেখা হচ্ছে…",
  },
  notSure: {
    en: "I'm not confident enough to call this. Try retaking the photo:",
    bn: "আমি এটি নিশ্চিতভাবে বলতে পারছি না। আবার ছবি তুলুন:",
  },
  retakeTips: {
    en: [
      "Use a single leaf, well-lit and in focus.",
      "Plain background, no other plants overlapping.",
      "Hold the phone steady, fill the frame with the leaf.",
    ],
    bn: [
      "ভালো আলোতে ফোকাসে একটি পাতার ছবি তুলুন।",
      "সাধারণ ব্যাকগ্রাউন্ড, অন্য গাছ যেন ঢাকা না দেয়।",
      "ফোন স্থির রাখুন, পাতাটি ফ্রেমে পূর্ণ করুন।",
    ],
  },
  topClass: {
    en: "Top guess",
    bn: "সবচেয়ে সম্ভাব্য",
  },
  otherGuesses: {
    en: "Other guesses",
    bn: "অন্যান্য সম্ভাবনা",
  },
  advice: {
    en: "What to do",
    bn: "কী করবেন",
  },
  disclaimer: {
    en: "This tool is a research preview. The shipped model was trained on the BdLeaf20 leaf-image dataset (9 tropical plant species, ~40–55 photos per class, single-leaf close-ups on plain backgrounds). Real field photos — uneven light, occluded leaves, multiple plants in frame — will give less reliable results. The model identifies plant species; it does not diagnose plant diseases. Always confirm with a botanist or local extension service before relying on the result for any decision.",
    bn: "এই টুলটি একটি গবেষণা প্রিভিউ। শিপড মডেলটি BdLeaf20 পাতার-ছবি ডেটাসেটে প্রশিক্ষিত (৯টি গ্রীষ্মমণ্ডলীয় উদ্ভিদ প্রজাতি, প্রতি শ্রেণিতে প্রায় ৪০–৫৫টি ছবি, সাধারণ ব্যাকগ্রাউন্ডে একটি পাতার ক্লোজ-আপ)। বাস্তব মাঠের ছবি — অসম আলো, ঢাকা পাতা, এক ফ্রেমে একাধিক গাছ — কম নির্ভরযোগ্য ফলাফল দেবে। মডেলটি উদ্ভিদ প্রজাতি শনাক্ত করে, রোগ নির্ণয় করে না। যেকোনো সিদ্ধান্তের আগে একজন উদ্ভিদবিদ বা স্থানীয় কৃষি সম্প্রসারণ কর্মকর্তার সাথে নিশ্চিত হন।",
  },
  error: {
    en: "Something went wrong",
    bn: "কিছু ভুল হয়েছে",
  },
  langToggle: {
    en: "EN",
    bn: "বাং",
  },
  knownSpeciesHeading: {
    en: "Species the model can identify",
    bn: "মডেল যে প্রজাতিগুলো শনাক্ত করতে পারে",
  },
  knownSpeciesIntro: {
    en: "The model is trained on BdLeaf20 — close-up photos of single leaves on plain backgrounds. Best results on similar photos.",
    bn: "মডেলটি BdLeaf20 ডেটাসেটে প্রশিক্ষিত — সাধারণ ব্যাকগ্রাউন্ডে একটি পাতার ক্লোজ-আপ ছবি। এই ধরনের ছবিতে সবচেয়ে ভালো ফল পাওয়া যায়।",
  },
  moreSpeciesHeading: {
    en: "Want more species?",
    bn: "আরও প্রজাতি চান?",
  },
  moreSpeciesBody: {
    en: "The same pipeline can be retrained on any leaf-image dataset. The plan and the commands are in the project README under Roadmap: more species.",
    bn: "একই পাইপলাইন যেকোনো পাতার-ছবি ডেটাসেটে পুনরায় প্রশিক্ষণযোগ্য। পরিকল্পনা ও কমান্ডগুলো প্রজেক্টের README-তে 'Roadmap: more species' শিরোনামে আছে।",
  },
  moreSpeciesSteps: {
    en: [
      "Collect (or download) ~50+ photos per new species.",
      "Drop them into a folder, one subdirectory per species.",
      "Run <code>python -m leafcheck.data prepare --source &lt;folder&gt; --out data/</code> then <code>python -m leafcheck.train --config configs/bdleaf20.yaml</code> — that is it, the same pipeline.",
    ],
    bn: [
      "প্রতিটি নতুন প্রজাতির জন্য প্রায় ৫০+ ছবি সংগ্রহ (বা ডাউনলোড) করুন।",
      "একটি ফোল্ডারে রাখুন, প্রতিটি প্রজাতির জন্য আলাদা সাবডিরেক্টরি।",
      "<code>python -m leafcheck.data prepare --source &lt;folder&gt; --out data/</code> তারপর <code>python -m leafcheck.train --config configs/bdleaf20.yaml</code> চালান — ব্যস, এটিই পাইপলাইন।",
    ],
  },
};

export function t(key, lang) {
  const entry = I18N[key];
  if (!entry) return key;
  return entry[lang] || entry.en;
}