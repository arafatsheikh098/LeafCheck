// EN/Bangla string table for the LeafCheck frontend.
// Translation key → { en, bn }.
// All visible UI strings live here so the toggle is a single string lookup.

export const I18N = {
  title: {
    en: "LeafCheck",
    bn: "লিফচেক",
  },
  tagline: {
    en: "Detect leaf diseases on tomato, potato, maize and bell pepper.",
    bn: "টমেটো, আলু, ভুট্টা ও ক্যাপসিকামের রোগ শনাক্ত করুন।",
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
    en: "Diagnose",
    bn: "রোগ নির্ণয়",
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
    en: "This tool is a research preview. The model was trained on lab-style photos (PlantVillage). Real field photos — uneven light, occluded leaves, multiple diseases — will give less reliable results. Always confirm with your local agricultural extension service before applying any treatment.",
    bn: "এই টুলটি একটি গবেষণা প্রিভিউ। মডেলটি ল্যাবের ছবিতে (PlantVillage) প্রশিক্ষিত। বাস্তব মাঠের ছবি — অসম আলো, ঢাকা পাতা, একাধিক রোগ — কম নির্ভরযোগ্য ফলাফল দেবে। যেকোনো ব্যবস্থা নেওয়ার আগে স্থানীয় কৃষি সম্প্রসারণ কর্মকর্তার সাথে নিশ্চিত হন।",
  },
  error: {
    en: "Something went wrong",
    bn: "কিছু ভুল হয়েছে",
  },
  langToggle: {
    en: "EN",
    bn: "বাং",
  },
};

export function t(key, lang) {
  const entry = I18N[key];
  if (!entry) return key;
  return entry[lang] || entry.en;
}