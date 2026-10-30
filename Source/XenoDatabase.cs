using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    public enum Habitat { Ground, Water, Underwater, Air, Flyer }   // Flyer = walks on the ground, takes off and glides
    public enum Temperament { Skittish, Passive, Curious, Territorial }
    public enum ActivityTime { Any, Day, Night }
    public enum BodyPlan { Quadruped, Hexapod, Serpent, Avian, Fish, Floater, Blob }
    public enum FossilForm { Shell, Bones, Trackway, Stromatolite, Amber }

    /// <summary>Visual description used by the procedural creature builder.</summary>
    public class ProceduralLook
    {
        public BodyPlan bodyPlan = BodyPlan.Quadruped;
        public Color color = new Color(0.55f, 0.5f, 0.4f);
        public Color accentColor = new Color(0.3f, 0.25f, 0.2f);
        public Color glowColor = Color.black;     // black = no glow
        public float bodyLength = 1f;             // relative proportions (multiplied by size)
        public float bodyWidth = 0.45f;
        public float legLength = 0.5f;
        public float headSize = 0.3f;
        public float tailLength = 0.5f;
        public float wingSpan = 2f;
        public int segments = 8;                  // serpents / tentacles
        public int eyes = 2;

        public static ProceduralLook Parse(ConfigNode n)
        {
            var p = new ProceduralLook();
            if (n == null) return p;
            string s = n.GetValue("bodyPlan");
            if (!string.IsNullOrEmpty(s)) p.bodyPlan = XenoDatabase.ParseEnum(s, BodyPlan.Quadruped);
            n.TryGetValue("color", ref p.color);
            n.TryGetValue("accentColor", ref p.accentColor);
            n.TryGetValue("glowColor", ref p.glowColor);
            n.TryGetValue("bodyLength", ref p.bodyLength);
            n.TryGetValue("bodyWidth", ref p.bodyWidth);
            n.TryGetValue("legLength", ref p.legLength);
            n.TryGetValue("headSize", ref p.headSize);
            n.TryGetValue("tailLength", ref p.tailLength);
            n.TryGetValue("wingSpan", ref p.wingSpan);
            n.TryGetValue("segments", ref p.segments);
            n.TryGetValue("eyes", ref p.eyes);
            p.segments = Mathf.Clamp(p.segments, 2, 24);
            p.eyes = Mathf.Clamp(p.eyes, 0, 8);
            return p;
        }
    }

    /// <summary>Optional hand-made model (.mu or any GameDatabase model).</summary>
    public class ModelInfo
    {
        public string path;
        public float scale = 1f;
        public Vector3 rotationOffset = Vector3.zero;   // euler degrees, to fix exporter axes
        public Vector3 positionOffset = Vector3.zero;
        public string idleAnim, moveAnim, fleeAnim, alertAnim, sleepAnim, glideAnim, takeoffAnim, landAnim, attackAnim, digAnim, emergeAnim, diveAnim, screechAnim, roarAnim, throwAnim, leapAnim, burstAnim;
        public string flapAnim;            // Flyer: played instead of glideAnim while climbing or fleeing in the air (null = glideAnim)
        public string swimAnim, floatAnim; // swims: paddling / resting on the water (null = moveAnim / idleAnim)
        public float swimAnimSpeed = 0f;   // m/s at which swimAnim plays at 1x
        public float moveAnimSpeed = 0f;   // ground speed (m/s) at which moveAnim plays at 1x; 0 = always 1x
        public float fleeAnimSpeed = 0f;   // same for fleeAnim

        public static ModelInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var m = new ModelInfo();
            m.path = n.GetValue("path");
            if (string.IsNullOrEmpty(m.path)) return null;
            n.TryGetValue("scale", ref m.scale);
            n.TryGetValue("rotationOffset", ref m.rotationOffset);
            n.TryGetValue("positionOffset", ref m.positionOffset);
            m.idleAnim = n.GetValue("idleAnim");
            m.moveAnim = n.GetValue("moveAnim");
            m.fleeAnim = n.GetValue("fleeAnim") ?? m.moveAnim;
            m.alertAnim = n.GetValue("alertAnim") ?? m.idleAnim;
            m.sleepAnim = n.GetValue("sleepAnim") ?? m.idleAnim;
            m.glideAnim = n.GetValue("glideAnim") ?? m.moveAnim;
            m.takeoffAnim = n.GetValue("takeoffAnim");
            m.landAnim = n.GetValue("landAnim");
            m.attackAnim = n.GetValue("attackAnim");
            m.digAnim = n.GetValue("digAnim");
            m.emergeAnim = n.GetValue("emergeAnim");
            m.diveAnim = n.GetValue("diveAnim") ?? m.glideAnim;
            m.screechAnim = n.GetValue("screechAnim") ?? m.moveAnim;
            m.roarAnim = n.GetValue("roarAnim");
            m.throwAnim = n.GetValue("throwAnim");
            m.leapAnim = n.GetValue("leapAnim");
            m.burstAnim = n.GetValue("burstAnim");
            m.flapAnim = n.GetValue("flapAnim");
            m.swimAnim = n.GetValue("swimAnim");
            m.floatAnim = n.GetValue("floatAnim") ?? m.swimAnim;
            n.TryGetValue("swimAnimSpeed", ref m.swimAnimSpeed);
            n.TryGetValue("moveAnimSpeed", ref m.moveAnimSpeed);
            n.TryGetValue("fleeAnimSpeed", ref m.fleeAnimSpeed);
            return m;
        }
    }

    public class FlightInfo
    {
        public float cruiseSpeed = 12f, minSpeed = 6f, maxSpeed = 24f;
        public float sinkRate = 1.4f;          // m/s lost while gliding level
        public float climbRate = 4f;           // m/s gained while flapping (takeoff, AI climbs)
        public float takeoffTime = 1.2f, landTime = 1.2f;
        public float takeoffChance = 0.15f;    // per wander decision, AI only
        public float minGlideTime = 15f, maxGlideTime = 45f;
        public float cruiseHeight = 40f;       // AI tries to stay about this high above the ground
        public float flapImpulse = 6f;         // rider: vertical speed added by one flap
        public int flapStamina = 4;            // rider: flaps available before landing to rest
        public static FlightInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var f = new FlightInfo();
            n.TryGetValue("cruiseSpeed", ref f.cruiseSpeed); n.TryGetValue("minSpeed", ref f.minSpeed); n.TryGetValue("maxSpeed", ref f.maxSpeed);
            n.TryGetValue("sinkRate", ref f.sinkRate); n.TryGetValue("climbRate", ref f.climbRate);
            n.TryGetValue("takeoffTime", ref f.takeoffTime); n.TryGetValue("landTime", ref f.landTime);
            n.TryGetValue("takeoffChance", ref f.takeoffChance);
            n.TryGetValue("minGlideTime", ref f.minGlideTime); n.TryGetValue("maxGlideTime", ref f.maxGlideTime);
            n.TryGetValue("cruiseHeight", ref f.cruiseHeight);
            n.TryGetValue("flapImpulse", ref f.flapImpulse); n.TryGetValue("flapStamina", ref f.flapStamina);
            return f;
        }
    }

    public class SleepInfo
    {
        public ActivityTime sleepsAt = ActivityTime.Night;   // Night, Day, or Any (= naps only)
        public float napChance = 0.08f;                      // chance per idle decision to doze off when not sleep-time
        public float minNap = 30f, maxNap = 90f;
        public float wakeDistance = 4f;                      // something this close may wake it...
        public float wakeChance = 0.2f;                      // ...with this probability per second
        public static SleepInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var s = new SleepInfo();
            s.sleepsAt = XenoDatabase.ParseEnum(n.GetValue("sleepsAt"), ActivityTime.Night);
            n.TryGetValue("napChance", ref s.napChance); n.TryGetValue("minNap", ref s.minNap); n.TryGetValue("maxNap", ref s.maxNap);
            n.TryGetValue("wakeDistance", ref s.wakeDistance); n.TryGetValue("wakeChance", ref s.wakeChance);
            return s;
        }
    }

    public class AttackInfo
    {
        public float range = 5f;          // metres from the creature's centre
        public float knockback = 8f;      // m/s added to the victim
        public float cooldown = 6f;
        public float duration = 1.0f;     // seconds the attack animation lasts
        public float hitTime = 0.42f;     // normalised moment the blow lands
        public bool onlyWhenProvoked = false;
        public static AttackInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var a = new AttackInfo();
            n.TryGetValue("range", ref a.range); n.TryGetValue("knockback", ref a.knockback); n.TryGetValue("cooldown", ref a.cooldown);
            n.TryGetValue("duration", ref a.duration); n.TryGetValue("hitTime", ref a.hitTime); n.TryGetValue("onlyWhenProvoked", ref a.onlyWhenProvoked);
            return a;
        }
    }

    public class MountInfo
    {
        public string seat = "saddle";        // transform in the model the rider sits on
        public Vector3 seatOffset = Vector3.zero;
        public float mountRange = 5f;
        public bool requireAsleep = true;     // must be approached while sleeping
        public string requiredTrait = "";     // e.g. Pilot; empty = any kerbal
        public float walkSpeed = 2.5f, runSpeed = 6f, turnRate = 90f;
        public static MountInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var m = new MountInfo();
            if (n.HasValue("seat")) m.seat = n.GetValue("seat");
            n.TryGetValue("seatOffset", ref m.seatOffset);
            n.TryGetValue("mountRange", ref m.mountRange); n.TryGetValue("requireAsleep", ref m.requireAsleep);
            if (n.HasValue("requiredTrait")) m.requiredTrait = n.GetValue("requiredTrait");
            n.TryGetValue("walkSpeed", ref m.walkSpeed); n.TryGetValue("runSpeed", ref m.runSpeed); n.TryGetValue("turnRate", ref m.turnRate);
            return m;
        }
    }

    public class BurrowInfo
    {
        public float digTime = 1.5f, emergeTime = 1.2f;
        public float depth = 1.8f;                 // how far below the surface it sinks
        public float minUnderground = 6f, maxUnderground = 12f;
        public float tunnelSpeed = 4f;             // m/s while hidden
        public Color moundColor = new Color(0.85f, 0.87f, 0.9f);
        public float moundLife = 90f;              // seconds the spoil heaps stay
        public static BurrowInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var b = new BurrowInfo();
            n.TryGetValue("digTime", ref b.digTime); n.TryGetValue("emergeTime", ref b.emergeTime); n.TryGetValue("depth", ref b.depth);
            n.TryGetValue("minUnderground", ref b.minUnderground); n.TryGetValue("maxUnderground", ref b.maxUnderground);
            n.TryGetValue("tunnelSpeed", ref b.tunnelSpeed); n.TryGetValue("moundColor", ref b.moundColor); n.TryGetValue("moundLife", ref b.moundLife);
            return b;
        }
    }

    public class FlybyInfo
    {
        public float detectRange = 300f;     // spots kerbals / landed vessels within this distance
        public float diveSpeed = 22f;
        public float passHeight = 4f;        // metres above the target at the bottom of the pass
        public float screechDistance = 25f;  // starts screeching this far out (horizontal)
        public float passDuration = 1.8f;    // seconds it holds the pass before pulling up
        public float retreatSpeed = 18f, climbRate = 7f;
        public bool singlePass = true;       // true = never comes back for a second pass
        public float cooldown = 90f;         // when singlePass = false
        public static FlybyInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var f = new FlybyInfo();
            n.TryGetValue("detectRange", ref f.detectRange); n.TryGetValue("diveSpeed", ref f.diveSpeed); n.TryGetValue("passHeight", ref f.passHeight);
            n.TryGetValue("screechDistance", ref f.screechDistance); n.TryGetValue("passDuration", ref f.passDuration);
            n.TryGetValue("retreatSpeed", ref f.retreatSpeed); n.TryGetValue("climbRate", ref f.climbRate);
            n.TryGetValue("singlePass", ref f.singlePass); n.TryGetValue("cooldown", ref f.cooldown);
            return f;
        }
    }

    public class SoundInfo
    {
        public string idle, alert, attack, flee, flyby, dig, roar, throwSound, impact, footstep;   // GameDatabase audio paths (no extension)
        public float stepInterval = 0f;                         // seconds between footsteps at moveAnimSpeed (0 = no footsteps)
        public float idleInterval = 25f;                        // average seconds between idle calls
        public float volume = 1f, range = 250f;
        public float pitch = 1f;                                // < 1 = deeper and slower (a kilometre-long animal)
        public static SoundInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var s = new SoundInfo();
            s.idle = n.GetValue("idle"); s.alert = n.GetValue("alert"); s.attack = n.GetValue("attack");
            s.flee = n.GetValue("flee"); s.flyby = n.GetValue("flyby"); s.dig = n.GetValue("dig");
            s.roar = n.GetValue("roar") ?? s.alert; s.throwSound = n.GetValue("throw"); s.impact = n.GetValue("impact"); s.footstep = n.GetValue("footstep");
            n.TryGetValue("stepInterval", ref s.stepInterval);
            n.TryGetValue("idleInterval", ref s.idleInterval); n.TryGetValue("volume", ref s.volume); n.TryGetValue("range", ref s.range); n.TryGetValue("pitch", ref s.pitch);
            return s;
        }
    }

    public class ThrowInfo
    {
        public float minRange = 35f, maxRange = 260f;
        public float launchSpeed = 55f;       // m/s; the aim picks the flatter ballistic arc that reaches
        public float cooldown = 10f;
        public float duration = 4f;           // seconds the throw animation lasts
        public float releaseTime = 0.62f;     // normalised moment the projectile leaves the hand
        public string hand = "handL";         // transform the boulder is held by until release
        public Vector3 releaseOffset = new Vector3(0, 0, 0);
        public float radius = 1.6f;           // projectile radius (m)
        public float mass = 6f;               // tonnes
        public float lead = 1f;               // 0 = aim at where the target is, 1 = where it will be
        public float spread = 4f;             // metres of random miss at the target
        public Color color = new Color(0.42f, 0.4f, 0.36f);
        public static ThrowInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var t = new ThrowInfo();
            n.TryGetValue("minRange", ref t.minRange); n.TryGetValue("maxRange", ref t.maxRange); n.TryGetValue("launchSpeed", ref t.launchSpeed);
            n.TryGetValue("cooldown", ref t.cooldown); n.TryGetValue("duration", ref t.duration); n.TryGetValue("releaseTime", ref t.releaseTime);
            if (n.HasValue("hand")) t.hand = n.GetValue("hand");
            n.TryGetValue("releaseOffset", ref t.releaseOffset);
            n.TryGetValue("radius", ref t.radius); n.TryGetValue("mass", ref t.mass); n.TryGetValue("lead", ref t.lead); n.TryGetValue("spread", ref t.spread);
            n.TryGetValue("color", ref t.color);
            return t;
        }
    }

    public class RoarInfo
    {
        public float duration = 3.5f, cooldown = 30f;
        public float range = 400f;            // roars at intruders that come this close
        public float scareRadius = 150f;      // other wildlife within this radius flees
        public static RoarInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var r = new RoarInfo();
            n.TryGetValue("duration", ref r.duration); n.TryGetValue("cooldown", ref r.cooldown);
            n.TryGetValue("range", ref r.range); n.TryGetValue("scareRadius", ref r.scareRadius);
            return r;
        }
    }

    /// <summary>LIGHT {}: lights provoke the creature (e.g. deep-sea squid). It hunts the light source down and attacks.</summary>
    public class LightInfo
    {
        public float range = 250f;            // notices lit vessels / kerbal headlamps this close
        public float aggroTime = 20f;         // keeps hunting this long after the light goes out
        public float chaseSpeed = -1f;        // -1 = fleeSpeed
        public bool darkOnly = true;          // only provoked where it is dark (night, or deeper than darkDepth)
        public float darkDepth = 60f;
        public string message;                // screen message when first drawn to your lights (default: a warning)
        public static LightInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var l = new LightInfo();
            l.message = n.GetValue("message");
            n.TryGetValue("range", ref l.range); n.TryGetValue("aggroTime", ref l.aggroTime); n.TryGetValue("chaseSpeed", ref l.chaseSpeed);
            n.TryGetValue("darkOnly", ref l.darkOnly); n.TryGetValue("darkDepth", ref l.darkDepth);
            return l;
        }
    }

    /// <summary>LEAP {}: a swimmer that jumps clear of the water (skimmers, breaching leviathans).</summary>
    public class LeapInfo
    {
        public float height = 3f;             // metres above the surface at the top of the arc
        public float length = 12f;            // horizontal distance covered
        public float duration = 1.6f;
        public float chance = 0.15f;          // per wander decision
        public bool whenFleeing = true;       // leaps to escape
        public float cooldown = 8f;
        public static LeapInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var l = new LeapInfo();
            n.TryGetValue("height", ref l.height); n.TryGetValue("length", ref l.length); n.TryGetValue("duration", ref l.duration);
            n.TryGetValue("chance", ref l.chance); n.TryGetValue("whenFleeing", ref l.whenFleeing); n.TryGetValue("cooldown", ref l.cooldown);
            return l;
        }
    }

    /// <summary>COLONY {}: smaller creatures that live on this one, e.g. crestflies nesting on a bloatfloater's crown.
    /// Colonists perch on the host, fly loops round it, and now and then stray into its tendrils and are eaten.</summary>
    public class ColonyInfo
    {
        public string species;
        public LifeformDef def;
        public int min = 4, max = 8;
        public float perchHeight = 10f;       // metres above the host's origin at the centre of the perch
        public float perchRadius = 5f;        // perch disc radius
        public float perchDrop = 0.03f;       // the perch is domed: height falls by perchDrop * r^2
        public float orbitRadius = 25f;       // sortie loops round the host
        public float orbitHeight = 15f;
        public float tendrilDepth = 30f;      // centre of the feeding zone below the host's origin
        public float tendrilRadius = 15f;
        public float sortieChance = 0.5f;     // per perch period
        public float preyChance = 0.15f;      // per sortie: strays into the tendrils and is eaten
        public float regrowTime = 90f;        // seconds per new colonist while below max
        public float swarmDistance = 80f;     // vessels this close send the colony up
        public string feedMessage = "";
        public static ColonyInfo Parse(ConfigNode n)
        {
            if (n == null || string.IsNullOrEmpty(n.GetValue("species"))) return null;
            var c = new ColonyInfo { species = n.GetValue("species") };
            n.TryGetValue("min", ref c.min); n.TryGetValue("max", ref c.max); if (c.max < c.min) c.max = c.min;
            n.TryGetValue("perchHeight", ref c.perchHeight); n.TryGetValue("perchRadius", ref c.perchRadius); n.TryGetValue("perchDrop", ref c.perchDrop);
            n.TryGetValue("orbitRadius", ref c.orbitRadius); n.TryGetValue("orbitHeight", ref c.orbitHeight);
            n.TryGetValue("tendrilDepth", ref c.tendrilDepth); n.TryGetValue("tendrilRadius", ref c.tendrilRadius);
            n.TryGetValue("sortieChance", ref c.sortieChance); n.TryGetValue("preyChance", ref c.preyChance);
            n.TryGetValue("regrowTime", ref c.regrowTime); n.TryGetValue("swarmDistance", ref c.swarmDistance);
            c.feedMessage = n.GetValue("feedMessage") ?? "";
            return c;
        }
    }

    /// <summary>METAMORPHOSIS {}: a larva that, while someone is watching, may swell with gas, rise to the surface
    /// and turn into its next life stage there (Sky Leviathan grubs becoming floating pupae).</summary>
    public class MetamorphInfo
    {
        public string into;
        public LifeformDef intoDef;
        public float chance = 0.02f;          // per individual per minute, while a vessel is within watchRange
        public float watchRange = 1500f;
        public float swellTime = 15f;         // seconds to inflate on the sea floor
        public float swellScale = 2.5f;
        public float riseSpeed = 3f;          // m/s up through the water
        public string message = "";
        public static MetamorphInfo Parse(ConfigNode n)
        {
            if (n == null || string.IsNullOrEmpty(n.GetValue("into"))) return null;
            var m = new MetamorphInfo { into = n.GetValue("into") };
            n.TryGetValue("chance", ref m.chance); n.TryGetValue("watchRange", ref m.watchRange); n.TryGetValue("swellTime", ref m.swellTime);
            n.TryGetValue("swellScale", ref m.swellScale); n.TryGetValue("riseSpeed", ref m.riseSpeed);
            m.message = n.GetValue("message") ?? "";
            return m;
        }
    }

    /// <summary>BURST {}: a sessile organism that bursts when something touches it (spore puffballs).</summary>
    public class BurstInfo
    {
        public float triggerRange = 2.5f;     // metres from the organism's centre
        public float duration = 1.2f;         // seconds of the burst animation
        public float regrowTime = 300f;       // seconds before it is whole again (hidden meanwhile)
        public string message = "";           // optional screen message
        public static BurstInfo Parse(ConfigNode n)
        {
            if (n == null) return null;
            var b = new BurstInfo();
            n.TryGetValue("triggerRange", ref b.triggerRange); n.TryGetValue("duration", ref b.duration); n.TryGetValue("regrowTime", ref b.regrowTime);
            b.message = n.GetValue("message") ?? "";
            return b;
        }
    }

    public enum EmitWhen { Always, Idle, Moving, Fleeing, Burst, Leap, Night, Provoked }

    /// <summary>EMITTER {}: a particle effect attached to the creature (bubbles, spores, motes, splashes).</summary>
    public class EmitterInfo
    {
        public string kind = "Motes";         // Bubbles, Spores, Motes, Splash, Steam (texture + defaults)
        public string transform = "";         // child transform to emit from; empty = creature centre
        public Vector3 offset = Vector3.zero; // local offset in metres (x right, y up, z forward)
        public EmitWhen when = EmitWhen.Always;
        public float rate = 10f;              // particles per second (continuous)
        public int burst = 0;                 // particles emitted at once when `when` starts (Burst/Leap)
        public float lifetime = 3f, speed = 0.5f, size = 0.3f, sizeGrow = 1.5f;
        public float radius = 0.5f;           // spawn sphere radius
        public float gravity = 0f;            // negative = rises (bubbles)
        public Color color = new Color(1, 1, 1, 0.6f), colorEnd = new Color(1, 1, 1, 0f);
        public bool underwaterOnly, surfaceOnly;
        public static EmitterInfo Parse(ConfigNode n)
        {
            var e = new EmitterInfo();
            if (n.HasValue("kind")) e.kind = n.GetValue("kind");
            e.transform = n.GetValue("transform") ?? "";
            n.TryGetValue("offset", ref e.offset);
            e.when = XenoDatabase.ParseEnum(n.GetValue("when"), EmitWhen.Always);
            n.TryGetValue("rate", ref e.rate); n.TryGetValue("burst", ref e.burst);
            n.TryGetValue("lifetime", ref e.lifetime); n.TryGetValue("speed", ref e.speed); n.TryGetValue("size", ref e.size); n.TryGetValue("sizeGrow", ref e.sizeGrow);
            n.TryGetValue("radius", ref e.radius); n.TryGetValue("gravity", ref e.gravity);
            n.TryGetValue("color", ref e.color); n.TryGetValue("colorEnd", ref e.colorEnd);
            n.TryGetValue("underwaterOnly", ref e.underwaterOnly); n.TryGetValue("surfaceOnly", ref e.surfaceOnly);
            return e;
        }
    }

    /// <summary>
    /// A microbe from another mod's database (MicrobiologyExpansion's MICROBE nodes). Static data is read from
    /// GameDatabase; discovery / lab state comes from MicrobeBridge at runtime.
    /// </summary>
    public class MicrobeDef
    {
        public string name, category, homePlanet, flavorText, icon, hazard, situation;
        public string[] biomes = new string[0];
        public string[] consumes = new string[0];
        public float scienceValue;
        public CladeDef parentClade;
        public Texture2D iconTex;
        public bool IsLife { get { return category != "Debris" && category != "Unknown"; } }
        public bool IsMicrofossil { get { return category == "Fossil"; } }
    }

    /// <summary>A fixed home (cave, nest, burrow...) that a unique resident lives in.</summary>
    public class LairDef
    {
        public string name, displayName, body, description, model, resident;
        public double latitude, longitude;          // centre of the search area
        public float searchRadius = 6000f;          // the flattest suitable spot inside this radius is chosen once per save
        public float minAltitude = 50f, maxAltitude = 3000f;
        public float footprint = 70f;               // radius (m) that should be flat
        public float sink = 0.6f;                   // lower the model into the ground by this much
        public float heading = -1f;                 // direction the entrance faces; -1 = downhill
        public float loadRange = 12000f;            // the model exists within this distance
        public float residentRange = 3500f;         // the resident lives (is simulated) within this distance
        public float discoverRange = 30000f;        // a waypoint appears once a vessel comes this close
        public float leash = 450f;                  // resident never strays further than this from the entrance
        public string doorOpenAnim = "open", doorCloseAnim = "close";
        public string entrance = "entrance", den = "den", pen = "pen";
        public string flock;                        // lifeform kept by the lair (e.g. grazing outside by day)
        public int flockMin = 3, flockMax = 5;
        public bool waypoint = true;
        public float scienceValue = 40f;            // EVA "Survey" from inside the lair
        public string surveyText = "";
        public string discoverMessage = "";         // shown when a vessel first comes within discoverRange
        public bool anomaly = true;                 // listed as a surface anomaly (KerbNet, SCANsat...)
        public bool underwater;                     // sited on the sea floor: min/maxAltitude are depths below sea level (negative)
        public float surveyRadius;                  // > 0: "inside" = within this radius of the centre (open sites like a reef)
        public bool lightsNightOnly;                // point lights only switch on at night
        public float glowPulse;                     // emissive materials breathe by this fraction (0 = steady)
        public float dayGlow = 1f;                  // emissive brightness by day (bioluminescence is mostly seen at night)
        public float swayAngle = 4f;
        public float detailRange;
        public bool clearScatters = true;           // keep Parallax terrain scatters (kelp, grass, trees) off the site
        public float scatterClearRadius;            // metres; 0 = 1.5 x footprint                   // > 0: children named coral_* / sway_* / dayonly_* are hidden beyond this distance                // degrees: children named "sway..." rock back and forth (sea fans, kelp)
        public CelestialBody celestialBody;
        public LifeformDef residentDef, flockDef;
        public float detailRangeSmall;              // > 0: objects named coral_s_* are hidden beyond this (default 0.3 x detailRange)
        public float catalogueScience;              // bonus when every species with a spec_ marker in the model has been observed
        public readonly List<LairFlock> flocks = new List<LairFlock>();   // FLOCK { lifeform = ..  size = a, b  spread = m  at = spot  leash = m }
        public ForestDef forest;                    // FOREST {}: a generated forest around the site (model optional)
    }

    public class LairFlock
    {
        public string lifeform; public LifeformDef def; public int min = 1, max = 3; public float spread = 30f;
        public string at;                // named spot (forest: clearing, bridge, pond, pool, stream, elder, entrance) or model transform; default pen
        public float leash;              // > 0: the flock turns back when it strays further than this from where it was spawned
    }

    public class BiosphereDef
    {
        public string name, body, displayName, description, rootClade;
        public string microbeClade;          // unplaced microbes of this body go here (MicrobiologyExpansion)
        public float spawnDensity = 1f;
        public bool extinct;                 // fossils only, nothing spawns alive
        public string url;
    }

    public class CladeDef
    {
        public string name, displayName, rank, parent, biosphere, description, era;
        public int revealThreshold = 2;
        public Color color = new Color(0.6f, 0.8f, 0.6f);
        public bool grouping;                    // not a true clade: unrelated lineages that share a world (drawn with dotted links)
        public string[] microbeNames = new string[0];       // microbes = A, B   (exact MICROBE names)
        public string[] microbeCategories = new string[0];  // microbeCategories = Bacteria, Archaea  (this body's unplaced microbes)
        // runtime
        public readonly List<MicrobeDef> microbes = new List<MicrobeDef>();
        public readonly List<CladeDef> childClades = new List<CladeDef>();
        public readonly List<LifeformDef> species = new List<LifeformDef>();
        public CladeDef parentClade;
        public int depth;
    }

    public class LifeformDef
    {
        public string name, displayName, scientificName, clade, body, description, silhouette, portrait;
        public string[] biomes = new string[0];      // empty = any biome
        public Habitat habitat = Habitat.Ground;
        public Temperament temperament = Temperament.Skittish;
        public ActivityTime activeTime = ActivityTime.Any;
        public float rarity = 1f;                     // spawn weight
        public float territoryChance = 0.6f;          // chance a territory cell hosts this species
        public int minGroup = 1, maxGroup = 1;
        public float size = 1f;                       // metres, overall scale
        public float speed = 2f, fleeSpeed = 6f;
        public float fleeDistance = 30f, alertDistance = 60f;
        public float observeRange = -1f;              // -1 = settings default
        public float minAltitude = 10f, maxAltitude = 80f; // Air: above ground/sea. Underwater: depth below 0
        public float scienceValue = 10f;
        public ProceduralLook look;
        public ModelInfo model;
        public FlightInfo flight;     // FLIGHT {}  (habitat = Flyer)
        public SleepInfo sleep;       // SLEEP {}
        public AttackInfo attack;     // ATTACK {}
        public MountInfo mount;       // MOUNT {}  makes the creature rideable
        public BurrowInfo burrow;     // BURROW {} digs in and tunnels away instead of running
        public FlybyInfo flyby;       // FLYBY {}  (habitat = Air) dives at intruders for one pass, then leaves
        public SoundInfo sounds;      // SOUNDS {}
        public ThrowInfo throwing;    // THROW {}  hurls projectiles at intruders
        public RoarInfo roar;         // ROAR {}   bellows at intruders before engaging
        public LightInfo light;       // LIGHT {}  provoked by lights
        public LeapInfo leap;         // LEAP {}   jumps clear of the water
        public BurstInfo burst;       // BURST {}  bursts when touched (sessile)
        public readonly List<EmitterInfo> emitters = new List<EmitterInfo>();   // EMITTER {} (any number)
        public bool unique;           // never spawned at random; only by its LAIR
        public bool sessile;          // never moves (corals, fungi, floating mats)
        public string guideCategory;
        public readonly List<PlumeInfo> plumes = new List<PlumeInfo>();   // PLUME {}: fake-volumetric smoke columns  // what an unidentified one is called ("coral", "sponge"...)
        public bool seafloor;         // Underwater: lives on the seabed (minAltitude = height above it)
        public bool amphibious;       // Ground: also walks into the sea and along the seabed
        public bool walkOnWater;      // Ground: runs across the water surface
        public bool swims;            // Ground/Flyer: swims at the surface over deep water (waterfowl, penguins, capybaras); Flyers may land on water
        public float swimSpeed = -1f; // m/s paddling speed (-1 = speed); fleeing swimmers manage 1.6x this
        public float waterline = -1f; // Water: depth of its centre below the surface (-1 = 15% of size)
        public float groupSpread = 0f;
        public bool circling = true;          // Air: lazy circles while wandering (false = long straight drifts)
        public float turnRate = 0f;           // deg/s; 0 = default
        public float maxClimbRate = 0f;       // m/s cap on altitude changes (0 = no cap); keeps huge drifters level
        public float cruiseChangeMin = 5f, cruiseChangeMax = 15f;   // Air: seconds between new cruise heights// metres between group members (0 = 2.5 x size); small = dense schools
        public string[] diet = new string[0];   // lifeform names, MICROBE names or plain text
        public string lifeStageOf;    // this is a juvenile/larval form of another lifeform
        public string lifeStage = ""; // label for this form, e.g. "Larva"
        public LifeformDef adultDef;
        public readonly List<LifeformDef> juveniles = new List<LifeformDef>();
        public ColonyInfo colony;     // COLONY {}  smaller creatures that live on this one
        public MetamorphInfo metamorph;  // METAMORPHOSIS {}  a larva that turns into its next stage
        public float spawnDistanceMin, spawnDistanceMax;   // > 0: giants spawned far out (seen from afar), not in the normal ring
        public float despawnDistance;                      // > 0: overrides the global despawn radius
        public float maxWadeDepth;                         // amphibious walkers: deepest water (m) they will wade into (0 = any)
        public float farSpawnChance = 0.05f;               // per far-spawn check (every 20 s) while none is around
        public string farSpawnMessage = "";
        public float DespawnDistance { get { return despawnDistance > 0f ? despawnDistance : XenoSettings.DespawnRadius; } }
        public LifeformDef colonyHost;  // set on a colonist species: it only spawns with (and on) this host
        public float CapWeight { get { return colonyHost != null ? 0.1f : (maxGroup >= 8 ? 0.25f : 1f); } }   // schools and colonists count less against the spawn cap
        // runtime
        public CladeDef parentClade;
        public CelestialBody celestialBody;
        Texture2D silTex, porTex;
        public Texture2D silhouetteTex { get { return silTex ?? (silTex = XenoTextures.Get(silhouette)); } }
        public Texture2D portraitTex { get { return porTex ?? (porTex = XenoTextures.Get(portrait)); } }

        public float ObserveRange { get { return observeRange > 0 ? observeRange : XenoSettings.DefaultObserveRange; } }

        public bool LivesInBiome(string biome)
        {
            if (biomes.Length == 0) return true;
            string b = XenoDatabase.NormBiome(biome);
            for (int i = 0; i < biomes.Length; i++)
                if (biomes[i] == b || biomes[i] == "any") return true;
            return false;
        }
    }

    public class FossilDef
    {
        public string name, displayName, body, description, silhouette, portrait;
        public string kind;                            // free-text type label for the guide (default: form)
        public string[] biomes = new string[0];
        public string[] evidenceFor = new string[0];  // clade or panspermia names
        public int evidence = 1;                       // evidence points per distinct fossil type studied
        public string ageText = "";
        public FossilForm form = FossilForm.Shell;
        public Color color = new Color(0.75f, 0.7f, 0.6f);
        public float rarity = 1f;
        public float size = 1f;
        public string requiredTrait = "Scientist";     // empty = anyone
        public int minLevel = 0;
        public float studyTime = 20f;                  // seconds at level 0
        public float scienceValue = 15f;
        public ModelInfo model;
        public CelestialBody celestialBody;
        Texture2D silTex, porTex;
        public Texture2D silhouetteTex { get { return silTex ?? (silTex = XenoTextures.Get(silhouette)); } }
        public Texture2D portraitTex { get { return porTex ?? (porTex = XenoTextures.Get(portrait)); } }
        // ---- landmarks: one huge, unique site placed once per save (e.g. the Fallen Titan)
        public bool landmark;
        public bool unique;                        // never scattered at random: only placed by a lair (fossil_<name>_## marker)
        public double searchLat = double.NaN, searchLon = double.NaN;   // optional search centre; default: scan the whole body for `biomes`
        public float searchRadius = 0f;            // metres around the search centre (0 with no centre = whole-body scan)
        public float footprint = 1000f;            // metres; used to find flat enough ground
        public float loadRange = 40000f, discoverRange = 25000f;
        public float studyRange = 40f;             // horizontal metres from a study point
        public float beaconSize = 3f;
        public double heading = -1;                // degrees; -1 = chosen by the site
        public string discoverMessage = "";
        public readonly List<Vector3> studyPoints = new List<Vector3>();   // model-local (Unity: x right, y up, z forward), metres
        public string KindLabel { get { return string.IsNullOrEmpty(kind) ? form.ToString() : kind; } }

        public bool InBiome(string biome)
        {
            if (biomes.Length == 0) return true;
            string b = XenoDatabase.NormBiome(biome);
            for (int i = 0; i < biomes.Length; i++)
                if (biomes[i] == b || biomes[i] == "any") return true;
            return false;
        }
    }

    public class PanspermiaDef
    {
        public string name, displayName, description, sourceClade, targetBiosphere, targetClade, mechanism, ageText;
        public string[] microbeEvidence = new string[0];   // each of these microbes discovered = +1 evidence
        public int revealThreshold = 3;
        public CladeDef source;
        public BiosphereDef target;
        public CladeDef targetCladeDef;      // the lineage that was seeded (default: the biosphere's root)
    }

    /// <summary>
    /// Loads and cross-links every XENO_* node in GameDatabase. Anything that refers to a body
    /// which isn't installed is skipped quietly, so planet-pack content can ship unconditionally.
    /// </summary>
    public static class XenoDatabase
    {
        public static readonly Dictionary<string, BiosphereDef> Biospheres = new Dictionary<string, BiosphereDef>();
        public static readonly Dictionary<string, CladeDef> Clades = new Dictionary<string, CladeDef>();
        public static readonly Dictionary<string, LifeformDef> Lifeforms = new Dictionary<string, LifeformDef>();
        public static readonly Dictionary<string, FossilDef> Fossils = new Dictionary<string, FossilDef>();
        public static readonly Dictionary<string, PanspermiaDef> Panspermia = new Dictionary<string, PanspermiaDef>();
        public static readonly Dictionary<string, LairDef> Lairs = new Dictionary<string, LairDef>();
        public static readonly Dictionary<string, MicrobeDef> Microbes = new Dictionary<string, MicrobeDef>();
        public static readonly Dictionary<string, FeatureDef> Features = new Dictionary<string, FeatureDef>();
        public static readonly List<string> Problems = new List<string>();
        public static bool Loaded;

        public static string NormBiome(string b)
        {
            if (string.IsNullOrEmpty(b)) return "";
            return b.Replace(" ", "").Replace("_", "").ToLowerInvariant();
        }

        public static T ParseEnum<T>(string s, T fallback) where T : struct
        {
            if (string.IsNullOrEmpty(s)) return fallback;
            try { return (T)Enum.Parse(typeof(T), s.Trim(), true); }
            catch { Problem("Unknown " + typeof(T).Name + " '" + s + "'"); return fallback; }
        }

        static void Problem(string msg) { Problems.Add(msg); XenoLog.Warn(msg); }

        static string[] SplitList(string s)
        {
            if (string.IsNullOrEmpty(s)) return new string[0];
            return s.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim()).Where(x => x.Length > 0).ToArray();
        }

        static CelestialBody FindBody(string name)
        {
            if (string.IsNullOrEmpty(name) || FlightGlobals.Bodies == null) return null;
            return FlightGlobals.Bodies.FirstOrDefault(b => b.name == name || b.bodyName == name);
        }

        public static void Load()
        {
            Biospheres.Clear(); Clades.Clear(); Lifeforms.Clear(); Fossils.Clear(); Panspermia.Clear(); Lairs.Clear(); Microbes.Clear(); Features.Clear(); Problems.Clear();

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_BIOSPHERE"))
            {
                ConfigNode n = url.config;
                var b = new BiosphereDef { url = url.url };
                b.name = n.GetValue("name"); b.body = n.GetValue("body");
                if (string.IsNullOrEmpty(b.name) || string.IsNullOrEmpty(b.body)) { Problem("XENO_BIOSPHERE missing name/body in " + url.url); continue; }
                if (FindBody(b.body) == null) { XenoLog.Info("Biosphere " + b.name + " skipped: body '" + b.body + "' not installed"); continue; }
                b.displayName = n.GetValue("displayName") ?? b.body + " Biosphere";
                b.description = n.GetValue("description") ?? "";
                b.rootClade = n.GetValue("rootClade");
                n.TryGetValue("spawnDensity", ref b.spawnDensity);
                b.microbeClade = n.GetValue("microbeClade");
                n.TryGetValue("extinct", ref b.extinct);
                Biospheres[b.name] = b;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_CLADE"))
            {
                ConfigNode n = url.config;
                var c = new CladeDef();
                c.name = n.GetValue("name");
                if (string.IsNullOrEmpty(c.name)) { Problem("XENO_CLADE without name in " + url.url); continue; }
                c.displayName = n.GetValue("displayName") ?? c.name;
                c.rank = n.GetValue("rank") ?? "Clade";
                c.parent = n.GetValue("parent");
                c.biosphere = n.GetValue("biosphere");
                c.description = n.GetValue("description") ?? "";
                c.era = n.GetValue("era") ?? "";
                n.TryGetValue("revealThreshold", ref c.revealThreshold);
                n.TryGetValue("color", ref c.color);
                n.TryGetValue("grouping", ref c.grouping);
                c.microbeNames = SplitList(n.GetValue("microbes"));
                c.microbeCategories = SplitList(n.GetValue("microbeCategories"));
                Clades[c.name] = c;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_LIFEFORM"))
            {
                ConfigNode n = url.config;
                var l = new LifeformDef();
                l.name = n.GetValue("name");
                if (string.IsNullOrEmpty(l.name)) { Problem("XENO_LIFEFORM without name in " + url.url); continue; }
                l.body = n.GetValue("body");
                l.celestialBody = FindBody(l.body);
                if (l.celestialBody == null) { XenoLog.Info("Lifeform " + l.name + " skipped: body '" + l.body + "' not installed"); continue; }
                l.displayName = n.GetValue("displayName") ?? l.name;
                l.scientificName = n.GetValue("scientificName") ?? "";
                l.clade = n.GetValue("clade");
                l.description = n.GetValue("description") ?? "";
                l.silhouette = n.GetValue("silhouette");
                l.portrait = n.GetValue("portrait");
                l.biomes = SplitList(n.GetValue("biomes")).Select(NormBiome).ToArray();
                l.habitat = ParseEnum(n.GetValue("habitat"), Habitat.Ground);
                l.temperament = ParseEnum(n.GetValue("temperament"), Temperament.Skittish);
                l.activeTime = ParseEnum(n.GetValue("activeTime"), ActivityTime.Any);
                n.TryGetValue("rarity", ref l.rarity);
                n.TryGetValue("territoryChance", ref l.territoryChance);
                string g = n.GetValue("groupSize");
                if (!string.IsNullOrEmpty(g))
                {
                    var parts = SplitList(g);
                    int a; if (parts.Length > 0 && int.TryParse(parts[0], out a)) l.minGroup = l.maxGroup = Math.Max(1, a);
                    int b2; if (parts.Length > 1 && int.TryParse(parts[1], out b2)) l.maxGroup = Math.Max(l.minGroup, b2);
                }
                n.TryGetValue("size", ref l.size);
                n.TryGetValue("speed", ref l.speed);
                n.TryGetValue("fleeSpeed", ref l.fleeSpeed);
                n.TryGetValue("fleeDistance", ref l.fleeDistance);
                n.TryGetValue("alertDistance", ref l.alertDistance);
                n.TryGetValue("observeRange", ref l.observeRange);
                n.TryGetValue("minAltitude", ref l.minAltitude);
                n.TryGetValue("maxAltitude", ref l.maxAltitude);
                n.TryGetValue("scienceValue", ref l.scienceValue);
                if (l.maxAltitude < l.minAltitude) l.maxAltitude = l.minAltitude;
                l.look = ProceduralLook.Parse(n.GetNode("PROCEDURAL"));
                l.model = ModelInfo.Parse(n.GetNode("MODEL"));
                l.flight = FlightInfo.Parse(n.GetNode("FLIGHT"));
                if (l.habitat == Habitat.Flyer && l.flight == null) l.flight = new FlightInfo();
                l.sleep = SleepInfo.Parse(n.GetNode("SLEEP"));
                l.attack = AttackInfo.Parse(n.GetNode("ATTACK"));
                l.mount = MountInfo.Parse(n.GetNode("MOUNT"));
                l.burrow = BurrowInfo.Parse(n.GetNode("BURROW"));
                l.flyby = FlybyInfo.Parse(n.GetNode("FLYBY"));
                l.sounds = SoundInfo.Parse(n.GetNode("SOUNDS"));
                l.throwing = ThrowInfo.Parse(n.GetNode("THROW"));
                l.roar = RoarInfo.Parse(n.GetNode("ROAR"));
                l.light = LightInfo.Parse(n.GetNode("LIGHT"));
                l.leap = LeapInfo.Parse(n.GetNode("LEAP"));
                l.colony = ColonyInfo.Parse(n.GetNode("COLONY"));
                l.metamorph = MetamorphInfo.Parse(n.GetNode("METAMORPHOSIS"));
                {
                    var sd = SplitList(n.GetValue("spawnDistance")); float a1, a2;
                    if (sd.Length > 0 && float.TryParse(sd[0], out a1)) l.spawnDistanceMin = l.spawnDistanceMax = Math.Max(0f, a1);
                    if (sd.Length > 1 && float.TryParse(sd[1], out a2)) l.spawnDistanceMax = Math.Max(l.spawnDistanceMin, a2);
                }
                n.TryGetValue("despawnDistance", ref l.despawnDistance);
                n.TryGetValue("maxWadeDepth", ref l.maxWadeDepth);
                n.TryGetValue("farSpawnChance", ref l.farSpawnChance);
                l.farSpawnMessage = n.GetValue("farSpawnMessage") ?? "";
                if (l.spawnDistanceMax > 0f && l.despawnDistance < l.spawnDistanceMax + 500f) l.despawnDistance = l.spawnDistanceMax + 1500f;
                l.burst = BurstInfo.Parse(n.GetNode("BURST"));
                foreach (ConfigNode en in n.GetNodes("EMITTER")) l.emitters.Add(EmitterInfo.Parse(en));
                foreach (ConfigNode pn in n.GetNodes("PLUME")) l.plumes.Add(PlumeInfo.Parse(pn));
                n.TryGetValue("unique", ref l.unique);
                n.TryGetValue("sessile", ref l.sessile);
                l.guideCategory = n.GetValue("guideCategory");
                n.TryGetValue("seafloor", ref l.seafloor);
                n.TryGetValue("amphibious", ref l.amphibious);
                n.TryGetValue("walkOnWater", ref l.walkOnWater);
                n.TryGetValue("swims", ref l.swims);
                n.TryGetValue("swimSpeed", ref l.swimSpeed);
                n.TryGetValue("waterline", ref l.waterline);
                n.TryGetValue("groupSpread", ref l.groupSpread);
                n.TryGetValue("circling", ref l.circling);
                n.TryGetValue("turnRate", ref l.turnRate);
                n.TryGetValue("maxClimbRate", ref l.maxClimbRate);
                string cc = n.GetValue("cruiseChangeTime");
                if (!string.IsNullOrEmpty(cc))
                {
                    var parts2 = SplitList(cc); float a2, b3;
                    if (parts2.Length > 0 && float.TryParse(parts2[0], out a2)) l.cruiseChangeMin = l.cruiseChangeMax = Math.Max(1f, a2);
                    if (parts2.Length > 1 && float.TryParse(parts2[1], out b3)) l.cruiseChangeMax = Math.Max(l.cruiseChangeMin, b3);
                }
                l.diet = SplitList(n.GetValue("diet"));
                l.lifeStageOf = n.GetValue("lifeStageOf");
                l.lifeStage = n.GetValue("lifeStage") ?? "";
                if (l.burst != null) l.sessile = true;
                Lifeforms[l.name] = l;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_FOSSIL"))
            {
                ConfigNode n = url.config;
                var f = new FossilDef();
                f.name = n.GetValue("name");
                if (string.IsNullOrEmpty(f.name)) { Problem("XENO_FOSSIL without name in " + url.url); continue; }
                f.body = n.GetValue("body");
                f.celestialBody = FindBody(f.body);
                if (f.celestialBody == null) { XenoLog.Info("Fossil " + f.name + " skipped: body '" + f.body + "' not installed"); continue; }
                f.displayName = n.GetValue("displayName") ?? f.name;
                f.description = n.GetValue("description") ?? "";
                f.silhouette = n.GetValue("silhouette");
                f.portrait = n.GetValue("portrait");
                f.kind = n.GetValue("kind");
                f.biomes = SplitList(n.GetValue("biomes")).Select(NormBiome).ToArray();
                f.evidenceFor = SplitList(n.GetValue("evidenceFor"));
                n.TryGetValue("evidence", ref f.evidence);
                f.ageText = n.GetValue("age") ?? "";
                f.form = ParseEnum(n.GetValue("form"), FossilForm.Shell);
                n.TryGetValue("color", ref f.color);
                n.TryGetValue("rarity", ref f.rarity);
                n.TryGetValue("size", ref f.size);
                if (n.HasValue("requiredTrait")) f.requiredTrait = n.GetValue("requiredTrait");
                n.TryGetValue("minLevel", ref f.minLevel);
                n.TryGetValue("studyTime", ref f.studyTime);
                n.TryGetValue("scienceValue", ref f.scienceValue);
                f.model = ModelInfo.Parse(n.GetNode("MODEL"));
                n.TryGetValue("landmark", ref f.landmark); n.TryGetValue("unique", ref f.unique);
                if (n.HasValue("searchCenter"))
                {
                    var sc = SplitList(n.GetValue("searchCenter")); double la, lo;
                    if (sc.Length > 1 && double.TryParse(sc[0], out la) && double.TryParse(sc[1], out lo)) { f.searchLat = la; f.searchLon = lo; }
                }
                n.TryGetValue("searchRadius", ref f.searchRadius); n.TryGetValue("footprint", ref f.footprint);
                n.TryGetValue("loadRange", ref f.loadRange); n.TryGetValue("discoverRange", ref f.discoverRange);
                n.TryGetValue("studyRange", ref f.studyRange); n.TryGetValue("beaconSize", ref f.beaconSize); n.TryGetValue("heading", ref f.heading);
                f.discoverMessage = n.GetValue("discoverMessage") ?? "";
                foreach (string sp in n.GetValues("studyPoint"))
                {
                    var c = SplitList(sp); float x, y, z;
                    if (c.Length > 2 && float.TryParse(c[0], out x) && float.TryParse(c[1], out y) && float.TryParse(c[2], out z)) f.studyPoints.Add(new Vector3(x, y, z));
                }
                Fossils[f.name] = f;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_PANSPERMIA"))
            {
                ConfigNode n = url.config;
                var p = new PanspermiaDef();
                p.name = n.GetValue("name");
                if (string.IsNullOrEmpty(p.name)) { Problem("XENO_PANSPERMIA without name in " + url.url); continue; }
                p.displayName = n.GetValue("displayName") ?? p.name;
                p.description = n.GetValue("description") ?? "";
                p.sourceClade = n.GetValue("sourceClade");
                p.targetBiosphere = n.GetValue("targetBiosphere");
                p.targetClade = n.GetValue("targetClade");
                p.microbeEvidence = SplitList(n.GetValue("microbeEvidence"));
                p.mechanism = n.GetValue("mechanism") ?? "Impact ejecta";
                p.ageText = n.GetValue("age") ?? "";
                n.TryGetValue("revealThreshold", ref p.revealThreshold);
                Panspermia[p.name] = p;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_LAIR"))
            {
                ConfigNode n = url.config;
                var d = new LairDef();
                d.name = n.GetValue("name"); d.body = n.GetValue("body");
                if (string.IsNullOrEmpty(d.name) || string.IsNullOrEmpty(d.body)) { Problem("XENO_LAIR missing name/body in " + url.url); continue; }
                d.celestialBody = FindBody(d.body);
                if (d.celestialBody == null) { XenoLog.Info("Lair " + d.name + " skipped: body '" + d.body + "' not installed"); continue; }
                d.displayName = n.GetValue("displayName") ?? d.name;
                d.description = n.GetValue("description") ?? "";
                d.model = n.GetValue("model");
                d.resident = n.GetValue("resident");
                n.TryGetValue("latitude", ref d.latitude); n.TryGetValue("longitude", ref d.longitude);
                n.TryGetValue("searchRadius", ref d.searchRadius); n.TryGetValue("minAltitude", ref d.minAltitude); n.TryGetValue("maxAltitude", ref d.maxAltitude);
                n.TryGetValue("footprint", ref d.footprint); n.TryGetValue("sink", ref d.sink); n.TryGetValue("heading", ref d.heading);
                n.TryGetValue("loadRange", ref d.loadRange); n.TryGetValue("residentRange", ref d.residentRange); n.TryGetValue("discoverRange", ref d.discoverRange);
                n.TryGetValue("leash", ref d.leash); n.TryGetValue("waypoint", ref d.waypoint);
                n.TryGetValue("scienceValue", ref d.scienceValue);
                d.surveyText = n.GetValue("surveyText") ?? "";
                d.discoverMessage = n.GetValue("discoverMessage") ?? "";
                n.TryGetValue("anomaly", ref d.anomaly);
                n.TryGetValue("underwater", ref d.underwater); n.TryGetValue("surveyRadius", ref d.surveyRadius);
                n.TryGetValue("lightsNightOnly", ref d.lightsNightOnly); n.TryGetValue("glowPulse", ref d.glowPulse);
                n.TryGetValue("dayGlow", ref d.dayGlow); n.TryGetValue("swayAngle", ref d.swayAngle);
                n.TryGetValue("detailRange", ref d.detailRange);
                n.TryGetValue("detailRangeSmall", ref d.detailRangeSmall); n.TryGetValue("catalogueScience", ref d.catalogueScience);
                foreach (ConfigNode fn_ in n.GetNodes("FLOCK"))
                {
                    var lf = new LairFlock { lifeform = fn_.GetValue("lifeform") };
                    var sz = SplitList(fn_.GetValue("size") ?? "");
                    int a_; if (sz.Length > 0 && int.TryParse(sz[0], out a_)) lf.min = lf.max = Math.Max(0, a_);
                    int b_; if (sz.Length > 1 && int.TryParse(sz[1], out b_)) lf.max = Math.Max(lf.min, b_);
                    fn_.TryGetValue("spread", ref lf.spread); lf.at = fn_.GetValue("at"); fn_.TryGetValue("leash", ref lf.leash);
                    if (!string.IsNullOrEmpty(lf.lifeform)) d.flocks.Add(lf);
                }
                if (n.HasNode("FOREST")) d.forest = ForestDef.Parse(n.GetNode("FOREST"), d.name);
                n.TryGetValue("clearScatters", ref d.clearScatters); n.TryGetValue("scatterClearRadius", ref d.scatterClearRadius);
                if (n.HasValue("doorOpenAnim")) d.doorOpenAnim = n.GetValue("doorOpenAnim");
                if (n.HasValue("doorCloseAnim")) d.doorCloseAnim = n.GetValue("doorCloseAnim");
                if (n.HasValue("entrance")) d.entrance = n.GetValue("entrance");
                if (n.HasValue("den")) d.den = n.GetValue("den");
                if (n.HasValue("pen")) d.pen = n.GetValue("pen");
                d.flock = n.GetValue("flock");
                string g = n.GetValue("flockSize");
                if (!string.IsNullOrEmpty(g))
                {
                    var parts = SplitList(g);
                    int a; if (parts.Length > 0 && int.TryParse(parts[0], out a)) d.flockMin = d.flockMax = Math.Max(0, a);
                    int b2; if (parts.Length > 1 && int.TryParse(parts[1], out b2)) d.flockMax = Math.Max(d.flockMin, b2);
                }
                Lairs[d.name] = d;
            }

            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("XENO_FEATURE"))
            {
                FeatureDef f = FeatureDef.Parse(url.config);
                if (f == null) { Problem("XENO_FEATURE missing name/body in " + url.url); continue; }
                f.url = url.url;
                f.celestialBody = FindBody(f.body);
                if (f.celestialBody == null) { XenoLog.Info("Feature " + f.name + " skipped: body '" + f.body + "' not installed"); continue; }
                f.biomes = SplitList(url.config.GetValue("biomes")).Select(NormBiome).ToArray();
                Features[f.name] = f;
            }

            // other mods' microbes (MicrobiologyExpansion); harmless when none are installed
            foreach (UrlDir.UrlConfig url in GameDatabase.Instance.GetConfigs("MICROBE"))
            {
                ConfigNode n = url.config;
                var m = new MicrobeDef();
                m.name = n.GetValue("name");
                if (string.IsNullOrEmpty(m.name)) continue;
                m.category = (n.GetValue("category") ?? "Unknown").Trim();
                m.homePlanet = (n.GetValue("homePlanet") ?? "").Trim();
                m.flavorText = n.GetValue("flavorText") ?? "";
                m.icon = n.GetValue("icon");
                m.hazard = n.GetValue("hazardLevel") ?? "Safe";
                m.situation = n.GetValue("situation") ?? "Any";
                m.biomes = SplitList(n.GetValue("biomes"));
                m.consumes = SplitList(n.GetValue("trophicRelations"));
                n.TryGetValue("scienceValue", ref m.scienceValue);
                Microbes[m.name] = m;
            }

            Link();
            LoadTextures();
            Loaded = true;
            XenoLog.Info(string.Format("Database: {0} biospheres, {1} clades, {2} lifeforms, {3} fossils, {4} panspermia events, {5} lairs, {6} microbes placed, {7} problems",
                Biospheres.Count, Clades.Count, Lifeforms.Count, Fossils.Count, Panspermia.Count, Lairs.Count, Microbes.Values.Count(m => m.parentClade != null), Problems.Count));
        }

        static void Link()
        {
            foreach (var f in Features.Values)
                if (!string.IsNullOrEmpty(f.attracts) && !Lifeforms.TryGetValue(f.attracts, out f.attractDef))
                    XenoLog.Info("Feature " + f.name + ": attracted species '" + f.attracts + "' not loaded");
            // Clades: drop those whose biosphere is missing, then wire parents.
            foreach (var c in Clades.Values.ToList())
            {
                if (string.IsNullOrEmpty(c.biosphere) || !Biospheres.ContainsKey(c.biosphere))
                {
                    if (!string.IsNullOrEmpty(c.biosphere)) XenoLog.Info("Clade " + c.name + " skipped: biosphere '" + c.biosphere + "' not loaded");
                    else Problem("Clade " + c.name + " has no biosphere");
                    Clades.Remove(c.name);
                }
            }
            foreach (var c in Clades.Values)
            {
                if (string.IsNullOrEmpty(c.parent)) continue;
                CladeDef p;
                if (Clades.TryGetValue(c.parent, out p) && p.biosphere == c.biosphere) { c.parentClade = p; p.childClades.Add(c); }
                else Problem("Clade " + c.name + ": parent '" + c.parent + "' not found in same biosphere");
            }
            // cycle guard + depth
            foreach (var c in Clades.Values)
            {
                int d = 0; var cur = c.parentClade; var seen = new HashSet<CladeDef> { c };
                while (cur != null) { if (!seen.Add(cur)) { Problem("Clade cycle at " + c.name); c.parentClade.childClades.Remove(c); c.parentClade = null; d = 0; break; } d++; cur = cur.parentClade; }
                c.depth = d;
            }
            foreach (var b in Biospheres.Values)
            {
                if (string.IsNullOrEmpty(b.rootClade) || !Clades.ContainsKey(b.rootClade))
                {
                    // infer: first parentless clade of this biosphere
                    var root = Clades.Values.FirstOrDefault(c => c.biosphere == b.name && c.parentClade == null);
                    if (root != null) b.rootClade = root.name;
                    else Problem("Biosphere " + b.name + " has no root clade");
                }
            }
            foreach (var l in Lifeforms.Values.ToList())
            {
                CladeDef c;
                if (!string.IsNullOrEmpty(l.clade) && Clades.TryGetValue(l.clade, out c)) { l.parentClade = c; c.species.Add(l); }
                else { Problem("Lifeform " + l.name + ": clade '" + l.clade + "' not found; removed"); Lifeforms.Remove(l.name); }
            }
            foreach (var p in Panspermia.Values.ToList())
            {
                Clades.TryGetValue(p.sourceClade ?? "", out p.source);
                Biospheres.TryGetValue(p.targetBiosphere ?? "", out p.target);
                if (p.source == null || p.target == null) { XenoLog.Info("Panspermia " + p.name + " skipped (source clade or target biosphere not loaded)"); Panspermia.Remove(p.name); continue; }
                if (!string.IsNullOrEmpty(p.targetClade) && (!Clades.TryGetValue(p.targetClade, out p.targetCladeDef) || p.targetCladeDef.biosphere != p.target.name))
                { Problem("Panspermia " + p.name + ": targetClade '" + p.targetClade + "' not found in " + p.target.name); p.targetCladeDef = null; }
                if (p.targetCladeDef == null) Clades.TryGetValue(p.target.rootClade ?? "", out p.targetCladeDef);
            }
            foreach (var l in Lifeforms.Values)
            {
                if (string.IsNullOrEmpty(l.lifeStageOf)) continue;
                if (Lifeforms.TryGetValue(l.lifeStageOf, out l.adultDef)) l.adultDef.juveniles.Add(l);
                else Problem("Lifeform " + l.name + ": lifeStageOf '" + l.lifeStageOf + "' not found");
            }
            foreach (var l in Lifeforms.Values)
            {
                if (l.metamorph == null) continue;
                if (!Lifeforms.TryGetValue(l.metamorph.into, out l.metamorph.intoDef)) { Problem("Lifeform " + l.name + ": METAMORPHOSIS into '" + l.metamorph.into + "' not found"); l.metamorph = null; }
            }
            foreach (var l in Lifeforms.Values)
            {
                if (l.colony == null) continue;
                if (Lifeforms.TryGetValue(l.colony.species, out l.colony.def) && l.colony.def != l) l.colony.def.colonyHost = l;
                else { Problem("Lifeform " + l.name + ": COLONY species '" + l.colony.species + "' not found"); l.colony = null; }
            }
            LinkMicrobes();
            foreach (var d in Lairs.Values.ToList())
            {
                if (!string.IsNullOrEmpty(d.resident) && !Lifeforms.TryGetValue(d.resident, out d.residentDef)) Problem("Lair " + d.name + ": resident '" + d.resident + "' not found");
                if (!string.IsNullOrEmpty(d.flock) && !Lifeforms.TryGetValue(d.flock, out d.flockDef)) Problem("Lair " + d.name + ": flock '" + d.flock + "' not found");
                foreach (var lf in d.flocks) if (!Lifeforms.TryGetValue(lf.lifeform, out lf.def)) Problem("Lair " + d.name + ": FLOCK lifeform '" + lf.lifeform + "' not found");
                if (d.forest != null) { var dn = d.name; d.forest.Link(id => { LifeformDef x; if (Lifeforms.TryGetValue(id, out x)) return x; Problem("Lair " + dn + ": FOREST lifeform '" + id + "' not found"); return null; }); }
            }
            foreach (var f in Fossils.Values)
                foreach (string e in f.evidenceFor)
                    if (!Clades.ContainsKey(e) && !Panspermia.ContainsKey(e))
                        Problem("Fossil " + f.name + ": evidenceFor '" + e + "' is not a known clade or panspermia event");
        }

        /// <summary>
        /// Places each microbe on one clade: an explicit `microbes =` listing wins, then the deepest clade of the
        /// microbe's home-world biosphere whose `microbeCategories` match, then the biosphere's `microbeClade`.
        /// Debris and abiotic "Unknown" entries are never placed unless listed explicitly.
        /// </summary>
        static void LinkMicrobes()
        {
            if (Microbes.Count == 0) return;
            foreach (var c in Clades.Values)
                foreach (string nm in c.microbeNames)
                {
                    MicrobeDef m;
                    if (!Microbes.TryGetValue(nm, out m)) { XenoLog.Info("Clade " + c.name + ": microbe '" + nm + "' not installed"); continue; }
                    if (m.parentClade != null) { Problem("Microbe '" + nm + "' is listed by both " + m.parentClade.name + " and " + c.name); continue; }
                    m.parentClade = c; c.microbes.Add(m);
                }
            foreach (var m in Microbes.Values)
            {
                if (m.parentClade != null || !m.IsLife) continue;
                BiosphereDef bio = Biospheres.Values.FirstOrDefault(b => string.Equals(b.body, m.homePlanet, StringComparison.OrdinalIgnoreCase));
                if (bio == null) continue;
                CladeDef best = null;
                foreach (var c in Clades.Values)
                    if (c.biosphere == bio.name && c.microbeCategories.Any(k => string.Equals(k, m.category, StringComparison.OrdinalIgnoreCase)))
                        if (best == null || c.depth > best.depth) best = c;
                if (best == null && !string.IsNullOrEmpty(bio.microbeClade)) Clades.TryGetValue(bio.microbeClade, out best);
                if (best != null) { m.parentClade = best; best.microbes.Add(m); }
            }
        }

        public static IEnumerable<MicrobeDef> AllMicrobesUnder(CladeDef c)
        {
            foreach (var m in c.microbes) yield return m;
            foreach (var ch in c.childClades) foreach (var m in AllMicrobesUnder(ch)) yield return m;
        }

        static void LoadTextures()
        {
            foreach (var m in Microbes.Values)
                if (m.parentClade != null && !string.IsNullOrEmpty(m.icon)) m.iconTex = GameDatabase.Instance.GetTexture(m.icon, false);
            // species/fossil portraits and silhouettes load on demand (XenoTextures)
        }

        // ---- queries ----
        public static BiosphereDef BiosphereFor(CelestialBody body)
        {
            if (body == null) return null;
            foreach (var b in Biospheres.Values) if (b.body == body.name || b.body == body.bodyName) return b;
            return null;
        }

        public static IEnumerable<LifeformDef> SpeciesOn(CelestialBody body)
        {
            return Lifeforms.Values.Where(l => l.celestialBody == body);
        }

        public static List<FeatureDef> FeaturesOn(CelestialBody body)
        {
            return Features.Values.Where(f => f.celestialBody == body).ToList();
        }

        public static IEnumerable<FossilDef> FossilsOn(CelestialBody body)
        {
            return Fossils.Values.Where(f => f.celestialBody == body);
        }

        public static IEnumerable<LifeformDef> AllSpeciesUnder(CladeDef c)
        {
            foreach (var s in c.species) yield return s;
            foreach (var ch in c.childClades) foreach (var s in AllSpeciesUnder(ch)) yield return s;
        }

        public static IEnumerable<CladeDef> CladesOf(BiosphereDef b)
        {
            return Clades.Values.Where(c => c.biosphere == b.name);
        }
    }

    [KSPAddon(KSPAddon.Startup.MainMenu, true)]
    public class XenoLoader : MonoBehaviour
    {
        void Start()
        {
            XenoSettings.Load();
            XenoDatabase.Load();
            DontDestroyOnLoad(this);
        }
    }
}
