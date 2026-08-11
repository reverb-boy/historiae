/* ============================================================================
   The World of Herodotus — dataset
   Places, peoples, and narrative routes drawn from the nine books of the
   Historiae. Coordinates are real (modern), so the ancient world sits on a
   true basemap. Blurbs paraphrase Herodotus; citations are book.chapter,
   e.g. (7.35) = Book VII, chapter 35.
   ========================================================================== */

const HERODOTUS = {

  /* --- BOOK METADATA ------------------------------------------------------ */
  books: [
    { n: 1, name: "Clio",        theme: "Croesus, Cyrus & the rise of Persia" },
    { n: 2, name: "Euterpe",     theme: "Egypt — land, river, gods & customs" },
    { n: 3, name: "Thalia",      theme: "Cambyses, the Magi & Darius' rise" },
    { n: 4, name: "Melpomene",   theme: "Scythia, Libya & the ends of the earth" },
    { n: 5, name: "Terpsichore", theme: "Thrace & the Ionian Revolt begins" },
    { n: 6, name: "Erato",       theme: "The revolt crushed; Marathon" },
    { n: 7, name: "Polymnia",    theme: "Xerxes' host, the Hellespont, Thermopylae" },
    { n: 8, name: "Urania",      theme: "Artemisium & the sea-fight at Salamis" },
    { n: 9, name: "Calliope",    theme: "Plataea & Mycale — the war won" },
  ],

  /* --- PLACES ------------------------------------------------------------- */
  /* places[] is GENERATED into src/data_places.js by build_data.py (415 places
     from the Perseus TEI + ToposText). Hand-authored blurbs live in
     data/places_curated.json and are merged in there. */

  /* --- PEOPLES / ETHNOGRAPHY ---------------------------------------------- */
  peoples: [
    { id:"p-scythians", name:"Scythians", lat:49.0, lng:34.0, books:[4],
      blurb:"The nomads of the northern steppe: no cities, no forts, their homes on wagons, their food the milk of mares. Because they carry all they have with them, no invader can catch or corner them.",
      quote:{text:"They have contrived that none who attacks them can escape, and none can catch them unless they choose — a people without towns, carrying their houses with them.", cite:"4.46"} },
    { id:"p-massagetae", name:"Massagetae", lat:44.0, lng:58.5, books:[1],
      blurb:"A fierce people east of the Caspian, ruled by Queen Tomyris. They drink no wine, worship only the sun, and to them Cyrus the Great lost both his last battle and his head.",
      quote:{text:"Tomyris filled a skin with blood and plunged Cyrus' head into it: 'You thirsted for blood; now drink your fill.'", cite:"1.214"} },
    { id:"p-persians", name:"Persians", lat:30.0, lng:53.0, books:[1,3],
      blurb:"The ruling people of the empire, quick to adopt foreign customs. They teach their sons three things only, and hold no disgrace worse than the lie.",
      quote:{text:"They train their boys from five to twenty in three things alone: to ride, to draw the bow, and to speak the truth.", cite:"1.136"} },
    { id:"p-medes", name:"Medes", lat:35.5, lng:49.0, books:[1],
      blurb:"The people who first threw off Assyria and built an empire, until Cyrus turned the tables and made master into subject. Their dress and cavalry the Persians took for their own.",
      quote:{text:"The Medes were the first to revolt from the Assyrians and win their freedom, and their example fired the other nations.", cite:"1.95"} },
    { id:"p-lydians", name:"Lydians", lat:38.6, lng:28.2, books:[1],
      blurb:"The people of Croesus, much like the Greeks in their ways — and, Herodotus says, the first men ever to strike coined money and to keep retail shops.",
      quote:{text:"The Lydians were the first men we know to coin gold and silver money, and the first to become retail traders.", cite:"1.94"} },
    { id:"p-egyptians", name:"Egyptians", lat:26.5, lng:31.5, books:[2],
      blurb:"The most god-fearing and, they claim, the oldest of peoples — who in their manners and customs seem to have reversed the common practice of mankind.",
      quote:{text:"Just as their climate and river are unlike all others, so in most of their manners and customs the Egyptians have reversed the common practice of the world.", cite:"2.35"} },
    { id:"p-ethiopians", name:"Ethiopians", lat:18.0, lng:32.5, books:[3],
      blurb:"The 'long-lived' people at the southern edge of the world, said to be the tallest and handsomest of men. Cambyses' army marched against them and starved before it ever arrived.",
      quote:{text:"The Ethiopians are said to be the tallest and most beautiful of all men, and to live to a hundred and twenty years and more.", cite:"3.23"} },
    { id:"p-libyans", name:"Libyans", lat:30.5, lng:17.0, books:[4],
      blurb:"The many tribes strung along the North African coast and inland — some nomads following their herds, whom Herodotus catalogues nation by nation from Egypt to the Atlas.",
      quote:{text:"The nomad Libyans bury their dead as the Greeks do, and hold the land the healthiest in the world for its lack of change in the seasons.", cite:"4.187"} },
    { id:"p-thracians", name:"Thracians", lat:42.0, lng:25.5, books:[5],
      blurb:"The most numerous nation on earth after the Indians, Herodotus says — and the most formidable, were they not hopelessly divided. Ungoverned, they can never be strong.",
      quote:{text:"If the Thracians were ruled by one man, or of one mind, they would be invincible and by far the mightiest of nations.", cite:"5.3"} },
    { id:"p-getae", name:"Getae", lat:44.0, lng:27.0, books:[4],
      blurb:"The bravest and most just of the Thracians, who believe they do not die but go to the god Zalmoxis. Every four years they send him a messenger — hurled onto the points of spears.",
      quote:{text:"They call themselves 'immortalizing,' holding that the dead do not perish but go to the god Zalmoxis.", cite:"4.94"} },
    { id:"p-indians", name:"Indians", lat:28.0, lng:72.0, books:[3],
      blurb:"The most populous nation known, made of many tribes with strange and opposite ways — some eating no living thing, others eating their own aged kin. From India comes gold dug up by monstrous ants.",
      quote:{text:"In the Indian desert live ants smaller than dogs but bigger than foxes, which throw up sand full of gold as they burrow.", cite:"3.102"} },
    { id:"p-arabians", name:"Arabians", lat:23.0, lng:45.0, books:[3],
      blurb:"The only land that yields frankincense, myrrh, cassia and cinnamon — spices, Herodotus reports, guarded by winged serpents and gathered only by strange and perilous shifts.",
      quote:{text:"Winged serpents guard the frankincense trees, and are driven off only by the smoke of burning storax.", cite:"3.107"} },
    { id:"p-phoenicians", name:"Phoenicians", lat:34.0, lng:35.4, books:[1,2,5],
      blurb:"The great seafarers and traders of the Levant, who Herodotus says came originally from the Red Sea. From them the Greeks received their letters — the 'Phoenician characters.'",
      quote:{text:"The Phoenicians who came with Cadmus brought many arts into Greece, and above all letters, which the Greeks had not had before.", cite:"5.58"} },
    { id:"p-babylonians", name:"Babylonians / Assyrians", lat:33.0, lng:44.5, books:[1],
      blurb:"The people of the great river-plain, whom Herodotus describes with equal wonder and disapproval — praising their wisest custom, the marriage-auction, and deploring their strangest.",
      quote:{text:"Their wisest custom, in my judgement, was this: in every village they auctioned the marriageable girls once a year, the fair ones dowering the plain.", cite:"1.196"} },
    { id:"p-sauromatae", name:"Sauromatae", lat:48.5, lng:45.5, books:[4],
      blurb:"A people east of the Don, born (the story goes) of Scythian men and Amazon women. Their women ride, hunt and go to war like the men, and none may marry until she has killed an enemy.",
      quote:{text:"Their women ride to the hunt and to war as the men do; no girl weds until she has slain a man of the enemy.", cite:"4.117"} },
    { id:"p-garamantes", name:"Garamantes", lat:26.4, lng:13.0, books:[4],
      blurb:"A great nation of the inner Libyan desert who spread earth over the salt to sow crops, and who hunt the 'cave-dwelling Ethiopians' from four-horse chariots.",
      quote:{text:"The Garamantes hunt the cave-dwelling Ethiopians in four-horse chariots, for those are the swiftest-footed of all men of whom we hear.", cite:"4.183"} },
    { id:"p-nasamones", name:"Nasamones", lat:30.5, lng:19.5, books:[2,4],
      blurb:"A Libyan people of the Syrtis, whose bold young men once crossed the whole desert to the south-west and reached a great river of crocodiles running east — the first hint of the Niger, or the Nile's course.",
      quote:{text:"They came to a city by a great river running from west to east, full of crocodiles; and its people were small, dark men.", cite:"2.32"} },
    { id:"p-neuri", name:"Neuri", lat:50.5, lng:27.0, books:[4],
      blurb:"A people beyond Scythia of whom the Scythians told a strange thing: that once every year each of the Neuri becomes a wolf for a few days, and then a man again.",
      quote:{text:"It seems these people are wizards; for the Scythians say each Neurian turns into a wolf once a year, then back into a man.", cite:"4.105"} },
    { id:"p-androphagi", name:"Androphagi", lat:53.0, lng:33.0, books:[4],
      blurb:"The 'man-eaters' of the far north, of all men the most savage, who keep no law and no justice — the human edge of the knowable world.",
      quote:{text:"The Androphagi have the most savage customs of all men: they keep no justice and use no law of any kind.", cite:"4.106"} },
  ],

  /* --- NARRATIVE ROUTES --------------------------------------------------- */
  routes: [
    {
      id:"xerxes", name:"Xerxes' Invasion of Greece", years:"480 BC", books:[7,8],
      color:"#b5361f",
      desc:"The greatest expedition ever assembled marches from Susa to burn Athens — and is broken at sea within sight of the King. Follow it from the muster at Sardis, across the bridged Hellespont, down through Thrace to the pass at Thermopylae, into a deserted Athens, and to catastrophe at Salamis.",
      stops:[
        { name:"Susa", lat:32.1897, lng:48.2578, note:"Xerxes gathers the host and, over Artabanus' warning, resolves on war (7.8–19)." },
        { name:"Sardis", lat:38.4885, lng:28.0403, note:"The army winters and musters; Pythius the Lydian offers his fortune — and loses a son to the King's anger (7.27–39)." },
        { name:"Hellespont (Abydos)", lat:40.1960, lng:26.4083, note:"A storm wrecks the first bridges; Xerxes has the sea whipped and fettered, then crosses on a bridge of boats (7.34–36). He reviews the host and weeps (7.45)." },
        { name:"Doriscus", lat:40.8500, lng:26.0000, note:"On the Thracian plain the army is counted: 1,700,000 foot, the tale of nations (7.59–60, 7.89)." },
        { name:"Thermopylae", lat:38.7967, lng:22.5378, note:"Leonidas and the 300 hold the Hot Gates until the mountain path is betrayed (7.201–233)." },
        { name:"Athens", lat:37.9838, lng:23.7275, note:"The Persians take the abandoned city and burn the Acropolis (8.51–53)." },
        { name:"Salamis", lat:37.9600, lng:23.4900, note:"Lured into the straits, the King's fleet is destroyed as he watches from the shore (8.83–96)." },
      ]
    },
    {
      id:"darius-scythia", name:"Darius' Scythian Campaign", years:"c. 513 BC", books:[4],
      color:"#6b3fa0",
      desc:"Darius bridges the Bosphorus and the Ister to chase the Scythians into their own emptiness. They never give battle — they burn the grass, fill the wells, and lead him in circles until the King, baffled, must retreat to the bridge his Ionians barely still hold.",
      stops:[
        { name:"Susa", lat:32.1897, lng:48.2578, note:"Darius sets out to punish the Scythians for an old invasion of Asia (4.1, 4.83)." },
        { name:"Bosphorus bridge", lat:41.1200, lng:29.0700, note:"Mandrocles of Samos bridges the strait; Darius surveys the Black Sea and the joined continents (4.87–89)." },
        { name:"Ister (Danube) bridge", lat:45.1800, lng:28.8000, note:"He bridges the Ister and orders the Ionians to guard it sixty days (4.89, 4.98)." },
        { name:"Into Scythia", lat:48.5000, lng:33.0000, note:"The Scythians retreat endlessly, scorching the earth; Darius chases a war he can never bring on (4.120–142)." },
        { name:"Retreat to the Ister", lat:45.1800, lng:29.6700, note:"Deceived and hungry, the King steals back by night; the Ionians keep the bridge and save his army (4.133–142)." },
      ]
    },
    {
      id:"croesus", name:"Croesus Against Cyrus", years:"547 BC", books:[1],
      color:"#c98a1b",
      desc:"Misreading the oracle, the richest king in the world crosses the Halys to strike Persia first — and destroys 'a great empire,' his own. From Sardis he marches to an indecisive clash at Pteria, withdraws for the winter, and is chased home and burned upon a pyre.",
      stops:[
        { name:"Sardis", lat:38.4885, lng:28.0403, note:"Croesus, warned by Delphi that crossing the Halys will destroy a great empire, takes it as a promise (1.53, 1.71)." },
        { name:"The Halys", lat:41.7200, lng:36.0200, note:"He crosses the boundary river into Cappadocia and Persian ground (1.75)." },
        { name:"Pteria", lat:40.0200, lng:34.6150, note:"A hard, indecisive battle; outnumbered, Croesus withdraws to winter at Sardis (1.76)." },
        { name:"Sardis besieged", lat:38.4885, lng:28.0403, note:"Cyrus follows unseasonably fast, storms the citadel, and sets Croesus on the pyre — from which the god saves him (1.84–87)." },
      ]
    },
    {
      id:"phoenician-africa", name:"Circumnavigation of Africa", years:"c. 600 BC", books:[4],
      color:"#1c8a86",
      desc:"At Pharaoh Necho's command, Phoenician sailors set out down the Red Sea, keep the coast on their left, and after three years come home through the Pillars of Heracles — the first known rounding of Africa. Herodotus doubts one detail, and it is that very detail that convinces us they truly did it.",
      stops:[
        { name:"Red Sea (start)", lat:29.9000, lng:32.5500, note:"Necho sends the Phoenicians south from the Arabian Gulf to find whether Libya is ringed by sea (4.42)." },
        { name:"Southern tip", lat:-34.4000, lng:20.0000, note:"They round the far south — and there, they report, the sun stood on their right hand, to the north." },
        { name:"Pillars of Heracles", lat:36.1408, lng:-5.3536, note:"In the third year they pass back into the inner sea through the Pillars." },
        { name:"Egypt (home)", lat:31.2000, lng:32.3000, note:"They return to Egypt with a tale Herodotus reports but will not believe — the very reason we do." },
      ]
    },
    {
      id:"royal-road", name:"The Royal Road", years:"Persian era", books:[5,8],
      color:"#8a5a2b",
      desc:"The imperial highway from the Aegean to the King's seat — 111 posting-stations, guardhouses, and river-crossings over some 90 days' walk. Along it the King's mounted couriers pass the message hand to hand, faster than anything mortal.",
      stops:[
        { name:"Sardis", lat:38.4885, lng:28.0403, note:"The western end of the road, in the old Lydian capital (5.52)." },
        { name:"The Halys crossing", lat:41.0000, lng:35.0000, note:"Guard-posts hold the great river-gate of Cappadocia (5.52)." },
        { name:"Euphrates (Zeugma)", lat:37.0600, lng:37.8600, note:"The road crosses the Euphrates and enters Armenia and the rivers beyond (5.52)." },
        { name:"Tigris & the four rivers", lat:35.4700, lng:44.4000, note:"Four navigable rivers must be ferried before Susiana (5.52)." },
        { name:"Susa", lat:32.1897, lng:48.2578, note:"The road's end at the King's seat — 14,040 stades, 90 days on foot (5.53–54)." },
      ]
    },
  ],
};
