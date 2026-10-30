using System;
using System.Collections.Generic;
using System.Linq;
using KSP.UI.Screens;
using UnityEngine;

namespace Xenobiology
{
    public enum RevealState { Hidden, Hinted, Revealed }

    public class SpeciesRecord
    {
        public string id;
        public double firstSeenUT;
        public int observations;
        public string discoveredBy = "";
        public string firstBiome = "";
    }

    public class LairRecord
    {
        public string id;
        public double lat, lon, heading;
        public bool discovered;
        public string surveyedBy = "";   // kerbal who first surveyed the inside (empty = not yet)
    }

    public class FossilRecord
    {
        public string id;
        public double firstStudiedUT;
        public int studies;
        public string studiedBy = "";
    }

    /// <summary>
    /// Save-game state: what has been discovered, and derived reveal state of the trees of life.
    /// </summary>
    [KSPScenario(ScenarioCreationOptions.AddToAllGames, GameScenes.FLIGHT, GameScenes.SPACECENTER, GameScenes.TRACKSTATION, GameScenes.EDITOR)]
    public class XenoScenario : ScenarioModule
    {
        public static XenoScenario Instance { get; private set; }

        public readonly Dictionary<string, SpeciesRecord> Species = new Dictionary<string, SpeciesRecord>();
        public readonly Dictionary<string, FossilRecord> Fossils = new Dictionary<string, FossilRecord>();
        public readonly HashSet<string> StudiedSites = new HashSet<string>();
        public readonly HashSet<string> Analysed = new HashSet<string>();   // "species:<name>" / "fossil:<name>" analysed in a lab
        public readonly Dictionary<string, LairRecord> Lairs = new Dictionary<string, LairRecord>();
        readonly HashSet<string> announced = new HashSet<string>();   // clades/panspermia already announced

        // derived
        readonly Dictionary<string, RevealState> cladeState = new Dictionary<string, RevealState>();
        readonly Dictionary<string, int> cladeScore = new Dictionary<string, int>();
        readonly Dictionary<string, RevealState> panState = new Dictionary<string, RevealState>();
        readonly Dictionary<string, int> panScore = new Dictionary<string, int>();

        public static event Action OnKnowledgeChanged;

        public override void OnAwake()
        {
            base.OnAwake();
            Instance = this;
        }

        void OnDestroy() { if (Instance == this) Instance = null; }

        int microbeStamp = -1;
        float microbeTimer;
        void Update()
        {
            // MicrobiologyExpansion discoveries feed the trees of life
            microbeTimer -= Time.unscaledDeltaTime;
            if (microbeTimer > 0f) return;
            microbeTimer = 2f;
            if (!MicrobeBridge.Installed || !XenoDatabase.Loaded) return;
            MicrobeBridge.Poll(false);
            int st = MicrobeBridge.Stamp;
            if (st != microbeStamp) { bool first = microbeStamp < 0; microbeStamp = st; Recompute(!first); }
        }

        public override void OnLoad(ConfigNode node)
        {
            Species.Clear(); Fossils.Clear(); StudiedSites.Clear(); announced.Clear(); Lairs.Clear(); Analysed.Clear();
            foreach (ConfigNode n in node.GetNodes("SPECIES"))
            {
                var r = new SpeciesRecord { id = n.GetValue("id") };
                if (string.IsNullOrEmpty(r.id)) continue;
                n.TryGetValue("firstSeenUT", ref r.firstSeenUT);
                n.TryGetValue("observations", ref r.observations);
                r.discoveredBy = n.GetValue("discoveredBy") ?? "";
                r.firstBiome = n.GetValue("firstBiome") ?? "";
                Species[r.id] = r;
            }
            foreach (ConfigNode n in node.GetNodes("FOSSIL"))
            {
                var r = new FossilRecord { id = n.GetValue("id") };
                if (string.IsNullOrEmpty(r.id)) continue;
                n.TryGetValue("firstStudiedUT", ref r.firstStudiedUT);
                n.TryGetValue("studies", ref r.studies);
                r.studiedBy = n.GetValue("studiedBy") ?? "";
                Fossils[r.id] = r;
            }
            foreach (ConfigNode n in node.GetNodes("LAIR"))
            {
                var r = new LairRecord { id = n.GetValue("id") };
                if (string.IsNullOrEmpty(r.id)) continue;
                n.TryGetValue("lat", ref r.lat); n.TryGetValue("lon", ref r.lon); n.TryGetValue("heading", ref r.heading);
                n.TryGetValue("discovered", ref r.discovered);
                r.surveyedBy = n.GetValue("surveyedBy") ?? "";
                Lairs[r.id] = r;
            }
            foreach (string s in node.GetValues("site")) StudiedSites.Add(s);
            foreach (string s in node.GetValues("announced")) announced.Add(s);
            foreach (string s in node.GetValues("analysed")) Analysed.Add(s);
            Recompute(false);
        }

        public override void OnSave(ConfigNode node)
        {
            foreach (var r in Species.Values)
            {
                ConfigNode n = node.AddNode("SPECIES");
                n.AddValue("id", r.id);
                n.AddValue("firstSeenUT", r.firstSeenUT);
                n.AddValue("observations", r.observations);
                n.AddValue("discoveredBy", r.discoveredBy);
                n.AddValue("firstBiome", r.firstBiome);
            }
            foreach (var r in Fossils.Values)
            {
                ConfigNode n = node.AddNode("FOSSIL");
                n.AddValue("id", r.id);
                n.AddValue("firstStudiedUT", r.firstStudiedUT);
                n.AddValue("studies", r.studies);
                n.AddValue("studiedBy", r.studiedBy);
            }
            foreach (var r in Lairs.Values)
            {
                ConfigNode n = node.AddNode("LAIR");
                n.AddValue("id", r.id); n.AddValue("lat", r.lat); n.AddValue("lon", r.lon); n.AddValue("heading", r.heading);
                n.AddValue("discovered", r.discovered);
                if (!string.IsNullOrEmpty(r.surveyedBy)) n.AddValue("surveyedBy", r.surveyedBy);
            }
            foreach (string s in StudiedSites) node.AddValue("site", s);
            foreach (string s in announced) node.AddValue("announced", s);
            foreach (string s in Analysed) node.AddValue("analysed", s);
        }

        // ------------------------------------------------------------------ discovery API

        public bool IsDiscovered(LifeformDef l) { return l != null && Species.ContainsKey(l.name); }
        public bool IsStudied(FossilDef f) { return f != null && Fossils.ContainsKey(f.name); }
        public bool IsAnalysed(LifeformDef l) { return l != null && Analysed.Contains("species:" + l.name); }
        public bool IsAnalysed(FossilDef f) { return f != null && Analysed.Contains("fossil:" + f.name); }

        /// <summary>A lab analysis of a specimen or fossil sample: +1 evidence for its lineage.</summary>
        /// <returns>true the first time this species / fossil type is analysed.</returns>
        public bool RecordAnalysis(string key)
        {
            if (string.IsNullOrEmpty(key) || !Analysed.Add(key)) return false;
            Recompute(true);
            return true;
        }

        /// <returns>true if this was a brand-new species.</returns>
        public bool RecordObservation(LifeformDef l, string observer, string biome)
        {
            SpeciesRecord r;
            bool isNew = false;
            if (!Species.TryGetValue(l.name, out r))
            {
                r = new SpeciesRecord { id = l.name, firstSeenUT = Planetarium.GetUniversalTime(), discoveredBy = observer ?? "", firstBiome = biome ?? "" };
                Species[l.name] = r;
                isNew = true;
                Announce("New species discovered: " + l.displayName,
                    "<b>" + l.displayName + "</b>" + (string.IsNullOrEmpty(l.scientificName) ? "" : " (<i>" + l.scientificName + "</i>)") +
                    "\nFirst observed by " + observer + " on " + l.body + (string.IsNullOrEmpty(biome) ? "" : " (" + biome + ")") + ".\n\n" + l.description);
            }
            r.observations++;
            Recompute(true);
            return isNew;
        }

        public bool RecordFossil(FossilDef f, string siteId, string scientist)
        {
            if (!string.IsNullOrEmpty(siteId)) StudiedSites.Add(siteId);
            FossilRecord r;
            bool isNew = false;
            if (!Fossils.TryGetValue(f.name, out r))
            {
                r = new FossilRecord { id = f.name, firstStudiedUT = Planetarium.GetUniversalTime(), studiedBy = scientist ?? "" };
                Fossils[f.name] = r;
                isNew = true;
                Announce("Fossil catalogued: " + f.displayName,
                    "<b>" + f.displayName + "</b>" + (string.IsNullOrEmpty(f.ageText) ? "" : " — " + f.ageText) +
                    "\nStudied by " + scientist + " on " + f.body + ".\n\n" + f.description);
            }
            r.studies++;
            Recompute(true);
            return isNew;
        }

        // ------------------------------------------------------------------ phylogeny reveal

        public RevealState CladeState(CladeDef c)
        {
            RevealState s; return c != null && cladeState.TryGetValue(c.name, out s) ? s : RevealState.Hidden;
        }
        public int CladeScore(CladeDef c) { int s; return c != null && cladeScore.TryGetValue(c.name, out s) ? s : 0; }
        public RevealState PanspermiaState(PanspermiaDef p)
        {
            RevealState s; return p != null && panState.TryGetValue(p.name, out s) ? s : RevealState.Hidden;
        }
        public int PanspermiaScore(PanspermiaDef p) { int s; return p != null && panScore.TryGetValue(p.name, out s) ? s : 0; }

        /// <summary>Has the player found anything at all in this biosphere?</summary>
        public bool BiosphereKnown(BiosphereDef b)
        {
            if (Species.Keys.Any(id => { LifeformDef l; return XenoDatabase.Lifeforms.TryGetValue(id, out l) && l.parentClade != null && l.parentClade.biosphere == b.name; })) return true;
            if (Fossils.Keys.Any(id => { FossilDef f; return XenoDatabase.Fossils.TryGetValue(id, out f) && f.body == b.body; })) return true;
            if (XenoDatabase.Microbes.Values.Any(m => m.parentClade != null && m.parentClade.biosphere == b.name && MicrobeBridge.IsDiscovered(m))) return true;
            return false;
        }

        int FossilEvidenceFor(string target)
        {
            int e = 0;
            foreach (string id in Fossils.Keys)
            {
                FossilDef f;
                if (XenoDatabase.Fossils.TryGetValue(id, out f) && f.evidenceFor.Contains(target)) e += f.evidence + (Analysed.Contains("fossil:" + id) ? 1 : 0);
            }
            return e;
        }

        /// <summary>
        /// Clade score = discovered species beneath it (+1 each for a lab analysis) + fossil evidence naming it (or a
        /// descendant clade; +1 for a lab-analysed sample).
        /// A clade with any evidence is "Hinted" (shown as an unnamed branch); at revealThreshold it is "Revealed".
        /// Panspermia score = fossil evidence + 1 for each revealed endpoint (source clade, target root).
        /// </summary>
        public void Recompute(bool announceNew)
        {
            if (!XenoDatabase.Loaded) return;
            cladeState.Clear(); cladeScore.Clear(); panState.Clear(); panScore.Clear();

            foreach (var c in XenoDatabase.Clades.Values)
            {
                int score = 0;
                foreach (var s in XenoDatabase.AllSpeciesUnder(c)) { if (Species.ContainsKey(s.name)) score++; if (Analysed.Contains("species:" + s.name)) score++; }
                foreach (var m in XenoDatabase.AllMicrobesUnder(c)) score += MicrobeBridge.Evidence(m);
                score += FossilEvidenceFor(c.name);
                foreach (var d in Descendants(c)) score += FossilEvidenceFor(d.name);
                cladeScore[c.name] = score;
                RevealState st = score <= 0 ? RevealState.Hidden : (score >= Math.Max(1, c.revealThreshold) ? RevealState.Revealed : RevealState.Hinted);
                cladeState[c.name] = st;
            }
            foreach (var p in XenoDatabase.Panspermia.Values)
            {
                int score = FossilEvidenceFor(p.name);
                if (CladeState(p.source) == RevealState.Revealed) score++;
                if (p.targetCladeDef != null && CladeState(p.targetCladeDef) == RevealState.Revealed) score++;
                foreach (string mn in p.microbeEvidence) if (MicrobeBridge.IsDiscovered(mn)) score++;
                panScore[p.name] = score;
                panState[p.name] = score <= 0 ? RevealState.Hidden : (score >= Math.Max(1, p.revealThreshold) ? RevealState.Revealed : RevealState.Hinted);
            }

            if (announceNew)
            {
                foreach (var c in XenoDatabase.Clades.Values)
                    if (cladeState[c.name] == RevealState.Revealed && announced.Add("clade:" + c.name))
                        Announce("Lineage resolved: " + c.displayName,
                            "Comparative study has resolved a branch of the " + XenoDatabase.Biospheres[c.biosphere].displayName + " tree of life.\n\n<b>" +
                            c.rank + " " + c.displayName + "</b>" + (string.IsNullOrEmpty(c.era) ? "" : " (" + c.era + ")") + "\n" + c.description);
                foreach (var p in XenoDatabase.Panspermia.Values)
                    if (panState[p.name] == RevealState.Revealed && announced.Add("pan:" + p.name))
                        Announce("Panspermia event confirmed!",
                            "<b>" + p.displayName + "</b>\n" + p.mechanism + (string.IsNullOrEmpty(p.ageText) ? "" : ", " + p.ageText) +
                            "\n\n" + (p.targetCladeDef != null && p.targetCladeDef.name != p.target.rootClade ? "The " + p.targetCladeDef.displayName + " of " + p.target.body + " descend" : "Life on " + p.target.body + " descends") + " from the " + p.source.displayName + " lineage of " +
                            XenoDatabase.Biospheres[p.source.biosphere].body + ".\n\n" + p.description);
            }
            else
            {
                // on load, silently mark what is already revealed
                foreach (var kv in cladeState) if (kv.Value == RevealState.Revealed) announced.Add("clade:" + kv.Key);
                foreach (var kv in panState) if (kv.Value == RevealState.Revealed) announced.Add("pan:" + kv.Key);
            }

            if (OnKnowledgeChanged != null) OnKnowledgeChanged();
        }

        static IEnumerable<CladeDef> Descendants(CladeDef c)
        {
            foreach (var ch in c.childClades) { yield return ch; foreach (var d in Descendants(ch)) yield return d; }
        }

        static void Announce(string title, string body)
        {
            ScreenMessages.PostScreenMessage("<color=#7CFC9A>" + title + "</color>", 6f, ScreenMessageStyle.UPPER_CENTER);
            if (MessageSystem.Instance != null)
                MessageSystem.Instance.AddMessage(new MessageSystem.Message(title, body, MessageSystemButton.MessageButtonColor.GREEN, MessageSystemButton.ButtonIcons.ACHIEVE));
            XenoLog.Info(title);
        }

        // ------------------------------------------------------------------ debug helpers
        public void DebugDiscoverAll()
        {
            foreach (var l in XenoDatabase.Lifeforms.Values) if (!Species.ContainsKey(l.name)) Species[l.name] = new SpeciesRecord { id = l.name, firstSeenUT = Planetarium.GetUniversalTime(), discoveredBy = "Debug", observations = 1 };
            foreach (var f in XenoDatabase.Fossils.Values) if (!Fossils.ContainsKey(f.name)) Fossils[f.name] = new FossilRecord { id = f.name, firstStudiedUT = Planetarium.GetUniversalTime(), studiedBy = "Debug", studies = 1 };
            Recompute(true);
        }

        public void DebugReset()
        {
            Species.Clear(); Fossils.Clear(); StudiedSites.Clear(); announced.Clear(); Lairs.Clear(); Analysed.Clear();
            Recompute(false);
        }
    }
}
