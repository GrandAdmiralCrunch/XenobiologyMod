"""Xenobiology — generates the Kerbin expansion 2 block of Kerbin.cfg: butterfly, moth, desert anaconda, sea tortoise,
beluga, man o' war, nautilus, vent tubeworms, cave glowworms (+ the Glowworm Grotto lair), rideable horse, megalodon and
anomalocaris; their clades; the megalodon tooth fossil.
Usage:  python kerbin_fauna2_cfg.py > fragment.cfg   (appended to Lifeforms/Stock/Kerbin.cfg after kerbin_fauna_cfg.py)
Also `patch(text)` applies the edits to the existing Kerbin block (duskmoth moves into Squamipennia; the coiled
thalassoshell fossil becomes evidence for the shelled cephalopods)."""

CLADES = [
    ("kerbin_squamipennia", "kerbin_pterohexa", "Squamipennia", "Order", "~140 million years ago", 1, "0.85,0.6,0.25,1",
     "\"Scale-wings\": insects whose broad wings are tiled with tiny coloured scales. Day fliers wear warning colours; night fliers wear eyespots and moonlight greens."),
    ("kerbin_lucivermidae", "kerbin_pterohexa", "Lucivermidae", "Family", "~60 million years ago", 1, "0.3,0.9,0.75,1",
     "Cave gnats whose larvae glow. A larva spins a curtain of sticky silk threads from the cave roof and lights them from below, and anything that flies toward the false stars is caught."),
    ("kerbin_testudinata", "kerbin_quadrimembra", "Testudinata", "Order", "~210 million years ago", 1, "0.35,0.5,0.35,1",
     "Shelled quadrimembrans. Their ribs fused into a domed carapace; the sea-going line traded feet for flippers but still crawls ashore to nest."),
    ("kerbin_cetolactia", "kerbin_lactifera", "Cetolactia", "Order", "~50 million years ago", 1, "0.85,0.9,0.95,1",
     "Milk-bearers that went back to the sea. They breathe through a blowhole, sing in clicks and whistles, and the white Arctic species can still turn its head on a flexible neck."),
    ("kerbin_colonomedusae", "kerbin_medusoida", "Colonomedusae", "Class", "~500 million years ago", 1, "0.55,0.55,0.95,1",
     "Colonies that pass as single animals: a gas float, feeding polyps and stinging fishing tentacles, each a different individual specialised for one job."),
    ("kerbin_cephaloconchia", "kerbin_thalassobiota", "Cephaloconchia", "Phylum", "~500 million years ago", 1, "0.8,0.5,0.35,1",
     "Shelled cephalopods: tentacled hunters living in the last chamber of a coiled, gas-filled shell they use as a float. The coiled shells high in Kerbin's mountains are theirs, and Laythe's soft-bodied squids descend from this line."),
    ("kerbin_tubicolae", "kerbin_thalassobiota", "Tubicolae", "Phylum", "~540 million years ago", 1, "0.85,0.15,0.15,1",
     "Tube-dwelling worms of the hydrothermal vents. They have no mouth or gut; bacteria living inside them make food from the vent's sulphur, and the red plumes are gills."),
    ("kerbin_selachopinna", "kerbin_pinnata", "Selachopinna", "Class", "~420 million years ago", 1, "0.4,0.45,0.5,1",
     "Cartilage-skeleton swimmers: sharks. Endless rows of replaceable teeth, which is why their fossils are almost entirely teeth."),
    ("kerbin_protoraptopoda", "kerbin_thalassobiota", "Protoraptopoda", "Phylum", "~520 million years ago", 1, "0.85,0.45,0.3,1",
     "The first big predators of Kerbin's oceans: segmented swimmers with flapping lobes and two raking claws before the mouth. A deep-water relict survives. Laythe's rakeclaws and tidal crawlers are its distant descendants."),
]

AV = dict(idleAnim="glide", moveAnim="glide", fleeAnim="flap", alertAnim="flap", fleeAnimSpeed=4)
BV = dict(AV, flapAnim="flap")             # butterflies: flutter-and-glide cruising, continuous flapping when climbing or fleeing
SPECIES = [
    dict(name="butterfly", clade="kerbin_squamipennia", display="Sunwing Butterfly", sci="Lepidovolans aurantius", habitat="Air", biomes="Grasslands, Highlands, Shores",
         active="Day", temper="Passive", group="1, 5", rarity=2.5, territory=0.65, size=1.0, speed=2, flee=4, alert=15, fleeD=6, observe=25, science=8,
         extra=dict(minAltitude=1, maxAltitude=8, groupSpread=3), diet="nectar, sap, fallen fruit",
         desc="A metre-wide butterfly whose orange wings are cut into panels by heavy black veins and edged with a black border set with two rows of white pearls; a band of cream spots crosses each black wingtip. It flutters three beats and glides, flutters and glides. On warm days hundreds drift across the grasslands, landing on anything bright, including rocket fuel tanks. Its wings are tiled with tiny scales that come off as orange dust on a kerbal's gloves.",
         model=dict(BV), proc=("Avian", "0.08,0.07,0.07,1", "0.98,0.55,0.1,1", 2.86)),
    dict(name="peacock", clade="kerbin_squamipennia", display="Peacock Eyewing", sci="Ocellopteryx pavonina", habitat="Air", biomes="Highlands, Mountains, Grasslands",
         active="Day", temper="Passive", group="1, 3", rarity=1.6, territory=0.6, size=0.8, speed=1.8, flee=4, alert=12, fleeD=5, observe=25, science=12,
         extra=dict(minAltitude=1, maxAltitude=10, groupSpread=3), diet="nectar, tree sap",
         desc="A rust-red butterfly with scalloped wings, each carrying one enormous eyespot: blue and violet pupils ringed in black and cream, flecked with white as if catching the light. Shut, the wings are bark-black and almost invisible on a tree trunk; flashed open, they become four staring eyes, and many birds back away. Related to the Sunwing, it shares the same vein plan beneath the paint.",
         model=dict(BV, fleeAnimSpeed=4), proc=("Avian", "0.14,0.09,0.07,1", "0.68,0.11,0.06,1", 2.0)),
    dict(name="swallowtail", clade="kerbin_squamipennia", display="Jewel Swallowtail", sci="Smaragdoptera caudata", habitat="Air", biomes="Shores, Grasslands",
         active="Day", temper="Passive", group="1, 2", rarity=1.2, territory=0.55, size=1.15, speed=2.4, flee=5, alert=15, fleeD=6, observe=30, science=14,
         extra=dict(minAltitude=2, maxAltitude=14, groupSpread=4), diet="nectar from coastal flowers",
         desc="The largest of Kerbin's scale-wings: velvet-black, with a glittering band of emerald shading to gold slashed across all four wings, a row of electric-blue crescents and a red eye at the base of each long, spoon-tipped tail. Underneath, the band turns cream and the crescents orange. It sails along the shoreline cliffs on long glides.",
         model=dict(BV, fleeAnimSpeed=5), proc=("Avian", "0.05,0.05,0.06,1", "0.3,0.85,0.45,1", 3.0)),
    dict(name="moth", clade="kerbin_squamipennia", display="Lunar Tailmoth", sci="Selenophalaena caudata", habitat="Air", biomes="Grasslands, Highlands, Tundra, Shores",
         active="Night", temper="Passive", group="1, 3", rarity=2, territory=0.6, size=0.8, speed=2, flee=4, alert=15, fleeD=5, observe=25, science=10,
         extra=dict(minAltitude=2, maxAltitude=15), diet="none as an adult - it lives a week on stored fat",
         desc="A pale green night moth with long trailing hindwing tails and four eyespots. Its wings glow very faintly, so on dark nights small groups look like drifting moonlight. Like the duskmoths, they are drawn to landing lights, and circle a lit lander until dawn.",
         blocks=[("LIGHT", dict(range=200, aggroTime=40, chaseSpeed=3, darkOnly="true", message="Lunar tailmoths are circling your lights."))],
         model=dict(AV), proc=("Avian", "0.93,0.93,0.86,1", "0.72,0.93,0.62,1", 2.6)),
    dict(name="anaconda", clade="kerbin_longiformes", display="Desert Anaconda", sci="Arenaboa magna", habitat="Ground", biomes="Deserts, Badlands",
         active="Any", temper="Territorial", group="1, 1", rarity=0.8, territory=0.4, size=9, speed=0.8, flee=2.5, alert=40, fleeD=10, observe=40, science=18,
         diet="kerbin_rockstrider, kerbin_scuttler, kerbin_springhopper, anything that sleeps too near its dune",
         desc="A sand-coloured constrictor nine metres long, blotched with dark brown saddles, the largest legless animal on Kerbin. It lies half-buried in the dunes for weeks between meals. Disturb it and it rears its head, hisses like a leaking fuel line and lunges; the strike is a shove rather than a bite, but it sends a kerbal sprawling.",
         blocks=[("ATTACK", dict(range=3.5, knockback=6, cooldown=8, duration=1.0, hitTime=0.4)),
                 ("SOUNDS", dict(alert="Xenobiology/Sounds/anaconda_hiss", attack="Xenobiology/Sounds/anaconda_hiss", volume=0.8, range=120))],
         model=dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", attackAnim="alert", moveAnimSpeed=0.8, fleeAnimSpeed=0.8),
         proc=("Serpent", "0.72,0.6,0.4,1", "0.27,0.19,0.11,1", 0)),
    dict(name="seatortoise", clade="kerbin_testudinata", display="Sea Tortoise", sci="Thalassochelys kerbinensis", habitat="Ground", biomes="Shores, Water",
         active="Any", temper="Passive", group="1, 3", rarity=1.5, territory=0.5, size=1.8, speed=0.5, flee=1.2, alert=15, fleeD=6, observe=35, science=12,
         extra=dict(swims="true", swimSpeed=1.6, waterline=0.44), diet="kerbin_moonjelly, sea grass",
         desc="A big olive-green turtle with a high domed shell of horn plates, each ringed with growth lines and streaked like old wood, its rear edge serrated, and long paddle flippers with a single claw. It glides through the shallows at a steady 1.6 m/s, hauls itself up the beach to bask and lay its eggs, and puts up with kerbals with immense, ancient patience. Some are thought to be older than the space program.",
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", moveAnimSpeed=0.5, fleeAnimSpeed=1.19, swimAnim="swim", floatAnim="float", swimAnimSpeed=1.6),
         proc=("Quadruped", "0.42,0.5,0.45,1", "0.33,0.4,0.26,1", 0)),
    dict(name="beluga", clade="kerbin_cetolactia", display="White Beluga", sci="Melonocetus albus", habitat="Water", biomes="Water, Shores",
         active="Any", temper="Curious", group="2, 6", rarity=1.5, territory=0.5, size=4.5, speed=1.5, flee=4, alert=80, fleeD=20, observe=60, science=16,
         extra=dict(waterline=0.35, groupSpread=7), diet="kerbin_glassfin, squid, shellfish",
         desc="A white whale with a bulging, squashy forehead (the melon), a permanent smile and no dorsal fin. Pods swim up to splashed-down capsules to look at them, turning their heads on unusually flexible necks, and chatter in whistles, squeals and clicks that carry through the hull. Sailors call them the canaries of the sea.",
         blocks=[("EMITTER", dict(kind="Steam", when="Moving", offset="0,0.5,1.4", rate=0.6, lifetime=2, speed=2.5, size=0.4, sizeGrow=2, radius=0.15, color="0.9,0.92,0.95,0.35", colorEnd="0.95,0.95,0.95,0")),
                 ("SOUNDS", dict(idle="Xenobiology/Sounds/beluga_song", alert="Xenobiology/Sounds/beluga_song", idleInterval=15, volume=0.9, range=400))],
         model=dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", moveAnimSpeed=1.5, fleeAnimSpeed=4), proc=("Fish", "0.9,0.92,0.94,1", "0.7,0.72,0.75,1", 0)),
    dict(name="manowar", clade="kerbin_colonomedusae", display="Bluesail Man o' War", sci="Pneumatophora velifera", habitat="Water", biomes="Water, Shores",
         active="Any", temper="Passive", group="3, 10", rarity=2, territory=0.45, size=1.2, speed=0.3, flee=0.5, alert=6, fleeD=2, observe=20, science=12,
         extra=dict(waterline=0.05, groupSpread=6, circling="false", turnRate=5), diet="kerbin_glassfin fry, plankton",
         desc="Not one animal but a colony: a blue gas float with a pink crest that catches the wind like a sail, polyps that digest and breed, and fishing tentacles that trail six metres below. Fleets of them drift wherever the wind blows. A kerbal swimming into the tentacles is stung and flung back - not dangerous in a suit, but very memorable.",
         blocks=[("ATTACK", dict(range=2.5, knockback=3, cooldown=6, duration=1.0, hitTime=0.5))],
         model=dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", attackAnim="sting"), proc=("Floater", "0.55,0.62,0.95,1", "0.88,0.52,0.88,1", 0)),
    dict(name="nautilus", clade="kerbin_cephaloconchia", display="Chambered Nautilus", sci="Nautiloides kerbini", habitat="Underwater", biomes="Water",
         active="Any", temper="Skittish", group="1, 3", rarity=1.2, territory=0.45, size=0.35, speed=0.6, flee=1.5, alert=15, fleeD=6, observe=20, science=14,
         extra=dict(minAltitude=15, maxAltitude=60), diet="shrimp, carrion, kerbin_glassfin eggs",
         desc="A living fossil: a tiger-striped coiled shell with a hood, a pinhole eye and some forty little tentacles. It rides up and down the water column by pumping gas into the empty chambers of its shell, and jets backward when startled. Its shells are identical in plan to the coiled fossils found on Kerbin's mountain tops.",
         model=dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", moveAnimSpeed=0.6, fleeAnimSpeed=1.5), proc=("Blob", "0.95,0.9,0.8,1", "0.62,0.26,0.12,1", 0)),
    dict(name="tubeworms", clade="kerbin_tubicolae", display="Smoker Tubeworms", sci="Fumivermis rubrus", habitat="Underwater", biomes="Water",
         active="Any", temper="Passive", group="1, 1", rarity=0.4, territory=0.15, size=3.5, speed=0, flee=0, alert=8, fleeD=7, observe=30, science=30,
         extra=dict(sessile="true", seafloor="true", minAltitude=0), diet="nothing - symbiotic bacteria feed them on vent sulphur",
         desc="A black-smoker chimney on the deep seabed, belching hot, mineral-black water and crusted with rust, ringed by a colony of white tubes as long as a kerbal. Each tube carries a blood-red feathery plume. Come close and the plumes snap back into their tubes, then slowly unfurl again. An entire food web lives here, powered by the planet's heat instead of the sun.",
         blocks=[("EMITTER", dict(kind="Steam", when="Always", offset="0,3.6,0", rate=6, lifetime=6, speed=0.7, size=0.5, sizeGrow=3, radius=0.2, gravity=-0.05, color="0.08,0.07,0.07,0.8", colorEnd="0.16,0.15,0.15,0")),
                 ("EMITTER", dict(kind="Bubbles", when="Always", offset="0,3.6,0", rate=4, lifetime=5, speed=0.5, size=0.06, radius=0.3))],
         model=dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"), proc=("Blob", "0.2,0.19,0.18,1", "0.86,0.08,0.1,1", 0)),
    dict(name="glowworm", clade="kerbin_lucivermidae", display="Lantern Glowworm", sci="Lucivermis pendulus", habitat="Ground", biomes="",
         active="Any", temper="Passive", group="1, 1", rarity=0, territory=0, size=9.4, speed=0, flee=0, alert=6, fleeD=6, observe=30, science=40,
         extra=dict(sessile="true", unique="true"), diet="gnats and moths caught on its threads",
         desc="The larvae of a cave gnat. Each lives in a silk nest on the cave roof and lowers dozens of threads beaded with sticky droplets, then lights its tail with a cold blue-green glow. A colony turns a cave ceiling into a starfield. When disturbed the larvae reel their lines in. Found only in the Glowworm Grotto.",
         model=dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"), proc=("Blob", "0.62,0.62,0.6,1", "0.2,0.95,0.78,1", 0)),
    dict(name="horse", clade="kerbin_ungulata", display="Plains Horse", sci="Hippokerbus velox", habitat="Ground", biomes="Grasslands, Highlands",
         active="Any", temper="Passive", group="3, 8", rarity=2, territory=0.5, size=2.6, speed=1.4, flee=12, alert=40, fleeD=6, observe=40, science=12,
         extra=dict(groupSpread=6), diet="grass",
         desc="A bay horse with a black mane, tail and stockings, living in loose herds on the open plains. They are unusually calm around kerbals, and anyone can climb on one simply by walking up to it. A ridden horse walks, trots and gallops at nearly 13 m/s: the fastest way to cross the grasslands without fuel.",
         blocks=[("SLEEP", dict(sleepsAt="Night", napChance=0.05, wakeDistance=5, wakeChance=0.4)),
                 ("MOUNT", dict(seat="saddle", seatOffset="0,0.15,0", mountRange=4.5, requireAsleep="false", walkSpeed=3, runSpeed=13, turnRate=75)),
                 ("SOUNDS", dict(idle="Xenobiology/Sounds/horse_whinny", alert="Xenobiology/Sounds/horse_whinny", idleInterval=30, volume=0.9, range=400))],
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", moveAnimSpeed=1.4, fleeAnimSpeed=11.23), proc=("Quadruped", "0.47,0.26,0.13,1", "0.08,0.07,0.06,1", 0)),
    dict(name="megalodon", clade="kerbin_selachopinna", display="Megalodon", sci="Carcharokerbus megalodon", habitat="Underwater", biomes="Water",
         active="Any", temper="Curious", group="1, 1", rarity=0.3, territory=0.25, size=16, speed=3, flee=8, alert=150, fleeD=15, observe=80, science=40,
         extra=dict(minAltitude=5, maxAltitude=60), diet="kerbin_beluga, kerbin_seatortoise, kerbin_nautilus, large fish",
         desc="A sixteen-metre shark, thought extinct for millions of years until a submarine pilot came home with a scratched hull and a photograph. It circles anything new in the water at a careful distance, then comes in close. It bites EVA kerbals hard enough to send them tumbling, and at this size it shoves whole vessels about. Its fossil teeth are found on old shorelines.",
         blocks=[("ATTACK", dict(range=7, knockback=12, cooldown=10, duration=1.0, hitTime=0.4))],
         model=dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="alert", attackAnim="bite", moveAnimSpeed=3, fleeAnimSpeed=8), proc=("Fish", "0.38,0.42,0.46,1", "0.9,0.9,0.88,1", 0)),
    dict(name="anomalocaris", clade="kerbin_protoraptopoda", display="Anomalocaris", sci="Anomalocaris kerbini", habitat="Underwater", biomes="Water",
         active="Any", temper="Skittish", group="1, 2", rarity=0.6, territory=0.35, size=2.4, speed=1.5, flee=4, alert=25, fleeD=10, observe=30, science=22,
         extra=dict(minAltitude=3, maxAltitude=40), diet="kerbin_nautilus, shrimp, worms",
         desc="A segmented swimmer from the dawn of animal life that never died out: banded red-orange, with rippling side lobes, a three-bladed tail fan, eyes on stalks and two spiny raking claws curled in front of a round, ring-toothed mouth. It rows itself along in waves of its lobes. Laythe's rakeclaws are its far-flung descendants.",
         model=dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert", moveAnimSpeed=1.5, fleeAnimSpeed=1.5), proc=("Serpent", "0.85,0.42,0.25,1", "0.35,0.12,0.08,1", 0)),
]

FOSSILS = [
    dict(name="kerbin_megalodon_tooth", display="Megalodon Tooth", form="Bones", kind="Tooth", biomes="Shores, Deserts, Badlands",
         evidence="kerbin_selachopinna", age="15 million years", color="0.25,0.24,0.24,1", rarity=0.8, minLevel=0, study=15, science=16,
         desc="A serrated triangle of black enamel as big as a kerbal's hand, weathering out of old shoreline sandstone. Sharks shed thousands of teeth in a lifetime, so the teeth are what survives. For years nobody believed an animal with teeth this size was still alive."),
]

LAIR = dict(name="kerbin_glowworm_grotto", displayName="Glowworm Grotto", model="Xenobiology/Models/Kerbin/GlowwormGrotto/glowworm_grotto", resident="kerbin_glowworm",
            latitude=45.0, longitude=135.5, searchRadius=20000, minAltitude=120, maxAltitude=3000, footprint=26, sink=0.3, heading=-1,
            loadRange=6000, residentRange=1500, discoverRange=12000, leash=4, entrance="entrance", den="den", pen="pen", scienceValue=60,
            description="A fern-hung limestone outcrop in the far northern highlands, about 50 km south-west of the Woomerang launch site. A stream runs out of its mouth from a domed chamber deep inside.",
            discoverMessage="A cold stream is running out of a cave mouth in a limestone hill",
            anomaly="true",
            surveyText="Switch your lamp off. The roof of the chamber is a field of blue-green stars: thousands of glowing silk threads hanging over a black, perfectly still pool. Every few seconds one of the lines twitches as something is reeled in.",
            waypoint="true")

def blk(name, d, ind="    "):
    out = [ind + name, ind + "{"]
    for k, v in d.items(): out.append(ind + "    %s = %s" % (k, v))
    out.append(ind + "}"); return out

def emit():
    L = ["", "// ============================================================ KERBIN EXPANSION 2",
         "// Butterflies and moths, desert anaconda, sea tortoise, beluga, man o' war, nautilus, vent tubeworms, cave glowworms",
         "// (and their Glowworm Grotto), the rideable Plains Horse, megalodon and anomalocaris. Generated by Tools/kerbin_fauna2_cfg.py;",
         "// models by fauna_kerbin2.py (whale, shark, siphon, nautilus, vent, glowworm), the mammal builder and classic archetypes.", ""]
    for n, par, disp, rank, era, th, col, desc in CLADES:
        L += ["XENO_CLADE", "{", "    name = " + n, "    parent = " + par, "    biosphere = kerbin_biosphere", "    displayName = " + disp,
              "    rank = " + rank, "    era = " + era, "    revealThreshold = %d" % th, "    color = " + col, "    description = " + desc, "}", ""]
    for s in SPECIES:
        n = "kerbin_" + s["name"]; cap = s["name"][0].upper() + s["name"][1:]
        L += ["XENO_LIFEFORM", "{", "    name = " + n, "    body = Kerbin", "    clade = " + s["clade"], "    displayName = " + s["display"],
              "    scientificName = " + s["sci"], "    silhouette = Xenobiology/Textures/Silhouettes/" + n, "    portrait = Xenobiology/Textures/Portraits/" + n,
              "    habitat = " + s["habitat"]]
        if s["biomes"]: L.append("    biomes = " + s["biomes"])
        if s["active"] != "Any": L.append("    activeTime = " + s["active"])
        L += ["    temperament = " + s["temper"], "    groupSize = " + s["group"], "    rarity = %g" % s["rarity"], "    territoryChance = %g" % s["territory"],
              "    size = %g" % s["size"], "    speed = %g" % s["speed"], "    fleeSpeed = %g" % s["flee"], "    alertDistance = %g" % s["alert"],
              "    fleeDistance = %g" % s["fleeD"], "    observeRange = %g" % s["observe"], "    scienceValue = %g" % s["science"]]
        for k, v in s.get("extra", {}).items(): L.append("    %s = %s" % (k, v))
        L += ["    diet = " + s["diet"], "    description = " + s["desc"]]
        for bn, bd in s.get("blocks", []): L += blk(bn, bd)
        md = {"path": "Xenobiology/Models/Kerbin/%s/%s" % (cap, s["name"])}; md.update(s["model"])
        L += blk("MODEL", md)
        plan, c1, c2, span = s["proc"]
        pr = {"bodyPlan": plan, "color": c1, "accentColor": c2, "bodyLength": 0.8, "bodyWidth": 0.3}
        if span: pr["wingSpan"] = span
        L += blk("PROCEDURAL", pr) + ["}", ""]
    L.append("// ------------------------------------------------------------ fossils")
    for f in FOSSILS:
        L += ["XENO_FOSSIL", "{", "    name = " + f["name"], "    body = Kerbin", "    displayName = " + f["display"],
              "    silhouette = Xenobiology/Textures/Silhouettes/fossil_" + f["name"], "    portrait = Xenobiology/Textures/Portraits/fossil_" + f["name"],
              "    form = " + f["form"], "    kind = " + f["kind"], "    biomes = " + f["biomes"], "    evidenceFor = " + f["evidence"], "    evidence = 1",
              "    age = " + f["age"], "    color = " + f["color"], "    rarity = %g" % f["rarity"], "    minLevel = %d" % f["minLevel"],
              "    studyTime = %d" % f["study"], "    scienceValue = %d" % f["science"], "    description = " + f["desc"]]
        L += blk("MODEL", {"path": "Xenobiology/Models/Fossils/Kerbin/" + f["name"]}) + ["}", ""]
    L.append("// ------------------------------------------------------------ the Glowworm Grotto (home of the Lantern Glowworms)")
    d = dict(LAIR); L += ["XENO_LAIR", "{", "    name = " + d.pop("name"), "    body = Kerbin"] + ["    %s = %s" % (k, v) for k, v in d.items()] + ["}", ""]
    return "\n".join(L)

def patch(text):
    """Edits to the existing Kerbin block."""
    a = "    name = kerbin_duskmoth\n    body = Kerbin\n    clade = kerbin_pterohexa\n"
    assert a in text, "duskmoth block not found"
    text = text.replace(a, "    name = kerbin_duskmoth\n    body = Kerbin\n    clade = kerbin_squamipennia\n")
    b = "    evidenceFor = kerbin_thalassobiota, kerbin_medusoida\n"
    assert b in text, "thalassoshell evidence not found"
    return text.replace(b, "    evidenceFor = kerbin_thalassobiota, kerbin_medusoida, kerbin_cephaloconchia\n")

if __name__ == "__main__":
    print(emit())
