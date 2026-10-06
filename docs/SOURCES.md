# مصادر محتوى رحلة العمرة (للمراجعة الشرعية)

Every line in `src/game/content.js` carries a `src` key (`S-…`). This file lists what each key
relies on, so the sheikh can review the prototype line by line before anything is released.

- **⚠️ خلاف** marks a point where the madhhabs differ. The game states the majority view and,
  where it matters, mentions the other one.
- **🔎 تحقق** marks a reference number or wording I could not confirm with full certainty. It
  must be checked against the printed source.

Nothing here has been reviewed yet.

## قبل الطواف (الفصول ١–٤)

| key | المحتوى في اللعبة | المصدر | ملاحظات |
|---|---|---|---|
| S-ihram-clothes | Men wear an izar and a rida (white is better) and sandals; no stitched clothing, no socks, no shoes covering the ankles | «لا يلبس القُمُص ولا العمائم ولا السراويلات ولا البرانس ولا الخفاف، إلا أحد لا يجد نعلين…» (البخاري ١٥٤٢، مسلم ١١٧٧). «وليُحرم أحدكم في إزار ورداء ونعلين» (أحمد ٤٨٩٩) | 🔎 تحقق: the Ahmad number. ⚠️ خلاف: on a shoe that stays below the ankles. The game says "ankles" only. |
| S-perfume | Perfume on the body before ihram is a sunnah; after the niyyah it is forbidden; not on the ihram clothes | Aisha: «كنتُ أُطيِّب رسول الله ﷺ لإحرامه قبل أن يُحرم» (البخاري ١٥٣٩، مسلم ١١٨٩). «ولا تلبسوا من الثياب شيئًا مسّه الزعفران ولا الورس» (البخاري ١٥٤٢) | ⚠️ خلاف: on perfuming the ihram clothes before ihram. The majority dislike it or forbid wearing them; the Shafi'is allow it. The game says the body only. The "trap" in the game: packing perfume to use while in ihram. |
| S-ghusl | Ghusl for ihram is a sunnah | Zayd ibn Thabit: «رأى النبي ﷺ تجرّد لإهلاله واغتسل» (الترمذي ٨٣٠) | Al-Tirmidhi: hasan gharib. 🔎 تحقق. |
| S-leave-home | «بسم الله، توكلت على الله، ولا حول ولا قوة إلا بالله» | (أبو داود ٥٠٩٥، الترمذي ٣٤٢٦) | Al-Tirmidhi: hasan sahih gharib. |
| S-travel-dua | The travel du'a when boarding | Ibn Umar (مسلم ١٣٤٢) | The game shows the opening part only, up to «…ومن العمل ما ترضى». |
| S-miqat | The miqat; whoever passes it intending Umrah must be in ihram; a plane enters ihram when level with the miqat; wearing the clothes before it is allowed | The hadith of the mawaqit (البخاري ١٥٢٤، مسلم ١١٨١). Umar set Dhat Irq level with Qarn (البخاري ١٥٣١) | ⚠️ خلاف: passing the miqat without ihram. The majority say go back to it, otherwise a dam is due; this is in the Q&A. **Simplification:** the countdown (20 minutes → 100 seconds of play) waits at one minute if the player is not ready, so the game never passes the miqat without ihram. |
| S-niyyah | The intention in the heart, and saying «لبيك اللهم عمرة» | Anas: «لبيك عمرةً وحجًّا» (مسلم ١٢٥١) for qiran. For Umrah alone, scholars use the wording «لبيك عمرة» / «لبيك اللهم عمرة» | 🔎 تحقق: which wording to rely on. Wearing the clothes alone does not make a person muhrim; the game says this explicitly. Ishtirat is not in the game yet. |
| S-talbiyah | The full talbiyah; men raise their voices; it continues until tawaf | The talbiyah of the Prophet ﷺ (البخاري ١٥٤٩، مسلم ١١٨٤). Raising the voice: al-Sa'ib ibn Khallad (أبو داود ١٨١٤، الترمذي ٨٢٩) | When it stops: see S-talbiya-stop. |
| S-prohibitions | Perfume, cutting hair and nails, covering the head (men), stitched clothing (men), hunting, contracting a marriage | (البخاري ١٥٤٢). Hair: البقرة ١٩٦. Hunting: المائدة ٩٥. Marriage: «لا يَنكح المحرم ولا يُنكح» (مسلم ١٤٠٩) | Nails: by consensus, by analogy with hair (Ibn al-Mundhir). |
| S-women-ihram | A woman wears her ordinary covering clothes, without niqab or gloves | «ولا تنتقب المرأة المحرمة ولا تلبس القفازين» (البخاري ١٨٣٨) | ⚠️ خلاف: many scholars allow covering the face in front of non-mahram men by lowering the cloth. |
| S-masjid-enter | The right foot first; «بسم الله، والصلاة والسلام على رسول الله، اللهم افتح لي أبواب رحمتك» | «اللهم افتح لي أبواب رحمتك» (مسلم ٧١٣). Blessings on the Prophet: (ابن ماجه ٧٧١، أبو داود ٤٦٥). The right foot: Anas (الحاكم), and the general hadith on starting with the right (البخاري ١٦٨) | 🔎 تحقق: the gradings. |
| S-kaaba-sight | No fixed du'a on seeing the Kaaba; make du'a from the heart (also the line at the start of tawaf) | Raising the hands and a specific du'a on first seeing the Kaaba are reported only in weak or mursal narrations | The game attributes no wording. |
| S-tahiyya | Someone entering for Umrah begins with tawaf | Aisha: the first thing he did was wudu, then tawaf (البخاري ١٦١٤) | Scholars say tawaf takes the place of the greeting prayer of the mosque. |

## الطواف

| key | المحتوى في اللعبة | المصدر | ملاحظات |
|---|---|---|---|
| S-tahara | الطهارة للطواف، والنية في القلب | Aisha: the first thing the Prophet ﷺ did on arriving was wudu, then tawaf (البخاري ١٦١٤، مسلم ١٢٣٥). «افعلي ما يفعل الحاج غير ألا تطوفي بالبيت حتى تطهري» (البخاري ٣٠٥، مسلم ١٢١١) | ⚠️ خلاف: the majority hold purity to be a **condition** of tawaf. The Hanafis hold it **obligatory (wajib)** but not a condition. The Q&A answer mentions both. |
| S-talbiya-stop | Stopping the talbiyah when tawaf begins | Ibn Abbas: «يُلبّي المعتمر حتى يستلم الحجر» (أبو داود ١٨١٧، الترمذي ٩١٩) | ⚠️ خلاف: the majority say at the start of tawaf. A Maliki view says on entering the Haram (or on seeing the houses of Makkah). 🔎 تحقق: whether the narration is marfu' or mawquf. |
| S-idtiba | Idtiba': right shoulder bare, men only, this tawaf only, covered afterwards | Ya'la ibn Umayya: «طاف النبي ﷺ مضطبعًا» (أبو داود ١٨٨٣، الترمذي ٨٥٩). Ibn Abbas on how it is done (أبو داود ١٨٨٤) | ⚠️ خلاف: the Malikis do not count idtiba' as a sunnah. It applies only to the tawaf that comes right after ihram (tawaf al-qudum, or the tawaf of Umrah), and the shoulder is covered for the two rak'ahs. |
| S-istilam | Facing the Black Stone, pointing with the right hand, «بسم الله والله أكبر». Kissing it only without harming anyone | Pointing and takbir: Ibn Abbas, «كلما أتى الركن أشار إليه بشيء كان عنده وكبّر» (البخاري ١٦١٣). «بسم الله والله أكبر»: from Ibn Umar (البيهقي، السنن الكبرى ٥/٧٩). Kissing: Umar (البخاري ١٥٩٧، مسلم ١٢٧٠). Not crowding: Umar's narration (مسند أحمد ١٩٠) | 🔎 تحقق: the grading of the Bayhaqi narration and the number in Ahmad. The game uses «بسم الله والله أكبر» on the first circuit and «الله أكبر» on the rest. |
| S-direction | The Kaaba on the left; starting from the Black Stone | Jabir: «لما قدم النبي ﷺ مكة أتى الحجر فاستلمه، ثم مشى على يمينه، فرمل ثلاثًا ومشى أربعًا» (مسلم ١٢١٨، النسائي ٢٩٣٩) | 🔎 تحقق: the exact wording and number in Muslim. |
| S-raml | Raml: brisk walking with short steps in the first 3 circuits, men only, without harming anyone | Ibn Umar: «رمل ثلاثة أطواف ومشى أربعة» (البخاري ١٦٠٣، مسلم ١٢٦٢). In the Farewell Hajj he did raml from the Black Stone round to the Black Stone (مسلم ١٢٦٣) | Ibn al-Mundhir reports consensus that women do not do raml. In the game raml is a bonus (Shift / 🏃) and is never forced. |
| S-hijr | Hijr Ismail is part of the Kaaba, so tawaf goes outside it | Aisha's question about the wall (al-jadr) (البخاري ١٥٨٤، مسلم ١٣٣٣) | ⚠️ خلاف: on a circuit walked inside the Hijr. The majority say that circuit does not count. The Hanafis say it must be repeated (otherwise a penalty). The game blocks walking inside it. |
| S-yamani | Touching ar-Rukn al-Yamani if possible, without kissing or pointing | Ibn Umar: «لم أرَ النبي ﷺ يستلم من البيت إلا الركنين اليمانيين» (البخاري ١٦٠٩، مسلم ١٢٦٧) | Pointing to it when it cannot be touched: nothing is reported, and this is the view of many scholars. 🔎 تحقق. |
| S-rabbana | «ربنا آتنا في الدنيا حسنة…» between the Yamani corner and the Black Stone | Abdullah ibn as-Sa'ib (أبو داود ١٨٩٢، أحمد)، والآية في البقرة ٢٠١ | Graded hasan by al-Albani. 🔎 تحقق. |
| S-free-dua | No fixed du'a for each circuit | Ibn Taymiyyah (مجموع الفتاوى ٢٦/١٢٢) and others | A statement of scholars, not a single hadith. |
| S-doubt | Doubt about the number of circuits: build on what you are sure of (the lower number) | By analogy with doubt in prayer (مسلم ٥٧١) | The majority view. |
| S-maqam | Two rak'ahs behind the Maqam, with al-Kafirun and al-Ikhlas; anywhere in the mosque if it is crowded | البقرة ١٢٥. Jabir: he recited the verse, prayed, and read «قل يا أيها الكافرون» and «قل هو الله أحد» (مسلم ١٢١٨) | Praying elsewhere when it is crowded: Umar prayed them at Dhu Tuwa (البخاري، تعليقًا). |
| S-kaaba-sight (tawaf) | «خد نفسك… وادعي باللي في قلبك» at the start of tawaf | See above | |
| S-zamzam | «لو تيسّر اشرب من زمزم» | Jabir, in Ahmad's version: «ثم ذهب إلى زمزم فشرب منها…» | 🔎 تحقق: the number and grading. Shown as optional. **Not in the game yet:** going back to touch the Black Stone after the two rak'ahs, before Sa'i (مسلم ١٢١٨). |

## السعي

| key | المحتوى في اللعبة | المصدر | ملاحظات |
|---|---|---|---|
| S-sai-count | 7 laps: Safa → Marwa is one lap and the return another, ending on Marwa | Jabir: «حتى إذا كان آخر طوافه على المروة» (مسلم ١٢١٨) | The view of the four madhhabs. |
| S-hajar | The origin of Sa'i in the story of Hajar | Ibn Abbas: «فذلك سعي الناس بينهما» (البخاري ٣٣٦٤) | The story is told briefly. Hajar is not shown on screen. |
| S-safa-first | Starting from Safa: «أبدأ بما بدأ الله به» | مسلم ١٢١٨. الآية: البقرة ١٥٨ | Al-Nasa'i (٢٩٦٢) has the imperative «ابدؤوا». The verse is recited only on approaching Safa at the start of the first lap. |
| S-safa-dhikr | Climbing Safa, facing the Kaaba, declaring Allah's oneness and greatness; the dhikr 3 times with du'a in between | Jabir: «فرقي عليه حتى رأى البيت، فاستقبل القبلة، فوحّد الله وكبّره، وقال: لا إله إلا الله وحده لا شريك له…» three times with du'a between (مسلم ١٢١٨) | 🔎 تحقق: the panel opens with «الله أكبر» three times. Jabir's wording is «وحّد الله وكبّره», and the threefold takbir comes from other narrations. |
| S-marwa | At Marwa as at Safa | «ففعل على المروة كما فعل على الصفا» (مسلم ١٢١٨) | Optional in the game. The verse is not repeated. |
| S-green | Men jog between the two green markers, women do not | «حتى إذا انصبّت قدماه في بطن الوادي سعى» (مسلم ١٢١٨). Ibn al-Mundhir reports consensus that women do not jog | The green lights mark the valley bed today. |
| S-green-dua | «ربِّ اغفر وارحم، إنك أنت الأعزّ الأكرم» | Mawquf: from Ibn Mas'ud and Ibn Umar (ابن أبي شيبة) | Labelled in the game «وارد عن بعض الصحابة». It is not attributed to the Prophet ﷺ. 🔎 تحقق: the grading. |
| S-sai-tahara | Wudu is not a condition for Sa'i, but it is better | The majority. The narration «غير ألا تطوفي بالبيت» did not exclude Sa'i | ⚠️ خلاف: al-Hasan al-Basri held it to be required. |
| S-halq | After Sa'i: shaving or shortening; shaving is better for men | «اللهم ارحم المحلّقين» (البخاري ١٧٢٧، مسلم ١٣٠١) | Chapter 8 (not built yet). |

## Simplifications in the prototype (not religious rulings)

- **Distance of the Mas'a:** shortened to 120 m. The real distance is about 395 m.
- **Kaaba:** a square of 11.6 m. The real Kaaba is slightly rectangular.
- **Hijr Ismail and Maqam Ibrahim:** placed approximately.
- **Start line:** the golden line on the floor is a game marker only. The old brown line was removed years ago. The green lamp on the colonnade facing the Black Stone is kept.
- **Green-lit stretch:** its position is approximate, at about a third of the way.
- **Crowds:** in tawaf most men show idtiba'. In Sa'i, none of them do.
