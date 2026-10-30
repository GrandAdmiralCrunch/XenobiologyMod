using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    static class PartUtil
    {
        /// <summary>Draws EC for dt seconds; returns false when the vessel can't supply it.</summary>
        public static bool DrawEC(Part p, double perSecond, double dt)
        {
            if (perSecond <= 0) return true;
            double want = perSecond * dt;
            double got = p.RequestResource("ElectricCharge", want);
            return got >= want * 0.95;
        }

        public static string Biome(CelestialBody b, double lat, double lon) { return Geo.Biome(b, lat, lon); }

        public static bool Underwater(CreatureController c)
        {
            return c.def.habitat == Habitat.Underwater || (c.def.habitat == Habitat.Water && c.alt < -0.3) || c.alt < -0.5;
        }
    }

    // =====================================================================================================
    /// <summary>
    /// Xenofauna Tracking Camera. A motorised telephoto turret that finds wildlife within line of sight,
    /// swings round to follow it, and photographs it (discovering the species and storing data).
    /// Transforms "pan" (rotates about the mount normal, Unity local +Z) and "tilt" (rotates about X;
    /// the lens looks along local +Y at rest).
    /// </summary>
    public class ModuleXenoTracker : PartModule
    {
        [KSPField] public float range = 1500f;              // metres
        [KSPField] public float maxHeight = 6000f;          // above terrain; the turret can't resolve anything higher up
        [KSPField] public float ecPerSecond = 0.06f;
        [KSPField] public float lockTime = 3f;              // seconds the target must stay in view to get a usable photo
        [KSPField] public float scienceMultiplier = 0.6f;   // photos are worth less than field notes
        [KSPField] public float slewRate = 60f;             // deg/s
        [KSPField] public float minTilt = -20f, maxTilt = 100f;
        [KSPField] public string panTransform = "pan";
        [KSPField] public string tiltTransform = "tilt";
        [KSPField] public string lensTransform = "lens";
        [KSPField] public string experimentID = "xenoTelephoto";

        [KSPField(isPersistant = true, guiActive = true, guiActiveEditor = true, guiName = "Auto-track"),
         UI_Toggle(disabledText = "Off", enabledText = "On")]
        public bool autoTrack = true;

        [KSPField(guiActive = true, guiName = "Camera")]
        public string status = "idle";

        Transform pan, tilt, lens;
        Quaternion panRest, tiltRest;
        CreatureController target;
        float lockTimer, scanTimer;
        readonly HashSet<string> shot = new HashSet<string>();   // species|biome photographed this flight

        public override void OnStart(StartState state)
        {
            pan = part.FindModelTransform(panTransform);
            tilt = part.FindModelTransform(tiltTransform);
            lens = part.FindModelTransform(lensTransform) ?? tilt ?? part.transform;
            if (pan != null) panRest = pan.localRotation;
            if (tilt != null) tiltRest = tilt.localRotation;
        }

        public override string GetInfo()
        {
            return string.Format("Photographs wildlife in line of sight.\n<b>Range:</b> {0:F0} m\n<b>Works up to:</b> {1:F0} m above ground\n<b>Power:</b> {2:F2} EC/s while tracking\n<b>Science:</b> {3:P0} of field notes",
                range, maxHeight, ecPerSecond, scienceMultiplier);
        }

        bool InView(CreatureController c, Vector3 eye, out float dist)
        {
            Vector3 p = c.transform.position + c.transform.up * (c.def.size * 0.25f);
            Vector3 d = p - eye; dist = d.magnitude;
            if (dist > range || c.state == CreatureState.Underground) return false;
            bool eyeUnder = vessel.mainBody.GetAltitude(eye) < -0.3;
            if (PartUtil.Underwater(c) != eyeUnder) return false;      // the water surface blocks the view
            // terrain blocks the view (layer 15); ignore hits right next to the creature
            RaycastHit hit;
            if (Physics.Raycast(eye, d.normalized, out hit, dist - Mathf.Max(1f, c.def.size * 0.5f), Geo.SceneryMask, QueryTriggerInteraction.Ignore))
                return false;
            return true;
        }

        CreatureController PickTarget(Vector3 eye)
        {
            var sp = XenoSpawner.Instance; if (sp == null) return null;
            var scen = XenoScenario.Instance;
            CreatureController best = null; float bestScore = float.MaxValue;
            foreach (var c in sp.Creatures)
            {
                if (c == null || c.Ridden) continue;
                float d;
                if (!InView(c, eye, out d)) continue;
                bool known = scen != null && scen.IsDiscovered(c.def);
                bool done = shot.Contains(c.def.name + "|" + c.biome);
                float score = d + (known ? 2000f : 0f) + (done ? 4000f : 0f);
                if (score < bestScore) { bestScore = score; best = c; }
            }
            return best;
        }

        [KSPEvent(guiActive = true, guiName = "Photograph Target", active = true)]
        public void Photograph()
        {
            if (target == null) { ScreenMessages.PostScreenMessage("The camera has nothing in its sights.", 3f, ScreenMessageStyle.UPPER_CENTER); return; }
            TakePhoto(target, true);
        }

        void TakePhoto(CreatureController c, bool manual)
        {
            string key = c.def.name + "|" + c.biome;
            if (!manual && shot.Contains(key)) return;
            shot.Add(key);
            string biomeName = ScienceUtil.GetBiomedisplayName(vessel.mainBody, c.biome);
            bool isNew = XenoScenario.Instance != null && XenoScenario.Instance.RecordObservation(c.def, vessel.vesselName + " (tracking camera)", biomeName);
            if (!isNew) ScreenMessages.PostScreenMessage("Camera: photographed " + c.def.displayName, 3f, ScreenMessageStyle.UPPER_LEFT);
            XenoScience.Collect(this, experimentID, c.def.name, c.def.displayName, c.def.scienceValue * scienceMultiplier, c.biome,
                "Telephoto images of " + c.def.displayName + ". " + c.def.description, "Photos stored");
        }

        public void Update()
        {
            if (!HighLogic.LoadedSceneIsFlight || vessel == null || !vessel.loaded) return;
            scanTimer -= Time.deltaTime;
            Vector3 eye = lens != null ? lens.position : part.transform.position;

            if (scanTimer <= 0f)
            {
                scanTimer = 0.5f;
                double h = vessel.altitude - (vessel.mainBody.ocean ? Math.Max(vessel.terrainAltitude, 0) : vessel.terrainAltitude);
                if (h > maxHeight) { target = null; status = "too high"; }
                else if (!PartUtil.DrawEC(part, ecPerSecond, 0.5)) { target = null; status = "no power"; }
                else
                {
                    float d;
                    if (target == null || !InView(target, eye, out d)) { target = PickTarget(eye); lockTimer = 0f; }
                    if (target == null) status = "scanning";
                    else
                    {
                        float dist = (target.transform.position - eye).magnitude;
                        bool known = XenoScenario.Instance != null && XenoScenario.Instance.IsDiscovered(target.def);
                        status = string.Format("{0}, {1:F0} m", known ? target.def.displayName : "unidentified lifeform", dist);
                    }
                }
            }

            if (target != null)
            {
                lockTimer += Time.deltaTime;
                if (autoTrack && lockTimer >= lockTime) TakePhoto(target, false);
                Aim(target.transform.position + target.transform.up * (target.def.size * 0.25f));
            }
            else Aim(Vector3.zero, true);
        }

        void Aim(Vector3 worldTarget, bool rest = false)
        {
            if (pan == null || tilt == null) return;
            float step = slewRate * Time.deltaTime;
            Quaternion panGoal = panRest, tiltGoal = tiltRest;
            if (!rest)
            {
                // pan: rotate about the parent's local Z (mount normal) so the boresight plane contains the target
                Vector3 d = pan.parent.InverseTransformDirection(worldTarget - pan.position);
                Vector3 dr = Quaternion.Inverse(panRest) * d;
                float p = Mathf.Atan2(-dr.x, dr.y) * Mathf.Rad2Deg;
                panGoal = panRest * Quaternion.AngleAxis(p, Vector3.forward);
                // tilt: in the (already panned) frame the target lies in the Y-Z plane
                Quaternion panNow = pan.localRotation;
                pan.localRotation = panGoal;
                Vector3 dt = Quaternion.Inverse(tiltRest) * tilt.parent.InverseTransformDirection(worldTarget - tilt.position);
                pan.localRotation = panNow;
                float t = Mathf.Clamp(Mathf.Atan2(dt.z, dt.y) * Mathf.Rad2Deg, minTilt, maxTilt);   // +90 = straight out from the hull
                tiltGoal = tiltRest * Quaternion.AngleAxis(t, Vector3.right);
            }
            pan.localRotation = Quaternion.RotateTowards(pan.localRotation, panGoal, step);
            tilt.localRotation = Quaternion.RotateTowards(tilt.localRotation, tiltGoal, step);
        }
    }

    // =====================================================================================================
    /// <summary>
    /// Hydrophone. Once submerged it listens for aquatic life. It hears creatures that are swimming nearby,
    /// and also surveys the territory cells around it out to `range`, picking up the calls of species that
    /// live there even though they are too far away to be simulated.
    /// </summary>
    public class ModuleXenoHydrophone : PartModule
    {
        [KSPField] public float range = 4000f;
        [KSPField] public float minDepth = 1.5f;            // the sensor must be at least this far below the surface
        [KSPField] public float ecPerSecond = 0.12f;
        [KSPField] public float scanInterval = 6f;
        [KSPField] public int bearings = 16;
        [KSPField] public float ringStep = 500f;
        [KSPField] public float scienceMultiplier = 0.5f;
        [KSPField] public string experimentID = "xenoHydrophone";
        [KSPField] public string lightTransform = "status_light";

        [KSPField(isPersistant = true, guiActive = true, guiActiveEditor = true, guiName = "Listening"),
         UI_Toggle(disabledText = "Off", enabledText = "On")]
        public bool listening = true;

        [KSPField(guiActive = true, guiName = "Hydrophone")]
        public string status = "dry";

        [KSPField(guiActive = true, guiName = "Strongest contact")]
        public string contact = "—";

        float timer;
        readonly HashSet<string> heard = new HashSet<string>();   // species|biome recorded this flight
        Transform light;

        public override void OnStart(StartState state)
        {
            light = part.FindModelTransform(lightTransform);
            timer = 1f;
        }

        public override string GetInfo()
        {
            return string.Format("Listens for aquatic life while submerged.\n<b>Range:</b> {0:F1} km\n<b>Minimum depth:</b> {1:F1} m\n<b>Power:</b> {2:F2} EC/s\n<b>Science:</b> {3:P0} of field notes",
                range / 1000f, minDepth, ecPerSecond, scienceMultiplier);
        }

        struct Contact { public LifeformDef def; public double dist, bearing; public string biome; }

        public void Update()
        {
            if (!HighLogic.LoadedSceneIsFlight || vessel == null || !vessel.loaded) return;
            CelestialBody body = vessel.mainBody;
            double depth = -body.GetAltitude(part.transform.position);
            bool wet = body.ocean && depth >= minDepth;
            if (light != null) light.gameObject.SetActive(wet && listening && Mathf.Repeat(Time.time, 2f) < 0.25f);
            timer -= Time.deltaTime;
            if (timer > 0f) return;
            timer = scanInterval;

            if (!listening) { status = "off"; return; }
            if (!body.ocean) { status = "no ocean here"; return; }
            if (!wet) { status = depth > 0 ? string.Format("too shallow ({0:F1} m)", depth) : "out of the water"; return; }
            if (!PartUtil.DrawEC(part, ecPerSecond, scanInterval)) { status = "no power"; return; }

            var contacts = Listen(body);
            status = contacts.Count == 0 ? "listening, no contacts" : contacts.Count + " acoustic contact" + (contacts.Count == 1 ? "" : "s");
            if (contacts.Count == 0) { contact = "—"; return; }
            var best = contacts.OrderBy(c => c.dist).First();
            bool bestKnown = XenoScenario.Instance != null && XenoScenario.Instance.IsDiscovered(best.def);
            contact = string.Format("{0}, {1:F1} km {2}", bestKnown ? best.def.displayName : "unknown signature", best.dist / 1000.0, Geo.CompassName(best.bearing));

            foreach (var c in contacts)
            {
                string key = c.def.name + "|" + c.biome;
                if (heard.Contains(key)) continue;
                heard.Add(key);
                bool isNew = XenoScenario.Instance != null && XenoScenario.Instance.RecordObservation(c.def, vessel.vesselName + " (hydrophone)", ScienceUtil.GetBiomedisplayName(body, c.biome));
                if (!isNew)
                    ScreenMessages.PostScreenMessage(string.Format("Hydrophone: {0}, {1:F1} km {2}", c.def.displayName, c.dist / 1000.0, Geo.CompassName(c.bearing)), 4f, ScreenMessageStyle.UPPER_LEFT);
                XenoScience.Collect(this, experimentID, c.def.name, c.def.displayName, c.def.scienceValue * scienceMultiplier, c.biome,
                    "Hydrophone recordings of " + c.def.displayName + ". " + c.def.description, "Recording stored");
            }
        }

        List<Contact> Listen(CelestialBody body)
        {
            var found = new Dictionary<string, Contact>();
            double lat = vessel.latitude, lon = vessel.longitude;
            // 1) things actually swimming nearby
            var sp = XenoSpawner.Instance;
            if (sp != null)
                foreach (var c in sp.Creatures)
                {
                    if (c == null || c.body != body) continue;
                    if (c.def.habitat != Habitat.Water && c.def.habitat != Habitat.Underwater) continue;
                    double n, e; Geo.Delta(body, lat, lon, c.lat, c.lon, out n, out e);
                    double d = Math.Sqrt(n * n + e * e);
                    if (d > range) continue;
                    Add(found, new Contact { def = c.def, dist = d, bearing = Geo.Bearing(body, lat, lon, c.lat, c.lon), biome = c.biome });
                }
            // 2) acoustic survey of the surrounding territories
            if (sp != null)
                for (double r = ringStep * 0.5; r <= range; r += ringStep)
                    for (int i = 0; i < bearings; i++)
                    {
                        double a = (i + (r / ringStep) * 0.5) / bearings * Math.PI * 2;
                        double la = lat, lo = lon;
                        Geo.Offset(body, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
                        if (Geo.Terrain(body, la, lo) > -2.0) continue;          // land, or too shallow to carry sound
                        foreach (var def in sp.CandidatesAt(body, la, lo))
                        {
                            if (def.habitat != Habitat.Water && def.habitat != Habitat.Underwater) continue;
                            Add(found, new Contact { def = def, dist = r, bearing = a * Geo.Rad2Deg, biome = Geo.Biome(body, la, lo) });
                        }
                    }
            return found.Values.ToList();
        }

        static void Add(Dictionary<string, Contact> found, Contact c)
        {
            Contact old;
            if (!found.TryGetValue(c.def.name, out old) || c.dist < old.dist) found[c.def.name] = c;
        }
    }

    // =====================================================================================================
    /// <summary>
    /// CO-Z Containment Unit. Holds live specimens caught by EVA kerbals (see ModuleXenoFieldKit.CaptureSpecimen).
    /// Specimens need power to stay alive; recovering the vessel turns them into science (living specimens are
    /// worth far more). Implements IScienceDataContainer and saves its specimens as ScienceData nodes, which is
    /// what stock recovery reads.
    /// </summary>
    public class ModuleXenoContainment : PartModule, IScienceDataContainer
    {
        [KSPField] public float capacity = 4f;              // specimen volume units (0.08 x size^3)
        [KSPField] public float maxSpecimenSize = 3.5f;     // metres; anything longer won't go through the hatch
        [KSPField] public float ecPerSpecimen = 0.03f;      // EC/s per living specimen
        [KSPField] public float survivalTime = 60f;         // seconds a specimen survives without power
        [KSPField] public float liveMultiplier = 3f;        // science = scienceValue x this on recovery (alive)
        [KSPField] public float deadMultiplier = 1.2f;
        [KSPField] public string experimentID = "xenoSpecimen";

        [KSPField(guiActive = true, guiActiveEditor = true, guiName = "Specimens")]
        public string status = "empty";

        public class Specimen
        {
            public string species, biome, subjectId, title, catcher;
            public bool alive = true;
            public double caughtUT;
            public float volume, starve;
        }
        public readonly List<Specimen> specimens = new List<Specimen>();

        public static float VolumeOf(LifeformDef d) { return 0.08f * d.size * d.size * d.size; }
        public float Used { get { return specimens.Sum(s => s.volume); } }

        public override string GetInfo()
        {
            return string.Format("Life-supported holding pens for live specimens.\n<b>Capacity:</b> {0:F1} units\n<b>Largest specimen:</b> {1:F1} m (megafauna will not fit)\n<b>Power:</b> {2:F2} EC/s per specimen\n<b>Recovery value:</b> {3:F0}x field notes alive, {4:F1}x dead",
                capacity, maxSpecimenSize, ecPerSpecimen, liveMultiplier, deadMultiplier);
        }

        /// <returns>null if it fits, otherwise the reason it doesn't</returns>
        public string WhyNot(LifeformDef d)
        {
            if (d.unique || d.size > 8f) return "The " + d.displayName + " is megafauna - it will not fit in a CO-Z unit (and would not appreciate the attempt).";
            if (d.size > maxSpecimenSize) return string.Format("The {0} is too big for the containment hatch ({1:F1} m, max {2:F1} m).", d.displayName, d.size, maxSpecimenSize);
            if (Used + VolumeOf(d) > capacity + 1e-4f) return string.Format("Not enough room: {0:F2} units needed, {1:F2} free.", VolumeOf(d), capacity - Used);
            return null;
        }

        public void Store(CreatureController c, string catcher)
        {
            LifeformDef d = c.def;
            ScienceExperiment exp = ResearchAndDevelopment.GetExperiment(experimentID);
            string subjectId = d.name, title = "Live specimen: " + d.displayName;
            if (exp != null)
            {
                ExperimentSituations sit = ScienceUtil.GetExperimentSituation(vessel);
                ScienceSubject subj = ResearchAndDevelopment.GetExperimentSubject(exp, sit, d.name, d.displayName, c.body, c.biome, ScienceUtil.GetBiomedisplayName(c.body, c.biome));
                subj.scienceCap = d.scienceValue * liveMultiplier * subj.subjectValue;
                subjectId = subj.id;
                title = exp.experimentTitle + ": " + d.displayName + " (" + c.body.displayName.LocalizeRemoveGender() + ")";
            }
            specimens.Add(new Specimen { species = d.name, biome = c.biome, subjectId = subjectId, title = title, catcher = catcher, caughtUT = Planetarium.GetUniversalTime(), volume = VolumeOf(d) });
            UpdateStatus();
        }

        void UpdateStatus()
        {
            if (specimens.Count == 0) { status = string.Format("empty (0/{0:F1})", capacity); return; }
            int dead = specimens.Count(s => !s.alive);
            status = string.Format("{0}{1} ({2:F1}/{3:F1})", specimens.Count, dead > 0 ? ", " + dead + " dead" : "", Used, capacity);
        }

        public override void OnStart(StartState state) { UpdateStatus(); }

        public void FixedUpdate()
        {
            if (!HighLogic.LoadedSceneIsFlight || specimens.Count == 0) return;
            int alive = specimens.Count(s => s.alive);
            if (alive == 0) return;
            float dt = TimeWarp.fixedDeltaTime;
            bool powered = PartUtil.DrawEC(part, ecPerSpecimen * alive, dt);
            foreach (var s in specimens)
            {
                if (!s.alive) continue;
                s.starve = powered ? Mathf.Max(0f, s.starve - dt) : s.starve + dt;
                if (s.starve > survivalTime)
                {
                    s.alive = false;
                    LifeformDef d; XenoDatabase.Lifeforms.TryGetValue(s.species, out d);
                    ScreenMessages.PostScreenMessage("<color=#FF8060>CO-Z unit lost power: the " + (d != null ? d.displayName : s.species) + " specimen has died.</color>", 6f, ScreenMessageStyle.UPPER_CENTER);
                    UpdateStatus();
                }
            }
        }

        [KSPEvent(guiActive = true, guiActiveUnfocused = true, externalToEVAOnly = false, unfocusedRange = 6f, guiName = "List Specimens")]
        public void ListSpecimens()
        {
            if (specimens.Count == 0) { ScreenMessages.PostScreenMessage("The CO-Z unit is empty.", 3f, ScreenMessageStyle.UPPER_CENTER); return; }
            string s = string.Join("\n", specimens.Select(x =>
            {
                LifeformDef d; XenoDatabase.Lifeforms.TryGetValue(x.species, out d);
                return (d != null ? d.displayName : x.species) + (x.alive ? "" : " (dead)") + ", caught by " + x.catcher;
            }).ToArray());
            ScreenMessages.PostScreenMessage(s, 6f, ScreenMessageStyle.UPPER_CENTER);
        }

        [KSPEvent(guiActive = true, guiActiveUnfocused = true, externalToEVAOnly = false, unfocusedRange = 6f, guiName = "Release Specimens")]
        public void ReleaseSpecimens()
        {
            if (specimens.Count == 0) return;
            var sp = XenoSpawner.Instance;
            int n = 0;
            foreach (var s in specimens)
            {
                LifeformDef d;
                if (!s.alive || sp == null || !XenoDatabase.Lifeforms.TryGetValue(s.species, out d) || d.celestialBody != vessel.mainBody) continue;
                double la = vessel.latitude, lo = vessel.longitude;
                Geo.Offset(vessel.mainBody, ref la, ref lo, UnityEngine.Random.Range(-6f, 6f), UnityEngine.Random.Range(-6f, 6f));
                var c = sp.Spawn(d, vessel.mainBody, la, lo);
                if (c != null) { c.Startle(UnityEngine.Random.Range(0f, 360f)); n++; }
            }
            ScreenMessages.PostScreenMessage(n > 0 ? n + " specimen(s) released. They do not look back." : "Specimens disposed of.", 4f, ScreenMessageStyle.UPPER_CENTER);
            specimens.Clear();
            UpdateStatus();
        }

        // ---------------------------------------------------------------- persistence (ScienceData nodes are what recovery reads)
        public override void OnLoad(ConfigNode node)
        {
            specimens.Clear();
            foreach (ConfigNode n in node.GetNodes("SPECIMEN"))
            {
                var s = new Specimen();
                s.species = n.GetValue("species"); s.biome = n.GetValue("biome") ?? ""; s.subjectId = n.GetValue("subjectId") ?? s.species;
                s.title = n.GetValue("title") ?? s.species; s.catcher = n.GetValue("catcher") ?? "";
                n.TryGetValue("alive", ref s.alive); n.TryGetValue("caughtUT", ref s.caughtUT); n.TryGetValue("volume", ref s.volume); n.TryGetValue("starve", ref s.starve);
                if (!string.IsNullOrEmpty(s.species)) specimens.Add(s);
            }
            UpdateStatus();
        }

        public override void OnSave(ConfigNode node)
        {
            foreach (var s in specimens)
            {
                ConfigNode n = node.AddNode("SPECIMEN");
                n.AddValue("species", s.species); n.AddValue("biome", s.biome); n.AddValue("subjectId", s.subjectId);
                n.AddValue("title", s.title); n.AddValue("catcher", s.catcher); n.AddValue("alive", s.alive);
                n.AddValue("caughtUT", s.caughtUT); n.AddValue("volume", s.volume); n.AddValue("starve", s.starve);
            }
            foreach (var d in GetData()) d.Save(node.AddNode("ScienceData"));
        }

        // ---------------------------------------------------------------- IScienceDataContainer
        public ScienceData[] GetData()
        {
            var list = new List<ScienceData>();
            foreach (var s in specimens)
            {
                LifeformDef d; XenoDatabase.Lifeforms.TryGetValue(s.species, out d);
                float baseValue = d != null ? d.scienceValue : 10f;
                float amount = baseValue * (s.alive ? liveMultiplier : deadMultiplier);
                list.Add(new ScienceData(amount, 0f, 0f, s.subjectId, s.title + (s.alive ? "" : " (preserved)"), false, part.flightID));
            }
            return list.ToArray();
        }
        public int GetScienceCount() { return specimens.Count; }
        public bool IsRerunnable() { return true; }
        public void ReturnData(ScienceData data) { }
        public void ReviewData() { ListSpecimens(); }
        public void ReviewDataItem(ScienceData data) { ListSpecimens(); }
        public void DumpData(ScienceData data)
        {
            var s = specimens.FirstOrDefault(x => x.subjectId == data.subjectID);
            if (s != null) specimens.Remove(s);
            UpdateStatus();
        }
    }
}
